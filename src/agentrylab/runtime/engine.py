from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional
import time

from agentrylab.runtime.nodes.base import NodeBase, NodeOutput
from agentrylab.runtime.scheduler.base import Scheduler
from agentrylab.runtime.actions import CONTINUE, STOP, STEP_BACK


class Engine:
    """Core runtime loop.

    Responsibilities:
      • Configure the scheduler with the active agent IDs.
      • For each tick, ask scheduler which nodes to run, execute them, and apply outputs.
      • Persist transcript events and (optionally) checkpoints via the Store facade.
      • Honor control actions (e.g., STEP_BACK/STOP) emitted by the moderator.
    """

    def __init__(
        self,
        *,
        preset_cfg: Any,
        nodes: Mapping[str, NodeBase],
        scheduler: Scheduler,
        store: Any,
        state: Any,
    ) -> None:
        self.cfg = preset_cfg
        self.nodes: Dict[str, NodeBase] = dict(nodes)
        self.scheduler = scheduler
        self.store = store
        self.state = state

        # Configure scheduler with the initial active agents
        try:
            self.scheduler.configure(
                agents=list(self.nodes.keys()),
                schedule=getattr(preset_cfg, "schedule", None),
            )
        except Exception:
            # Scheduler implementations are free to ignore configure()
            pass

        # transcript writer capabilities are optional; we feature-detect
        self._has_append = hasattr(self.store, "append_transcript")
        self._has_checkpoint = hasattr(self.store, "save_checkpoint") or hasattr(
            self.store, "checkpoint"
        )

    # ------------------------------------------------------------------
    def tick(self) -> None:
        """Execute one iteration based on the scheduler's decision."""
        # Reset per-iteration tool budgets at the start of each tick
        if hasattr(self.state, "reset_iteration_counters"):
            try:
                self.state.reset_iteration_counters()
            except Exception:
                pass

        if getattr(self.state, "stop_flag", False):
            return

        turn_agents = self.scheduler.next(
            turn_idx=getattr(self.state, "iter", 0), agents=list(self.nodes.keys())
        )

        for agent_id in turn_agents:
            node = self.nodes.get(agent_id)
            if node is None:
                # Skip silently if unknown id; could log
                continue

            started_at = time.time()
            try:
                out = node(self.state)
                duration_ms = (time.time() - started_at) * 1000.0
                self._apply_output(agent_id, out, duration_ms=duration_ms)
                if out.actions:  # e.g., moderator control
                    self._apply_actions(out.actions)
            except Exception as e:
                # Record error in transcript
                self._append_transcript(
                    {
                        "t": time.time(),
                        "iter": getattr(self.state, "iter", 0),
                        "agent_id": agent_id,
                        "role": getattr(node, "role_name", "agent"),
                        "error": f"{type(e).__name__}: {e}",
                    }
                )
                # Optionally stop on first error if configured
                try:
                    stop_on_error = bool(getattr(getattr(self.cfg, "runtime", None), "stop_on_error", False))
                except Exception:
                    stop_on_error = False
                if stop_on_error:
                    self.state.stop_flag = True
                    break
                continue

        # Advance iteration counter
        self.state.iter = int(getattr(self.state, "iter", 0)) + 1

        # Periodic checkpoint (MVP: every turn). Store may ignore or throttle internally
        self._maybe_checkpoint()

    # ------------------------------------------------------------------
    def _apply_output(self, agent_id: str, out: NodeOutput, *, duration_ms: float | None = None) -> None:
        """Apply a node's output to state and persistence."""
        # Skip empty user outputs to avoid transcript noise
        if out.role == "user":
            content = out.content if getattr(out, "content", None) is not None else ""
            if not isinstance(content, str) or not content.strip():
                return
        # Update state/history first so later consumers can see it
        if hasattr(self.state, "append_message"):
            try:
                self.state.append_message(agent_id, out)
            except Exception:
                pass

        # Persist structured transcript
        entry: Dict[str, Any] = {
            "t": time.time(),
            "iter": getattr(self.state, "iter", 0),
            "agent_id": agent_id,
            "role": out.role,
            "content": self._serialize(out.content),
            "metadata": self._serialize(out.metadata),
            "actions": self._serialize(out.actions),
        }
        if duration_ms is not None:
            entry["latency_ms"] = float(duration_ms)
        self._append_transcript(entry)

    def _apply_actions(self, actions: Mapping[str, Any]) -> None:
        t = actions.get("type") if isinstance(actions, Mapping) else None
        if t == STEP_BACK:
            rollback_n = int(actions.get("rollback", 0) or 0)
            clear = bool(actions.get("clear_summaries", False))
            if hasattr(self.state, "rollback"):
                self.state.rollback(rollback_n, clear_summaries=clear)
        elif t == STOP:
            self.state.stop_flag = True
        # CONTINUE is the default (no-op)

    # ------------------------------------------------------------------
    def _append_transcript(self, entry: Dict[str, Any]) -> None:
        thread_id = getattr(self.state, "thread_id", None) or getattr(self.state, "id", "run")
        if self._has_append:
            try:
                self.store.append_transcript(thread_id, entry)
                return
            except Exception:
                pass
        # Fallback: keep an in-memory history for the session
        hist = getattr(self.state, "history", None)
        if isinstance(hist, list):
            hist.append(entry)
        else:
            setattr(self.state, "history", [entry])

    def _maybe_checkpoint(self) -> None:
        if not self._has_checkpoint:
            return
        thread_id = getattr(self.state, "thread_id", None) or getattr(self.state, "id", "run")
        try:
            if hasattr(self.store, "save_checkpoint"):
                self.store.save_checkpoint(thread_id, self.state)
            else:
                # alt method name
                self.store.checkpoint(thread_id, self.state)
        except Exception:
            # Best-effort: ignore checkpoint failures for MVP
            pass

    # --------------------------- utils ---------------------------------
    @staticmethod
    def _serialize(obj: Any) -> Any:
        """Make dataclasses/TypedDicts JSON-serializable for transcript writes."""
        if is_dataclass(obj):
            return asdict(obj)
        return obj
