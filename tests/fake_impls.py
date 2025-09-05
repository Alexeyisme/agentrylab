from __future__ import annotations

from typing import Any, Dict, List, Optional, Mapping

from agentrylab.runtime.providers.base import LLMProvider, Message
from agentrylab.runtime.tools.base import Tool, ToolResult


class TestProvider(LLMProvider):
    __test__ = False  # prevent pytest from collecting as a test
    """Deterministic provider for tests.

    Behavior hints via system prompt content (first system message):
    - contains the word "moderator" or "Respond ONLY with JSON" -> emit moderator JSON
    - contains the word "summarizer" -> emit plain summary text
    - otherwise:
        * first call: ask for a tool if content mentions TOOL_REQUEST
        * subsequent calls: return final assistant content
    """

    def _send_chat(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        # record last messages for tests
        try:
            self.last_messages = list(messages)  # type: ignore[attr-defined]
        except Exception:
            pass
        system = ""
        if messages:
            for m in messages:
                if m.get("role") == "system":
                    system = m.get("content", "")
                    break
        # Moderator JSON
        sys_l = (system or "").lower()
        if "respond only with json" in sys_l or "moderator" in sys_l:
            payload = {
                "summary": "Round check OK.",
                "drift": 0.05,
                "action": "CONTINUE",
                "rollback": 0,
                "citations": ["https://example.org/evidence"],
                "clear_summaries": False,
            }
            return {"content": payload}
        # Summarizer plain text
        if "summarizer" in sys_l:
            return {"content": "Concise summary of the session."}

        # Agent behavior: if last assistant message requested tools, produce final text
        # If first call (no assistant in messages yet), emit a single tool request
        saw_assistant = any(m.get("role") == "assistant" for m in messages)
        if not saw_assistant:
            # ask for echo tool
            return {"content": '{"tool":"echo","args":{"text":"hello"}}'}
        # After tool results, respond with final content
        return {"content": "Agent final answer with citations."}


class EchoTool(Tool):
    __test__ = False
    """Simple tool that echoes text and adds a test citation."""

    def run(self, **kwargs: Any) -> ToolResult:
        text = kwargs.get("text", "")
        return {
            "ok": True,
            "data": {"echo": str(text)},
            "meta": {"citations": ["https://example.com/source"]},
        }
