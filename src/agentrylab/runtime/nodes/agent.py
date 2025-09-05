from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from agentrylab.runtime.providers.base import Message
from .base import NodeBase, NodeOutput
from agentrylab.utils.urls import extract_urls, merge_citations


TOOL_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```", re.IGNORECASE)


class AgentNode(NodeBase):
    """Conversational agent node with best-effort tool execution.

    Protocol for tool calls (any of the following in the model output):
      1) Single object: {"tool": "<tool_id>", "args": {...}}
      2) List under known keys: {"tools": [{...}, ...]} or {"tool_calls": [{...}, ...]}
      3) Same JSON wrapped inside a fenced code block (```json ... ```)

    Each tool call result is appended as a `{"role": "tool", "content": "{...}"}` message
    using `tool_result_to_message`, and then the provider is called again so the model can
    use the results to produce the final assistant content.
    """

    role_name = "agent"

    # ------------------------- NodeBase hooks -------------------------
    def build_messages(self, state: Any) -> List[Message]:
        return state.compose_messages(self.cfg, role_hint=self.role_name)

    def postprocess(self, raw: Dict[str, Any], state: Any) -> NodeOutput:
        content, meta = state.extract_content_and_metadata(raw, expect_json=False)
        return NodeOutput(role=self.role_name, content=content, metadata=meta)

    def validate(self, out: NodeOutput, state: Any) -> None:
        state.contracts.validate_agent_output(out, self.cfg)

    def llm_params(self, state: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        temp = getattr(self.cfg, "temperature", None)
        if temp is not None:
            params["temperature"] = temp
        return params

    # ---------------------------- Orchestration ----------------------------
    def __call__(self, state: Any) -> NodeOutput:
        messages = self.build_messages(state)
        raw = self.provider_chat(messages, **self.llm_params(state))

        # Collect citations from tool results to satisfy message_contract
        collected_citations: List[str] = []

        # Try tool loop if the model requested tools
        max_iters = int(getattr(self.cfg, "tool_max_iters", 2) or 2)
        allow_parallel = bool(getattr(self.cfg, "allow_parallel_tools", True))
        fail_open = bool(getattr(self.cfg, "fail_open_on_tool_error", False))

        parsed = self._parse_tool_calls(raw)
        iters = 0
        first_error_msg: Optional[str] = None
        while parsed and iters < max_iters:
            iters += 1

            tool_calls = parsed
            if not allow_parallel:
                tool_calls = tool_calls[:1]

            # Add the assistant message that contained the tool request
            assistant_content, _ = state.extract_content_and_metadata(raw, expect_json=False)
            messages.append(Message(role="assistant", content=str(assistant_content)))

            # Execute tools and append tool messages
            any_error = False
            for call in tool_calls:
                tool_id = call.get("tool")
                args = call.get("args", {}) if isinstance(call.get("args"), dict) else {}
                if not tool_id or not isinstance(tool_id, str):
                    continue
                if not self.has_tool(tool_id):
                    any_error = True
                    tool_msg = Message(role="tool", content=str({
                        "tool": tool_id,
                        "status": "error",
                        "error": f"unknown tool: {tool_id}",
                    }))
                    messages.append(tool_msg)
                    continue
                # Forward runtime state for budget checks and counter increments
                result = self.call_tool(tool_id, _state=state, **args)
                if not bool(result.get("ok", False)):
                    any_error = True
                    if first_error_msg is None:
                        em = result.get("error") if isinstance(result, dict) else None
                        if isinstance(em, str):
                            first_error_msg = em
                # Merge citations from tool meta if present
                meta = result.get("meta") if isinstance(result, dict) else None
                if isinstance(meta, dict):
                    cites = meta.get("citations")
                    if isinstance(cites, list):
                        for u in cites:
                            if isinstance(u, str):
                                collected_citations.append(u)
                messages.append(self.tool_result_to_message(tool_id, result))

            if any_error and not fail_open:
                # Surface the error as a regular assistant output and stop
                detail = f" Tool error: {first_error_msg}." if first_error_msg else ""
                return NodeOutput(
                    role=self.role_name,
                    content=f"One or more tool calls failed and fail_open_on_tool_error is False.{detail}",
                    metadata=None,
                )

            # Ask the model again with tool outputs
            raw = self.provider_chat(messages, **self.llm_params(state))
            parsed = self._parse_tool_calls(raw)

        # Either no tools requested or loop finished → finalize
        out = self.postprocess(raw, state)
        # Merge tool citations and, if still empty, extract URLs from content as a fallback
        existing = []
        if out.metadata and isinstance(out.metadata, dict):
            ex = out.metadata.get("citations")
            if isinstance(ex, list):
                existing = [x for x in ex if isinstance(x, str)]
        extracted: List[str] = extract_urls(out.content) if isinstance(out.content, str) else []
        merged = merge_citations(existing, collected_citations, extracted)
        if merged:
            new_meta = dict(out.metadata or {})
            new_meta["citations"] = merged
            out = NodeOutput(role=self.role_name, content=out.content, metadata=new_meta)
        self.validate(out, state)
        return out

    # -------------------------- Tool call parsing --------------------------
    def _parse_tool_calls(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return list of {"tool": str, "args": dict} parsed from provider output.

        Supports top-level dict, lists under `tools` or `tool_calls`, or JSON found in
        fenced blocks within a string `content`.
        """
        # 1) If provider already returned a dict with tool directives
        if isinstance(raw, dict):
            # Direct single tool call
            if raw.get("tool") and isinstance(raw.get("tool"), str):
                args = raw.get("args") if isinstance(raw.get("args"), dict) else {}
                return [{"tool": raw["tool"], "args": args}]
            # List forms under known keys
            for key in ("tools", "tool_calls"):
                calls = raw.get(key)
                parsed = self._normalize_calls_list(calls)
                if parsed:
                    return parsed

        # 2) Try to parse JSON from content string (including fenced code blocks)
        content, _ = self._safe_extract_text(raw)
        if content:
            # Look for fenced JSON first
            for match in TOOL_JSON_FENCE.finditer(content):
                obj = self._json_or_none(match.group(1))
                parsed = self._normalize_any(obj)
                if parsed:
                    return parsed
            # Try raw content as JSON
            obj = self._json_or_none(content)
            parsed = self._normalize_any(obj)
            if parsed:
                return parsed

        return []

    def _normalize_any(self, obj: Any) -> List[Dict[str, Any]]:
        if isinstance(obj, dict):
            if obj.get("tool") and isinstance(obj.get("tool"), str):
                args = obj.get("args") if isinstance(obj.get("args"), dict) else {}
                return [{"tool": obj["tool"], "args": args}]
            for key in ("tools", "tool_calls"):
                parsed = self._normalize_calls_list(obj.get(key))
                if parsed:
                    return parsed
        elif isinstance(obj, list):
            return self._normalize_calls_list(obj)
        return []

    def _normalize_calls_list(self, calls: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if isinstance(calls, list):
            for c in calls:
                if isinstance(c, dict) and isinstance(c.get("tool"), str):
                    args = c.get("args") if isinstance(c.get("args"), dict) else {}
                    out.append({"tool": c["tool"], "args": args})
        return out

    def _safe_extract_text(self, raw: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Extract best-effort text from a provider response without relying on `state`.

        Supports common shapes: top-level `content`, OpenAI-like `choices[0].message.content`,
        Ollama-like `message.content`, and generic list-of-blocks with text fields.
        Returns (text, None) where text may be None if nothing is found.
        """
        if not isinstance(raw, dict):
            return (None, None)
        # direct
        cnt = raw.get("content")
        if isinstance(cnt, str):
            return (cnt, None)
        # OpenAI-like
        choices = raw.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(msg, dict):
                c = msg.get("content")
                if isinstance(c, str):
                    return (c, None)
        # Ollama-like
        msg = raw.get("message")
        if isinstance(msg, dict):
            c = msg.get("content")
            if isinstance(c, str):
                return (c, None)
        # Generic list-of-blocks
        if isinstance(cnt, list):
            parts: List[str] = []
            for item in cnt:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    for k in ("text", "value", "content"):
                        v = item.get(k)
                        if isinstance(v, str):
                            parts.append(v)
                            break
            if parts:
                return ("\n".join(parts), None)
        return (None, None)

    @staticmethod
    def _json_or_none(text: str) -> Any:
        try:
            return json.loads(text)
        except Exception:
            return None
