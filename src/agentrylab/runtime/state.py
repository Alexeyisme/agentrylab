from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple
import json
import logging

from agentrylab.runtime.providers.base import Message
from agentrylab.types import ProgressInfo  # exported for typing only


# --------------------------- Lightweight contracts ---------------------------
class _Contracts:
    def __init__(self, root_cfg: Any) -> None:
        self._mcfg = getattr(getattr(root_cfg, "runtime", None), "message_contract", None)

    def validate_agent_output(self, out: Any, cfg: Any) -> None:
        # Only enforce for agent role
        role = getattr(out, "role", None)
        if role != "agent" or self._mcfg is None:
            return

        if bool(getattr(self._mcfg, "require_metadata", False)):
            md = getattr(out, "metadata", None)
            if not isinstance(md, dict):
                raise ValueError("Agent output missing metadata (required by message_contract)")
            cites = md.get("citations")
            if not (isinstance(cites, list) and len(cites) >= int(getattr(self._mcfg, "min_citations", 1))):
                need = int(getattr(self._mcfg, "min_citations", 1))
                raise ValueError(f"Agent output must include at least {need} citation(s) per message_contract")

    # keep the other hooks no-ops
    def validate_summary_output(self, out: Any, cfg: Any) -> None: return
    def validate_advisor_output(self, out: Any, cfg: Any) -> None: return


# --------------------------------- State ------------------------------------
class State:
    """In-memory run state + helpers used by nodes and engine.

    Holds the thread context, running counters, message history, and normalization
    utilities so nodes stay thin and providers remain pluggable.
    """

    def __init__(self, *, thread_id: str, cfg: Any) -> None:
        self.thread_id: str = thread_id
        self.cfg = cfg
        self.iter: int = 0
        self.stop_flag: bool = False
        self.contracts = _Contracts(self.cfg)

        # Simple in-memory event log; Engine also writes to persistence
        self.history: List[Dict[str, Any]] = []

        # Optional running summary for UI/CLI
        self.running_summary: Optional[str] = None

        # ---------------- Budgets / counters ----------------
        # Global totals across the whole run
        self._tool_calls_run_total: int = 0
        # Global per-iteration counter
        self._tool_calls_iteration: int = 0
        # Per-tool totals across the run
        self._tool_calls_run_by_id: Dict[str, int] = {}
        # Per-tool counts for the current iteration
        self._tool_calls_iter_by_id: Dict[str, int] = {}

        # User input queues (per user id)
        self._user_inputs: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Message building for providers
    # ------------------------------------------------------------------
    def compose_messages(self, node_cfg: Any, *, role_hint: Optional[str] = None) -> List[Message]:
        """Build a provider-ready message list for a node.

        Order:
          1) System prompt from the node config (if any)
          2) A sliding window of prior assistant/tool messages from history

        For MVP we treat previous agent/advisor/summarizer outputs as assistant messages.
        Moderator JSON payloads are not injected here by default.
        """
        messages: List[Message] = []

        # --- TRACE LOGGING: log the full input context for this agent ---
        from agentrylab.logging import emit_trace
        agent_id = getattr(node_cfg, "id", None) or getattr(node_cfg, "display_name", None) or "unknown"
        # We'll build up the context as we go, then log it at the end
        trace_context = {
            "agent_id": agent_id,
            "system_prompt": getattr(node_cfg, "system_prompt", None),
            "objective": getattr(self.cfg, "objective", None),
            "max_messages": getattr(getattr(node_cfg, "context", None), "max_messages", None) or (getattr(node_cfg, "context", None) or {}).get("max_messages", None),
            "history": []
        }

        # Helper to read nested context flags with sensible fallbacks
        def _ctx_bool(key: str, default: bool = False) -> bool:
            val = None
            ctx = getattr(node_cfg, "context", None)
            if isinstance(ctx, dict):
                val = ctx.get(key, None)
            else:
                # tolerate pydantic model with attrs
                v = getattr(ctx, key, None) if ctx is not None else None
                val = v
            if val is None:
                defaults = getattr(self.cfg, "context_defaults", None)
                if isinstance(defaults, dict):
                    val = defaults.get(key, None)
                else:
                    val = getattr(defaults, key, None) if defaults is not None else None
            return bool(val) if val is not None else default

        def _ctx_int(key: str, default: int) -> int:
            ctx = getattr(node_cfg, "context", None)
            val = None
            if isinstance(ctx, dict):
                val = ctx.get(key, None)
            else:
                val = getattr(ctx, key, None) if ctx is not None else None
            try:
                return int(val) if val is not None else int(default)
            except Exception:
                return int(default)

        # System prompt (pinned each turn by design)
        system_prompt = getattr(node_cfg, "system_prompt", None)
        if isinstance(system_prompt, str) and system_prompt.strip():
            messages.append(Message(role="system", content=system_prompt.strip()))

        # Optional objective injection
        if _ctx_bool("pin_objective", default=False):
            objective = getattr(self.cfg, "objective", None)
            if isinstance(objective, str) and objective.strip():
                messages.append(Message(role="user", content=objective.strip()))

        # Pull simple window from history
        # Prefer per-node context.max_messages over global history_window
        window = _ctx_int("max_messages", int(getattr(self.cfg, "history_window", 20) or 20))
        recent = self.history[-window:]
        for ev in recent:
            role = ev.get("role")
            content = ev.get("content")
            # Add to trace context
            trace_context["history"].append({"role": role, "content": content})
            if role == "user":
                if isinstance(content, (str, dict)):
                    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                    messages.append(Message(role="user", content=text))
            elif role in {"agent", "advisor", "summarizer"}:
                if isinstance(content, (str, dict)):
                    # stringify dicts (e.g., structured summaries)
                    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                    messages.append(Message(role="assistant", content=text))
            # tool results are appended inline by AgentNode during the turn

        # Emit the trace log for this agent's input context
        emit_trace("agent_input_context", **trace_context)
        return messages

    # ------------------------------------------------------------------
    # Normalization helpers (provider-agnostic best-effort)
    # ------------------------------------------------------------------
    def extract_content_and_metadata(
        self, raw: Mapping[str, Any], *, expect_json: bool = False
    ) -> Tuple[Any, Optional[Dict[str, Any]]]:
        """Best-effort normalization similar to LLMProvider._extract_content_and_metadata.

        Returns (content, metadata). If `expect_json=True`, will attempt to parse
        content as JSON and return a Python object in `content`.
        """
        # direct
        if isinstance(raw, Mapping) and "content" in raw:
            content = raw.get("content") or ""
            meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else None
            return (self._maybe_json(content) if expect_json else content, meta)

        # OpenAI-like
        choices = raw.get("choices") if isinstance(raw, Mapping) else None
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {}) if isinstance(choices[0], Mapping) else {}
            if isinstance(msg, Mapping):
                content = msg.get("content") or ""
                meta = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else None
                return (self._maybe_json(content) if expect_json else content, meta)

        # Ollama-like
        msg = raw.get("message") if isinstance(raw, Mapping) else None
        if isinstance(msg, Mapping) and "content" in msg:
            content = msg.get("content") or ""
            meta = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else None
            return (self._maybe_json(content) if expect_json else content, meta)

        # Grok / xAI-ish quick paths
        for key in ("output_text", "output"):
            if isinstance(raw.get(key), str):
                return (self._maybe_json(raw[key]) if expect_json else raw[key], None)  # type: ignore[index]

        # Generic list-of-blocks in `content`
        cnt = raw.get("content") if isinstance(raw, Mapping) else None
        if isinstance(cnt, list):
            parts: List[str] = []
            for item in cnt:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, Mapping):
                    for k in ("text", "value", "content"):
                        v = item.get(k)
                        if isinstance(v, str):
                            parts.append(v)
                            break
            text = "\n".join(parts) if parts else ""
            return (self._maybe_json(text) if expect_json else text, None)

        # Fallback to readable JSON
        try:
            text = json.dumps(raw, ensure_ascii=False)
        except Exception:
            text = str(raw)
        return (self._maybe_json(text) if expect_json else text, None)

    def parse_json_response(self, raw: Mapping[str, Any]) -> Dict[str, Any]:
        """Extract JSON content from a provider response or raise ValueError."""
        content, _ = self.extract_content_and_metadata(raw, expect_json=False)
        if isinstance(content, dict):
            return content
        if not isinstance(content, str):
            raise ValueError("Expected string content to parse as JSON")
        try:
            return json.loads(content)
        except Exception as e:
            raise ValueError(f"Expected JSON content, got: {content[:120]!r} ...") from e

    # ------------------------------------------------------------------
    # Transcript & reducers used by the engine
    # ------------------------------------------------------------------
    def append_message(self, agent_id: str, out: Any) -> None:
        """Append a node output to in-memory history for context windows.

        Engine persists a richer transcript; this is just for composing prompts.
        """
        entry: Dict[str, Any] = {
            "agent_id": agent_id,
            "role": getattr(out, "role", None) or getattr(out, "role_name", "agent"),
            "content": getattr(out, "content", None),
        }
        self.history.append(entry)

    def rollback(self, n: int, *, clear_summaries: bool = False) -> None:
        if n <= 0:
            return
        if n >= len(self.history):
            self.history.clear()
        else:
            del self.history[-n:]
        if clear_summaries:
            self.running_summary = None

    def replace_last_output_with_trimmed_summary(self, *, role: str, content: str, original: Any) -> None:
        """Optional helper for summarizer to apply trimmed text to running_summary.
        For MVP, we just update the running_summary; the engine already persisted the original.
        """
        self.running_summary = content

    # ------------------------------------------------------------------
    # User input queue (used by user-injection features and UserNode)
    # ------------------------------------------------------------------
    def enqueue_user_message(self, user_id: str, content: str) -> None:
        """Enqueue a user message to be consumed by user turns or injected immediately."""
        self._user_inputs.setdefault(user_id, []).append(str(content))

    def has_user_input(self, user_id: str) -> bool:
        return bool(self._user_inputs.get(user_id))

    def pop_user_input(self, user_id: str) -> Optional[str]:
        queue = self._user_inputs.get(user_id) or []
        if queue:
            return queue.pop(0)
        return None

    # ------------------------------------------------------------------
    # Budgets: per-run / per-iteration (global and per-tool-id)
    # ------------------------------------------------------------------
    def reset_iteration_counters(self) -> None:
        """Reset per-iteration counters; engine should call at each tick start."""
        self._tool_calls_iteration = 0
        self._tool_calls_iter_by_id.clear()

    def get_tool_budgets(self, tool_id: Optional[str] = None) -> Dict[str, Optional[int]]:
        """Return budget limits for tools, overlaying per-tool overrides if provided.

        Looks for global defaults at `cfg.runtime.budgets.tools` and per-tool
        overrides at the matching entry under `cfg.tools` with a `budget` block.

        Returns a dict with keys:
          per_run_min, per_run_max, per_iteration_min, per_iteration_max
        All values may be `None` (treated as unlimited / not enforced).
        """
        # Global defaults
        rt = getattr(self.cfg, "runtime", None)
        budgets = getattr(rt, "budgets", None) if rt is not None else None
        tools = getattr(budgets, "tools", None) if budgets is not None else None
        def _coerce_int(v: Any) -> Optional[int]:
            try:
                return int(v) if v is not None else None
            except Exception:
                return None
        out = {
            "per_run_min": _coerce_int(getattr(tools, "per_run_min", None) if tools is not None else None),
            "per_run_max": _coerce_int(getattr(tools, "per_run_max", None) if tools is not None else None),
            "per_iteration_min": _coerce_int(getattr(tools, "per_iteration_min", None) if tools is not None else None),
            "per_iteration_max": _coerce_int(getattr(tools, "per_iteration_max", None) if tools is not None else None),
        }

        # Per-tool overlay from cfg.tools[].budget when tool_id provided
        if tool_id:
            try:
                tool_list = getattr(self.cfg, "tools", []) or []
                for t in tool_list:
                    tid = getattr(t, "id", None)
                    if tid != tool_id:
                        continue
                    budget = getattr(t, "budget", None)
                    if budget is None:
                        break
                    for key in ("per_run_min", "per_run_max", "per_iteration_min", "per_iteration_max"):
                        val = getattr(budget, key, None)
                        if val is not None:
                            out[key] = _coerce_int(val)
                    break
            except Exception:
                # Best-effort: ignore schema inconsistencies
                pass
        return out

    def can_call_tool(self, tool_id: Optional[str] = None) -> Tuple[bool, str]:
        """Check whether the next tool call is allowed under budgets.

        If `tool_id` is provided, both global and per-tool maxima are enforced.
        Minimums are not enforced here (they're for post-run analysis or prompts).
        """
        logger = logging.getLogger(__name__)
        b = self.get_tool_budgets(tool_id)
        # Temporary debug log to inspect per-iteration counters (shared per tick)
        try:
            per_iter_total = int(getattr(self, "_tool_calls_iteration", 0))
            per_iter_tool = int(self._tool_calls_iter_by_id.get(tool_id or "", 0))
            per_run_total = int(getattr(self, "_tool_calls_run_total", 0))
            per_run_tool = int(self._tool_calls_run_by_id.get(tool_id or "", 0))
            logger.debug(
                "[budget] turn=%s tool=%s run_total=%s run_tool=%s iter_total=%s iter_tool=%s limits=%s",
                getattr(self, "iter", None), tool_id, per_run_total, per_run_tool, per_iter_total, per_iter_tool, b,
            )
        except Exception:
            pass
        # Global caps
        if b["per_run_max"] is not None and self._tool_calls_run_total >= b["per_run_max"]:
            return False, f"global per_run_max reached: {self._tool_calls_run_total}/{b['per_run_max']}"
        if b["per_iteration_max"] is not None and self._tool_calls_iteration >= b["per_iteration_max"]:
            return False, f"global per_iteration_max reached: {self._tool_calls_iteration}/{b['per_iteration_max']}"
        # Per-tool caps
        if tool_id:
            run_by_id = self._tool_calls_run_by_id.get(tool_id, 0)
            iter_by_id = self._tool_calls_iter_by_id.get(tool_id, 0)
            if b["per_run_max"] is not None and run_by_id >= b["per_run_max"]:
                return False, f"{tool_id} per_run_max reached: {run_by_id}/{b['per_run_max']}"
            if b["per_iteration_max"] is not None and iter_by_id >= b["per_iteration_max"]:
                return False, f"{tool_id} per_iteration_max reached: {iter_by_id}/{b['per_iteration_max']}"
        return True, ""

    def note_tool_call(self, tool_id: Optional[str] = None) -> None:
        """Increment counters after a tool call attempt (regardless of success)."""
        self._tool_calls_run_total += 1
        self._tool_calls_iteration += 1
        if tool_id:
            self._tool_calls_run_by_id[tool_id] = self._tool_calls_run_by_id.get(tool_id, 0) + 1
            self._tool_calls_iter_by_id[tool_id] = self._tool_calls_iter_by_id.get(tool_id, 0) + 1

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _maybe_json(content: Any) -> Any:
        if isinstance(content, (dict, list)):
            return content
        if not isinstance(content, str):
            return content
        s = content.strip()
        if not s:
            return s
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                return json.loads(s)
            except Exception:
                return content
        return content
