"""Accounts, sessions and the API-key vault.

Security model, in one paragraph: passwords are hashed with scrypt and never
stored; sessions are random tokens stored hashed, delivered as HttpOnly
cookies. API keys live **only in server memory**, per user, and disappear on
logout, on "forget", or when the process restarts. If a user opts to remember
a key, it is encrypted with AES-256-GCM under a key derived from the user's
own password (scrypt, separate salt). The database therefore never contains a
usable key: the operator can read ciphertext, but decrypting it needs the
password, which the operator does not have. After a restart the vault is
empty until the user signs in (or unlocks) again, which re-derives that key.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SESSION_TTL_S = 7 * 24 * 3600
LOGIN_MAX_FAILURES = 8
LOGIN_WINDOW_S = 15 * 60

# scrypt parameters: N=2^14, r=8 is ~16 MiB and ~30 ms per hash; tunable via env
# (tests lower it). OpenSSL caps memory at 32 MiB by default, so pass maxmem.
_SCRYPT_N = int(os.getenv("AGENTRYLAB_SCRYPT_N", str(2**14)))
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_MAXMEM = 128 * _SCRYPT_N * _SCRYPT_R * 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    pw_salt     BLOB NOT NULL,
    pw_hash     BLOB NOT NULL,
    kek_salt    BLOB NOT NULL,
    created_at  REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash  TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    created_at  REAL NOT NULL,
    expires_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
CREATE TABLE IF NOT EXISTS api_keys (
    user_id     TEXT NOT NULL,
    provider    TEXT NOT NULL,
    nonce       BLOB NOT NULL,
    ciphertext  BLOB NOT NULL,
    hint        TEXT NOT NULL,
    updated_at  REAL NOT NULL,
    PRIMARY KEY (user_id, provider)
);
"""


@dataclass(frozen=True)
class User:
    id: str
    email: str
    kek_salt: bytes
    created_at: float


class AuthError(Exception):
    pass


class LockedOut(AuthError):
    pass


# ----------------------------------------------------------------------- crypto
def _scrypt(secret: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        secret.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, maxmem=_SCRYPT_MAXMEM, dklen=32
    )


def hash_password(password: str, salt: bytes) -> bytes:
    return _scrypt(password, salt)


def derive_kek(password: str, kek_salt: bytes) -> bytes:
    """Key-encryption key for the user's remembered API keys."""
    return _scrypt("kek:" + password, kek_salt)


def encrypt_key(kek: bytes, plaintext: str, aad: bytes) -> Tuple[bytes, bytes]:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = secrets.token_bytes(12)
    return nonce, AESGCM(kek).encrypt(nonce, plaintext.encode("utf-8"), aad)


def decrypt_key(kek: bytes, nonce: bytes, ciphertext: bytes, aad: bytes) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    return AESGCM(kek).decrypt(nonce, ciphertext, aad).decode("utf-8")


def key_hint(key: str) -> str:
    return ("…" + key[-4:]) if len(key) >= 8 else "…"


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email or len(email) < 5 or len(email) > 254 or " " in email:
        raise AuthError("that does not look like an email address")
    return email


def check_password_strength(password: str) -> None:
    if len(password) < 8:
        raise AuthError("password must be at least 8 characters")
    if len(password) > 256:
        raise AuthError("password is too long")


# ------------------------------------------------------------------------ store
class AuthStore:
    """SQLite-backed users, sessions and encrypted key blobs."""

    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self.path = str(db_path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._failures: Dict[str, List[float]] = {}

    def close(self) -> None:
        self._conn.close()

    # ---- users
    def create_user(self, email: str, password: str) -> User:
        email = normalize_email(email)
        check_password_strength(password)
        pw_salt, kek_salt = secrets.token_bytes(16), secrets.token_bytes(16)
        user = User(id=f"u_{uuid.uuid4().hex[:12]}", email=email, kek_salt=kek_salt, created_at=time.time())
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO users(id,email,pw_salt,pw_hash,kek_salt,created_at) VALUES(?,?,?,?,?,?)",
                    (user.id, email, pw_salt, hash_password(password, pw_salt), kek_salt, user.created_at),
                )
                self._conn.commit()
            except sqlite3.IntegrityError:
                raise AuthError("an account with that email already exists")
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        row = self._conn.execute("SELECT id,email,kek_salt,created_at FROM users WHERE id=?", (user_id,)).fetchone()
        return User(*row) if row else None

    def verify_password(self, email: str, password: str) -> Optional[User]:
        """Return the user if the credentials match; None otherwise. Rate-limited."""
        email = normalize_email(email)
        now = time.time()
        recent = [t for t in self._failures.get(email, []) if now - t < LOGIN_WINDOW_S]
        if len(recent) >= LOGIN_MAX_FAILURES:
            self._failures[email] = recent
            raise LockedOut("too many failed attempts; try again in a few minutes")
        row = self._conn.execute(
            "SELECT id,email,pw_salt,pw_hash,kek_salt,created_at FROM users WHERE email=?", (email,)
        ).fetchone()
        if row is None:
            # Still burn time so missing accounts are not distinguishable by latency.
            hash_password(password, b"\x00" * 16)
            ok = False
        else:
            ok = hmac.compare_digest(hash_password(password, row[2]), row[3])
        if not ok:
            recent.append(now)
            self._failures[email] = recent
            return None
        self._failures.pop(email, None)
        return User(id=row[0], email=row[1], kek_salt=row[4], created_at=row[5])

    def change_password(self, user_id: str, new_password: str) -> None:
        check_password_strength(new_password)
        pw_salt = secrets.token_bytes(16)
        with self._lock:
            self._conn.execute(
                "UPDATE users SET pw_salt=?, pw_hash=? WHERE id=?",
                (pw_salt, hash_password(new_password, pw_salt), user_id),
            )
            self._conn.commit()

    # ---- sessions
    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)",
                (self._token_hash(token), user_id, now, now + SESSION_TTL_S),
            )
            self._conn.commit()
        return token

    def user_for_session(self, token: Optional[str]) -> Optional[User]:
        if not token:
            return None
        row = self._conn.execute(
            "SELECT u.id,u.email,u.kek_salt,u.created_at,s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?",
            (self._token_hash(token),),
        ).fetchone()
        if row is None:
            return None
        if row[4] < time.time():
            self.delete_session(token)
            return None
        return User(id=row[0], email=row[1], kek_salt=row[2], created_at=row[3])

    def delete_session(self, token: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM sessions WHERE token_hash=?", (self._token_hash(token),))
            self._conn.commit()

    def delete_user_sessions(self, user_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            self._conn.commit()

    # ---- remembered (encrypted) keys
    def save_key_blob(self, user_id: str, provider: str, nonce: bytes, ciphertext: bytes, hint: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO api_keys(user_id,provider,nonce,ciphertext,hint,updated_at) VALUES(?,?,?,?,?,?)",
                (user_id, provider, nonce, ciphertext, hint, time.time()),
            )
            self._conn.commit()

    def list_key_blobs(self, user_id: str) -> List[Tuple[str, bytes, bytes, str]]:
        rows = self._conn.execute(
            "SELECT provider,nonce,ciphertext,hint FROM api_keys WHERE user_id=? ORDER BY provider", (user_id,)
        ).fetchall()
        return [(r[0], r[1], r[2], r[3]) for r in rows]

    def delete_key_blob(self, user_id: str, provider: Optional[str] = None) -> None:
        with self._lock:
            if provider is None:
                self._conn.execute("DELETE FROM api_keys WHERE user_id=?", (user_id,))
            else:
                self._conn.execute("DELETE FROM api_keys WHERE user_id=? AND provider=?", (user_id, provider))
            self._conn.commit()


# ------------------------------------------------------------------------ vault
class KeyVault:
    """Per-user API keys and key-encryption keys, in process memory only."""

    def __init__(self) -> None:
        self._keys: Dict[str, Dict[str, str]] = {}
        self._kek: Dict[str, bytes] = {}
        self._lock = threading.Lock()

    def unlock(self, user_id: str, kek: bytes) -> None:
        with self._lock:
            self._kek[user_id] = kek

    def is_unlocked(self, user_id: str) -> bool:
        return user_id in self._kek

    def kek(self, user_id: str) -> Optional[bytes]:
        return self._kek.get(user_id)

    def set(self, user_id: str, provider: str, key: str) -> None:
        with self._lock:
            self._keys.setdefault(user_id, {})[provider] = key

    def get(self, user_id: str, provider: str) -> Optional[str]:
        return self._keys.get(user_id, {}).get(provider)

    def providers(self, user_id: str) -> List[str]:
        return sorted(self._keys.get(user_id, {}))

    def remove(self, user_id: str, provider: str) -> None:
        with self._lock:
            self._keys.get(user_id, {}).pop(provider, None)

    def forget(self, user_id: str) -> None:
        """Drop everything we hold for a user (logout / explicit forget / lock)."""
        with self._lock:
            self._keys.pop(user_id, None)
            self._kek.pop(user_id, None)


# ------------------------------------------------------------------- helpers
def aad_for(user_id: str, provider: str) -> bytes:
    """Bind each ciphertext to its user and provider so blobs cannot be swapped."""
    return f"{user_id}:{provider}".encode("utf-8")


def load_remembered_keys(store: AuthStore, vault: KeyVault, user: User) -> List[str]:
    """Decrypt a user's remembered keys into the vault. Returns providers loaded."""
    kek = vault.kek(user.id)
    if kek is None:
        return []
    loaded: List[str] = []
    for provider, nonce, ciphertext, _hint in store.list_key_blobs(user.id):
        try:
            vault.set(user.id, provider, decrypt_key(kek, nonce, ciphertext, aad_for(user.id, provider)))
            loaded.append(provider)
        except Exception:
            # Wrong password epoch (e.g. password changed elsewhere): leave it locked.
            continue
    return loaded
