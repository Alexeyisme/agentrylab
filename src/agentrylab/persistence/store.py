from __future__ import annotations

"""Persistence facade combining checkpoints and transcript backends.

This class adapts the preset's `persistence` and `persistence_tools` blocks into
concrete backends used by the Engine and Lab. It is intentionally tolerant of
missing/partial configuration and falls back to local defaults under `outputs/`.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from .checkpoints.sqlite import SQLiteCheckpointer
from .transcript.jsonl import JSONLTranscriptStore


class Store:
    def __init__(self, cfg: Any) -> None:
        self.cfg = cfg

        # Defaults
        outputs_dir = Path("outputs")
        outputs_dir.mkdir(parents=True, exist_ok=True)

        # ----------------------- Resolve persistence_tools -----------------------
        # We support two built-ins: sqlite (checkpoints) and jsonl (transcript).
        tools_cfg: Dict[str, Any] = {}
        pt = getattr(cfg, "persistence_tools", None)
        if isinstance(pt, dict):
            tools_cfg = pt

        # Helper to read a tool's params safely
        def tool_params(tool_id: str) -> Dict[str, Any]:
            block = tools_cfg.get(tool_id)
            if isinstance(block, dict):
                params = block.get("params")
                return dict(params or {}) if isinstance(params, dict) else {}
            return {}

        # ----------------------- Transcript backend (JSONL) ----------------------
        transcript_root: Optional[Path] = None

        # 1) If preset.persistence.transcript (list of tool ids) includes 'jsonl', use its params
        p = getattr(cfg, "persistence", None)
        if p is not None and hasattr(p, "transcript") and getattr(p, "transcript"):
            t_list = list(getattr(p, "transcript") or [])
            if "jsonl" in t_list:
                params = tool_params("jsonl")
                pth = params.get("path") or params.get("root")
                if isinstance(pth, str) and pth.strip():
                    path = Path(pth)
                    transcript_root = path.parent if path.suffix == ".jsonl" else path

        # 2) Else if simple transcript_path provided, treat as directory or file
        if transcript_root is None and p is not None and getattr(p, "transcript_path", None):
            path = Path(getattr(p, "transcript_path"))
            transcript_root = path.parent if path.suffix == ".jsonl" else path

        # 3) Fallback default
        if transcript_root is None:
            transcript_root = outputs_dir / "transcripts"

        transcript_root.mkdir(parents=True, exist_ok=True)
        self._transcript = JSONLTranscriptStore(transcript_root)

        # ----------------------- Checkpoints backend (SQLite) --------------------
        sqlite_path: Optional[Path] = None

        # 1) If preset.persistence.checkpoints includes 'sqlite', use its params
        if p is not None and hasattr(p, "checkpoints") and getattr(p, "checkpoints"):
            c_list = list(getattr(p, "checkpoints") or [])
            if "sqlite" in c_list:
                params = tool_params("sqlite")
                pth = params.get("path") or params.get("db_path")
                if isinstance(pth, str) and pth.strip():
                    sqlite_path = Path(pth)

        # 2) Else if simple sqlite_path provided
        if sqlite_path is None and p is not None and getattr(p, "sqlite_path", None):
            sqlite_path = Path(getattr(p, "sqlite_path"))

        # 3) Fallback default
        if sqlite_path is None:
            sqlite_path = outputs_dir / "checkpoints.db"

        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._checkpointer = SQLiteCheckpointer(str(sqlite_path))

    # ----------------------------- Transcript API -----------------------------
    def append_transcript(self, thread_id: str, entry: Dict[str, Any]) -> None:
        self._transcript.append_transcript(thread_id, entry)

    def read_transcript(self, thread_id: str, limit: Optional[int] = None):
        return self._transcript.read_transcript(thread_id, limit=limit)

    # ----------------------------- Checkpoint API -----------------------------
    def save_checkpoint(self, thread_id: str, state: Any) -> None:
        self._checkpointer.save_checkpoint(thread_id, state)

    # Back-compat alias
    def checkpoint(self, thread_id: str, state: Any) -> None:  # pragma: no cover
        self.save_checkpoint(thread_id, state)

    def load_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Load a previously saved snapshot for thread_id if available.

        Returns a dict of state attributes or None if missing/corrupt.
        """
        try:
            return self._checkpointer.load_checkpoint(thread_id)
        except Exception:
            return None

    # Utilities for CLI
    def delete_checkpoint(self, thread_id: str) -> None:
        try:
            self._checkpointer.delete_checkpoint(thread_id)
        except Exception:
            pass

    def delete_transcript(self, thread_id: str) -> None:
        try:
            self._transcript.delete_transcript(thread_id)
        except Exception:
            pass

    def list_threads(self) -> list[tuple[str, float]]:
        """Return list of (thread_id, updated_at) from the checkpoint store."""
        try:
            if hasattr(self._checkpointer, "list_threads"):
                return self._checkpointer.list_threads()  # type: ignore[attr-defined]
        except Exception:
            pass
        return []

    # ----------------------------- Lifecycle -----------------------------
    def close(self) -> None:  # pragma: no cover
        try:
            cp = getattr(self, "_checkpointer", None)
            if cp is not None and hasattr(cp, "close"):
                cp.close()
        except Exception:
            pass
