from __future__ import annotations

import os
import sqlite3
import time
import pickle
from pathlib import Path
from typing import Any, Dict, Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT PRIMARY KEY,
    payload   BLOB NOT NULL,
    updated_at REAL NOT NULL
);
"""


class SQLiteCheckpointer:
    """Simple SQLite-backed checkpoint store.

    Stores a serialized snapshot per `thread_id`. Intended for best-effort recovery
    between runs; schema is intentionally small.
    """

    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self.path = str(db_path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    # ----------------------------- Public API -----------------------------
    def save_checkpoint(self, thread_id: str, state: Any) -> None:
        """Persist a snapshot of the given state.

        We prefer to serialize `state.__dict__` to avoid code-coupled pickles; if that
        fails, fall back to pickling the object itself.
        """
        payload = self._serialize_state(state)
        updated_at = time.time()
        with self._conn:  # implicit transaction
            self._conn.execute(
                "INSERT INTO checkpoints(thread_id, payload, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(thread_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
                (thread_id, payload, updated_at),
            )

    # Back-compat alternate name (Engine may call `checkpoint`)
    def checkpoint(self, thread_id: str, state: Any) -> None:  # pragma: no cover
        self.save_checkpoint(thread_id, state)

    def load_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Load a previously saved snapshot for `thread_id`.

        Returns a dict of state attributes if available, else None. The caller
        is responsible for rehydrating its State instance.
        """
        cur = self._conn.execute(
            "SELECT payload FROM checkpoints WHERE thread_id = ?", (thread_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return self._deserialize_state(row[0])

    def delete_checkpoint(self, thread_id: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))

    def list_threads(self) -> list[tuple[str, float]]:
        """Return list of (thread_id, updated_at)."""
        try:
            cur = self._conn.execute(
                "SELECT thread_id, updated_at FROM checkpoints ORDER BY updated_at DESC"
            )
            return [(r[0], float(r[1])) for r in cur.fetchall()]
        except Exception:
            return []

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    # ----------------------------- Internals -----------------------------
    @staticmethod
    def _serialize_state(state: Any) -> bytes:
        # Prefer shallow dict snapshot
        try:
            snapshot: Dict[str, Any] = dict(getattr(state, "__dict__", {}))
            # Avoid storing huge raw provider payloads if present
            snapshot.pop("_provider_raw", None)
            return pickle.dumps({"__kind__": "dict", "data": snapshot}, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            # Fallback: pickle full object
            return pickle.dumps({"__kind__": "pickle", "data": state}, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def _deserialize_state(blob: bytes) -> Dict[str, Any]:
        try:
            wrapper = pickle.loads(blob)
            kind = wrapper.get("__kind__")
            if kind == "dict":
                data = wrapper.get("data", {})
                if isinstance(data, dict):
                    return data
            # Fallback: foreign pickle → expose under a common key
            return {"_pickled": wrapper.get("data")}
        except Exception:
            # Corrupt payload; caller should treat as missing
            return {}
