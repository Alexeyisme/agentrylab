from __future__ import annotations

from typing import Any, Dict, List

from .base import NodeBase, NodeOutput
from agentrylab.runtime.providers.base import Message


class UserNode(NodeBase):
    """Scheduled user node that emits the next queued user message.

    This node does not call any provider. It pops the next message from the
    state's user input queue for this node's id (cfg.id). If no message is
    available, it returns an empty content; the Engine will skip empty user
    outputs to avoid transcript noise.
    """

    role_name = "user"

    def build_messages(self, state: Any) -> List[Message]:
        # Users do not talk to providers; no messages needed.
        return []

    def postprocess(self, raw: Dict[str, Any], state: Any) -> NodeOutput:  # pragma: no cover
        # Not used; we never call providers for UserNode.
        return NodeOutput(role=self.role_name, content="")

    def validate(self, out: NodeOutput, state: Any) -> None:  # pragma: no cover
        return

    def __call__(self, state: Any) -> NodeOutput:
        user_id = getattr(self.cfg, "id", "user")
        try:
            content = state.pop_user_input(user_id)  # type: ignore[attr-defined]
        except Exception:
            content = None
        text = content if isinstance(content, str) else ""
        return NodeOutput(role=self.role_name, content=text)

