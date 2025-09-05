from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe_thread_filename(thread_id: str) -> str:
    # Replace unsafe chars, avoid empty
    s = _SAFE_NAME.sub("_", thread_id).strip("._-") or "run"
    return f"{s}.jsonl"


class JSONLTranscriptStore:
    """Append-only per-thread transcript writer/reader.

    Each thread is stored as a separate JSONL file under `root_dir` named
    `<safe_thread_id>.jsonl`. Appends are newline-delimited JSON objects.
    """

    def __init__(self, root_dir: str | os.PathLike[str], *, fsync: bool = False) -> None:
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.fsync = bool(fsync)

    # ----------------------------- public API -----------------------------
    def append_transcript(self, thread_id: str, entry: Dict[str, Any]) -> None:
        """Append a single event to a thread's JSONL file."""
        path = self.root / _safe_thread_filename(thread_id)
        # Ensure ascii is not forced so we keep readable unicode; add newline terminator
        data = json.dumps(entry, ensure_ascii=False)
        # Use buffered text write for performance; optionally fsync
        with path.open("a", encoding="utf-8") as f:
            f.write(data)
            f.write("\n")
            if self.fsync:
                try:
                    f.flush()
                    os.fsync(f.fileno())
                except Exception:
                    # Best-effort; ignore fsync failures
                    pass

    def iter_transcript(self, thread_id: str) -> Iterator[Dict[str, Any]]:
        """Yield events for a thread in order."""
        path = self.root / _safe_thread_filename(thread_id)
        if not path.exists():
            return iter(())  # empty iterator
        # Using text mode with universal newlines; tolerate partial/corrupt lines
        def _gen() -> Iterator[Dict[str, Any]]:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        # Skip malformed line
                        continue
                    if isinstance(obj, dict):
                        yield obj
        return _gen()

    def read_transcript(self, thread_id: str, *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read all (or last N) events for a thread into memory."""
        if limit is None or limit <= 0:
            return list(self.iter_transcript(thread_id))
        # Efficient last-N: read lines and keep a rotating buffer
        path = self.root / _safe_thread_filename(thread_id)
        if not path.exists():
            return []
        # Fallback simple approach (files are typically small in MVP)
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception:
            return []
        out: List[Dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    out.append(obj)
            except Exception:
                continue
        return out

    def delete_transcript(self, thread_id: str) -> None:
        path = self.root / _safe_thread_filename(thread_id)
        try:
            path.unlink(missing_ok=True)  # type: ignore[call-arg]
        except TypeError:
            # Python <3.8 compatibility
            if path.exists():
                try:
                    path.unlink()
                except Exception:
                    pass
