from __future__ import annotations

from typing import Any, Dict

from .base import NodeBase, NodeOutput


class UserNode(NodeBase):
    """Scheduled user turn that emits the next queued user message."""

    role_name = "user"

    def __init__(self, cfg: Any, provider: Any = None, tools: Dict[str, Any] | None = None):
        # User nodes don't call a provider; store references for API parity
        self.cfg = cfg
        self.provider = provider
        self.tools = tools or {}

    def __call__(self, state: Any) -> NodeOutput:  # type: ignore[override]
        msg = None
        if hasattr(state, "pop_user_input"):
            try:
                msg = state.pop_user_input(getattr(self.cfg, "id", "user"))
            except Exception:
                msg = None
        if msg is None:
            msg = ""
        return NodeOutput(role="user", content=str(msg))

    # Unused abstract hooks -------------------------------------------------
    def build_messages(self, state: Any):  # pragma: no cover - not used
        return []

    def postprocess(self, raw: Dict[str, Any], state: Any):  # pragma: no cover - not used
        raise NotImplementedError

    def validate(self, out: NodeOutput, state: Any) -> None:  # pragma: no cover - not used
        return
