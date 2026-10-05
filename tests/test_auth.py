from __future__ import annotations

import os

import pytest

os.environ.setdefault("AGENTRYLAB_SCRYPT_N", str(2**12))  # fast hashing for tests

from fastapi.testclient import TestClient  # noqa: E402

from agentrylab.room import Persona, Room, RoomManager  # noqa: E402
from agentrylab.room.auth import (  # noqa: E402
    AuthError,
    AuthStore,
    KeyVault,
    LockedOut,
    aad_for,
    decrypt_key,
    derive_kek,
    encrypt_key,
    key_hint,
    load_remembered_keys,
)
from agentrylab.room.providers import BrainUnavailable, MockProvider, build_user_provider  # noqa: E402
from agentrylab.room.room import Brain  # noqa: E402
from agentrylab.room.server import COOKIE_NAME, create_app  # noqa: E402


# ---------------------------------------------------------------- store
@pytest.fixture()
def store(tmp_path):
    s = AuthStore(tmp_path / "room.db")
    yield s
    s.close()


def test_register_login_and_lockout(store):
    u = store.create_user("Alex@Example.com ", "correct horse")
    assert u.email == "alex@example.com"
    with pytest.raises(AuthError):
        store.create_user("alex@example.com", "another one")
    with pytest.raises(AuthError):
        store.create_user("bob@example.com", "short")
    with pytest.raises(AuthError):
        store.create_user("not-an-email", "longenough")

    assert store.verify_password("alex@example.com", "wrong") is None
    assert store.verify_password("ALEX@example.com", "correct horse").id == u.id
    assert store.verify_password("ghost@example.com", "whatever") is None

    for _ in range(8):
        store.verify_password("alex@example.com", "wrong")
    with pytest.raises(LockedOut):
        store.verify_password("alex@example.com", "correct horse")


def test_sessions(store):
    u = store.create_user("s@example.com", "password1")
    token = store.create_session(u.id)
    assert store.user_for_session(token).id == u.id
    assert store.user_for_session("nope") is None
    assert store.user_for_session(None) is None
    store.delete_session(token)
    assert store.user_for_session(token) is None


def test_key_encryption_round_trip_and_binding(store):
    u = store.create_user("k@example.com", "password1")
    kek = derive_kek("password1", u.kek_salt)
    nonce, ct = encrypt_key(kek, "sk-secret-1234", aad_for(u.id, "openai"))
    assert b"sk-secret" not in ct
    assert decrypt_key(kek, nonce, ct, aad_for(u.id, "openai")) == "sk-secret-1234"
    with pytest.raises(Exception):
        decrypt_key(kek, nonce, ct, aad_for(u.id, "anthropic"))  # bound to provider
    with pytest.raises(Exception):
        decrypt_key(derive_kek("password2", u.kek_salt), nonce, ct, aad_for(u.id, "openai"))

    store.save_key_blob(u.id, "openai", nonce, ct, key_hint("sk-secret-1234"))
    vault = KeyVault()
    assert load_remembered_keys(store, vault, u) == []  # locked: no KEK yet
    vault.unlock(u.id, kek)
    assert load_remembered_keys(store, vault, u) == ["openai"]
    assert vault.get(u.id, "openai") == "sk-secret-1234"
    vault.forget(u.id)
    assert vault.get(u.id, "openai") is None and not vault.is_unlocked(u.id)


def test_key_hint():
    assert key_hint("sk-abcdefgh1234") == "…1234"
    assert key_hint("short") == "…"


# ----------------------------------------------------------- providers
def test_build_user_provider_requires_key_for_key_providers():
    with pytest.raises(BrainUnavailable):
        build_user_provider("openai", None, None)
    with pytest.raises(BrainUnavailable):
        build_user_provider("nope", None, "x")
    assert isinstance(build_user_provider("mock", None, None), MockProvider)
    p = build_user_provider("deepseek", None, "sk-test")
    assert p.base_url == "https://api.deepseek.com/v1" and p.model == "deepseek-chat" and p.vendor == "DeepSeek"
    p = build_user_provider("anthropic", None, "sk-ant-test")
    assert p.model == "claude-opus-5-5"
    with pytest.raises(ValueError):
        build_user_provider("openai", "bad model name!", "sk-test")


def test_brain_validation():
    assert Brain().provider == "server"
    assert Brain(provider="OpenAI").provider == "openai"
    with pytest.raises(ValueError):
        Brain(provider="skynet")
    assert Brain(provider="mock").describe()["demo"] is True


# -------------------------------------------------------------- server
class Echo(MockProvider):
    def _send_chat(self, messages, *, tools=None, **kwargs):  # type: ignore[override]
        return {"content": "echo"}


@pytest.fixture()
def app(tmp_path):
    seen = {}

    def factory(persona: Persona, room: Room):
        seen["room"] = room
        if room.brain.provider in {"server", "mock"}:
            return Echo()
        key = app.state.vault.get(room.owner_id, room.brain.provider) if room.owner_id else None
        return build_user_provider(room.brain.provider, room.brain.model, key, temperature=persona.temperature)

    mgr = RoomManager(provider_factory=factory, transcript_dir=tmp_path, seed_default=False)
    app = create_app(manager=mgr, serve_ui=False, auth_store=AuthStore(tmp_path / "auth.db"), vault=KeyVault())
    app.state.seen = seen
    return app


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c


def test_anonymous_cannot_create_rooms_or_store_keys(client):
    assert client.get("/api/auth/me").json()["user"] is None
    assert client.post("/api/rooms", json={"id": "x"}).status_code == 401
    assert client.put("/api/auth/keys/openai", json={"key": "sk-abcdefgh"}).status_code == 401


def test_register_sets_cookie_and_keys_are_never_returned(client):
    r = client.post("/api/auth/register", json={"email": "a@example.com", "password": "password1"})
    assert r.status_code == 201 and r.json()["user"]["email"] == "a@example.com"
    assert COOKIE_NAME in r.cookies
    assert r.json()["vault_unlocked"] is True

    r = client.put("/api/auth/keys/openai", json={"key": "sk-abcdefghijkl", "remember": False})
    assert r.status_code == 200
    keys = r.json()["keys"]
    assert keys == [{"provider": "openai", "hint": "…ijkl", "remembered": False, "available": True}]
    assert "sk-abcdefghijkl" not in r.text

    assert client.put("/api/auth/keys/skynet", json={"key": "sk-abcdefghijkl"}).status_code == 404
    assert client.put("/api/auth/keys/openai", json={"key": "has space in it"}).status_code == 422


def test_duplicate_register_and_bad_login(client):
    client.post("/api/auth/register", json={"email": "d@example.com", "password": "password1"})
    client.post("/api/auth/logout")
    assert client.post("/api/auth/register", json={"email": "d@example.com", "password": "password1"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "d@example.com", "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "d@example.com", "password": "password1"}).status_code == 200


def test_own_room_uses_own_key_and_is_private(client, app):
    client.post("/api/auth/register", json={"email": "o@example.com", "password": "password1"})
    # no key yet: cannot pick a key provider
    r = client.post("/api/rooms", json={"id": "lab", "brain": {"provider": "openai"}})
    assert r.status_code == 409
    client.put("/api/auth/keys/deepseek", json={"key": "sk-deepseek-test"})
    r = client.post("/api/rooms", json={"id": "lab", "topic": "keys"})
    assert r.status_code == 201
    snap = r.json()
    assert snap["brain"] == {"provider": "deepseek", "model": None}
    assert snap["provider"]["kind"] == "deepseek" and snap["owner_id"]

    # room list shows ownership
    rooms = {x["id"]: x for x in client.get("/api/rooms").json()}
    assert rooms["lab"]["mine"] is True and rooms["main"]["mine"] is False

    # the owner's key is resolved when the room builds a provider
    room = app.state.manager.get("lab")
    room.pause()
    room.add_from_library("kid")
    prov = room._provider_for(next(iter(room.personas.values())))
    assert prov.headers["Authorization"] == "Bearer sk-deepseek-test"

    # switching brain to one without a key is refused; mock is fine
    assert client.patch("/api/rooms/lab", json={"brain": {"provider": "anthropic"}}).status_code == 409
    r = client.patch("/api/rooms/lab", json={"brain": {"provider": "mock"}})
    assert r.json()["brain"]["provider"] == "mock"
    assert room._providers == {}  # cache dropped

    # another user cannot see or touch it
    other = TestClient(app)
    other.post("/api/auth/register", json={"email": "p@example.com", "password": "password1"})
    assert other.get("/api/rooms/lab").status_code == 403
    assert other.post("/api/rooms/lab/messages", json={"content": "hi"}).status_code == 403
    assert all(x["id"] != "lab" for x in other.get("/api/rooms").json())
    anon = TestClient(app)
    assert anon.get("/api/rooms/lab").status_code == 403
    with pytest.raises(Exception):
        with anon.websocket_connect("/ws/rooms/lab") as ws:
            ws.receive_json()
    # the public stage cannot be re-brained
    assert client.patch("/api/rooms/main", json={"brain": {"provider": "mock"}}).status_code == 403


def test_logout_wipes_keys_and_remembered_keys_survive_relogin(client, app):
    client.post("/api/auth/register", json={"email": "r@example.com", "password": "password1"})
    client.put("/api/auth/keys/openai", json={"key": "sk-remember-me-1234", "remember": True})
    client.put("/api/auth/keys/xai", json={"key": "xai-ephemeral-5678", "remember": False})
    me = client.get("/api/auth/me").json()
    assert {k["provider"]: k["remembered"] for k in me["keys"]} == {"openai": True, "xai": False}
    uid = me["user"]["id"]

    client.post("/api/auth/logout")
    assert app.state.vault.get(uid, "openai") is None and app.state.vault.get(uid, "xai") is None
    assert client.get("/api/auth/me").json()["user"] is None

    client.post("/api/auth/login", json={"email": "r@example.com", "password": "password1"})
    me = client.get("/api/auth/me").json()
    assert me["vault_unlocked"] is True
    assert [k["provider"] for k in me["keys"]] == ["openai"]  # xai was session-only
    assert app.state.vault.get(uid, "openai") == "sk-remember-me-1234"

    # forget everything
    client.delete("/api/auth/keys")
    assert client.get("/api/auth/me").json()["keys"] == []
    assert app.state.auth.list_key_blobs(uid) == []


def test_restart_locks_vault_until_unlock(client, app):
    client.post("/api/auth/register", json={"email": "u@example.com", "password": "password1"})
    client.put("/api/auth/keys/anthropic", json={"key": "sk-ant-remember-9999", "remember": True})
    uid = client.get("/api/auth/me").json()["user"]["id"]
    # simulate a process restart: memory gone, cookie + database intact
    app.state.vault.forget(uid)
    me = client.get("/api/auth/me").json()
    assert me["user"] and me["vault_unlocked"] is False
    assert me["keys"] == [{"provider": "anthropic", "hint": "…9999", "remembered": True, "available": False}]
    # remembering a new key needs the vault unlocked
    assert client.put("/api/auth/keys/openai", json={"key": "sk-new-key-0000", "remember": True}).status_code == 409
    assert client.post("/api/auth/unlock", json={"password": "wrong"}).status_code == 401
    me = client.post("/api/auth/unlock", json={"password": "password1"}).json()
    assert me["vault_unlocked"] and me["keys"][0]["available"] is True
    assert app.state.vault.get(uid, "anthropic") == "sk-ant-remember-9999"


def test_password_change_reencrypts_keys(client, app):
    client.post("/api/auth/register", json={"email": "c@example.com", "password": "password1"})
    client.put("/api/auth/keys/openai", json={"key": "sk-keep-me-around-1", "remember": True})
    assert client.post("/api/auth/password", json={"current_password": "nope", "new_password": "password2"}).status_code == 401
    assert client.post("/api/auth/password", json={"current_password": "password1", "new_password": "password2"}).status_code == 200
    uid = client.get("/api/auth/me").json()["user"]["id"]
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"email": "c@example.com", "password": "password1"}).status_code == 401
    client.post("/api/auth/login", json={"email": "c@example.com", "password": "password2"})
    assert app.state.vault.get(uid, "openai") == "sk-keep-me-around-1"


async def test_room_pauses_when_brain_unavailable():
    def factory(_p: Persona, room: Room):
        raise BrainUnavailable("No OpenAI API key in your vault.")

    room = Room("nokey", speed=0.5, provider_factory=factory, owner_id="u_1", brain=Brain(provider="openai"))
    q = room.subscribe()
    room.start()
    try:
        room.add_from_library("poet")
        for _ in range(200):
            if room.status == "paused":
                break
            import asyncio

            await asyncio.sleep(0.01)
    finally:
        await room.close()
    assert room.status == "paused"
    assert any(m.kind == "system" and "No OpenAI API key" in m.content for m in room.messages)
    assert any(e and e["type"] == "error" for e in list(q._queue))  # type: ignore[attr-defined]


async def test_room_pauses_after_repeated_failures():
    import asyncio

    class Boom(MockProvider):
        def _send_chat(self, messages, *, tools=None, **kwargs):  # type: ignore[override]
            raise RuntimeError("401 bad key")

    room = Room("boom", speed=0.5, provider_factory=lambda _p, _r: Boom())
    room.start()
    try:
        room.add_from_library("poet")
        for _ in range(300):
            if room.status == "paused":
                break
            await asyncio.sleep(0.01)
    finally:
        await room.close()
    assert room.status == "paused"
    assert sum(1 for m in room.messages if "glitched" in m.content) == 3
