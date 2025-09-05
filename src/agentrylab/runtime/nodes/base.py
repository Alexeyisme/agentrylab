from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, TypedDict, Literal, Union

from agentrylab.runtime.providers.base import LLMProvider, Message
from agentrylab.logging import emit_trace
from agentrylab.runtime.tools.base import Tool, ToolResult, ToolError


logger = logging.getLogger(__name__)


# ----------------------------- Types ---------------------------------------
Role = Literal["agent", "moderator", "summarizer", "advisor"]

class NodeAction(TypedDict, total=False):
    """Control signals emitted by nodes (primarily Moderator)."""
    type: Literal["CONTINUE", "STOP", "STEP_BACK"]
    rollback: int
    clear_summaries: bool

class NodeMetadata(TypedDict, total=False):
    """Lightweight, discoverable metadata attached to a node's output."""
    citations: List[str]
    usage: Mapping[str, Any]
    provider: str
    model: str
    extra: Mapping[str, Any]

Content = Union[str, Dict[str, Any]]


@dataclass(frozen=True)
class NodeOutput:
    """Normalized output from any node.

    - `content` is text for Agents/Summarizer, JSON dict for Moderator (by design).
    - `metadata` can carry citations, usage, etc.
    - `actions` can instruct the Engine to STOP/STEP_BACK/etc.
    """
    role: Role
    content: Content
    metadata: Optional[NodeMetadata] = None
    actions: Optional[NodeAction] = None


class NodeBase(ABC):
    """Strict abstract base for all nodes (Agent, Moderator, Summarizer, Advisor).

    Subclasses implement the message construction, postprocessing, and validation
    for their specific role. The base orchestrates a single provider call.
    """

    role_name: Role

    def __init__(self, cfg: Any, provider: LLMProvider, tools: Dict[str, Tool]):
        self.cfg = cfg
        self.provider = provider
        self.tools = tools  # mapping of tool_id -> Tool instance
        logger.debug("Initialized %s with provider=%s, tools=%s", self.__class__.__name__, provider, list(tools.keys()))

    def __call__(self, state: Any) -> NodeOutput:
        """Execute the node once within the given runtime state."""
        messages: List[Message] = self.build_messages(state)
        logger.debug("[%s] Built %d messages", getattr(self, "role_name", "?"), len(messages))
        raw = self.provider_chat(messages, **self.llm_params(state))
        logger.debug("[%s] Provider returned payload keys: %s", getattr(self, "role_name", "?"), list(raw.keys()) if isinstance(raw, dict) else type(raw))
        # Trace and log whether provider returned any textual content
        node_id = getattr(self.cfg, "id", "?")
        content_len = -1
        try:
            preview, _ = state.extract_content_and_metadata(raw, expect_json=False)
            text = preview if isinstance(preview, str) else ""
            content_len = len(text)
        except Exception:
            content_len = -1
        emit_trace("provider_result", node_id=node_id, role=getattr(self, "role_name", "?"), content_len=max(0, content_len))
        if content_len <= 0:
            logger.debug("[%s:%s] provider returned empty content", getattr(self, "role_name", "?"), node_id)
        out = self.postprocess(raw, state)
        logger.debug("[%s] Postprocessed output: role=%s, has_meta=%s, has_actions=%s", getattr(self, "role_name", "?"), out.role, bool(out.metadata), bool(out.actions))
        self.validate(out, state)
        logger.debug("[%s] Validation complete", getattr(self, "role_name", "?"))
        return out

    # --------------------- Provider & Tool helpers -------------------------
    def provider_chat(self, messages: List[Message], **kwargs: Any) -> Dict[str, Any]:
        """Call the underlying LLM provider.

        Subclasses can override to inject provider-specific kwargs (e.g., tools schema)
        or tracing. By default, delegates to `self.provider.chat(...)`.
        """
        return self.provider.chat(messages, **kwargs)

    def has_tool(self, tool_id: str) -> bool:
        return tool_id in self.tools

    def get_tool(self, tool_id: str) -> Tool:
        try:
            return self.tools[tool_id]
        except KeyError as e:
            raise KeyError(f"Unknown tool id: {tool_id}") from e

    def call_tool(self, tool_id: str, **kwargs: Any) -> ToolResult:
        """Execute a tool by id and return its normalized ToolResult envelope.

        Tool-level retries/backoff are handled by the Tool base class.
        """
        # Pull state for budget enforcement; do not forward to tool
        state = kwargs.pop("_state", None)

        # Budget check (global + per-tool) if State provides helpers
        if state is not None and hasattr(state, "can_call_tool"):
            try:
                allowed, reason = state.can_call_tool(tool_id)
            except TypeError:
                # Backward-compat: older signature with no args
                allowed, reason = state.can_call_tool()  # type: ignore[misc]
            if not allowed:
                logger.warning(
                    "[%s] Tool budget exceeded for %s: %s",
                    getattr(self, "role_name", "?"),
                    tool_id,
                    reason,
                )
                return {  # type: ignore[return-value]
                    "ok": False,
                    "data": None,
                    "error": f"tool-budget-exceeded: {reason}",
                }

        tool = self.get_tool(tool_id)
        logger.info("[%s] Calling tool %s with args=%s", getattr(self, "role_name", "?"), tool_id, kwargs)

        # Note attempt after passing budget check
        if state is not None and hasattr(state, "note_tool_call"):
            try:
                state.note_tool_call(tool_id)
            except TypeError:
                # Backward-compat: older signature with no args
                state.note_tool_call()  # type: ignore[misc]

        result = tool(**kwargs)
        logger.info("[%s] Tool %s returned ok=%s", getattr(self, "role_name", "?"), tool_id, result.get("ok"))
        return result

    def tool_result_to_message(self, tool_id: str, result: ToolResult) -> Message:
        """Convert a ToolResult into a provider-ready tool message.

        This constructs an assistant-tool style message the provider can consume
        on the next call. Exact shape can be adapted to your provider's tool-calling
        format; by default we emit a generic 'tool' role message.
        """
        # compact string for LLM consumption; keep structured data in state separately
        status = "ok" if bool(result.get("ok", False)) else "error"
        payload = {
            "tool": tool_id,
            "status": status,
            "data": result.get("data"),
            "error": result.get("error"),
        }
        return Message(role="tool", content=str(payload))

    # --------------------- Abstract & overridable hooks ---------------------
    @abstractmethod
    def build_messages(self, state: Any) -> List[Message]:
        """Compose the provider-ready chat messages for this node."""
        ...

    @abstractmethod
    def postprocess(self, raw: Dict[str, Any], state: Any) -> NodeOutput:
        """Transform a raw provider response into a `NodeOutput`."""
        ...

    @abstractmethod
    def validate(self, out: NodeOutput, state: Any) -> None:
        """Enforce role-specific contracts (schemas, policies)."""
        ...

    def llm_params(self, state: Any) -> Dict[str, Any]:
        """Optional provider call kwargs (e.g., temperature, tool configs)."""
        return {}
