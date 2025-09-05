from __future__ import annotations

from typing import Any, Dict, List, Optional

from agentrylab.runtime.providers.base import Message
from .base import NodeBase, NodeOutput


class AdvisorNode(NodeBase):
    """Non-blocking advisory node.

    Advisors provide side-channel critiques/suggestions that do not control
    the engine's flow. Their outputs are for UX and optional guidance.
    """

    role_name = "advisor"

    def __init__(self, cfg: Any, provider, tools: Dict[str, Any]):
        super().__init__(cfg, provider, tools)
        if tools:
            import logging
            logging.getLogger(__name__).info(
                "Advisor '%s' configured with tools %s (advisors do not execute tools)",
                getattr(cfg, "id", "advisor"), list(tools.keys()),
            )

    # ------------------------- NodeBase hooks -------------------------
    def build_messages(self, state: Any) -> List[Message]:
        # Advisors usually see the same (or slightly reduced) context as agents
        return state.compose_messages(self.cfg, role_hint=self.role_name)

    def postprocess(self, raw: Dict[str, Any], state: Any) -> NodeOutput:
        content, meta = state.extract_content_and_metadata(raw, expect_json=False)
        return NodeOutput(role=self.role_name, content=content, metadata=meta)

    def validate(self, out: NodeOutput, state: Any) -> None:
        # Optional policy checks if present
        if hasattr(state, "contracts") and hasattr(state.contracts, "validate_advisor_output"):
            state.contracts.validate_advisor_output(out, self.cfg)

    def llm_params(self, state: Any) -> Dict[str, Any]:
        # Advisors are often low-temperature to be precise and concise
        params: Dict[str, Any] = {}
        temp = getattr(self.cfg, "temperature", None)
        if temp is not None:
            params["temperature"] = temp
        return params
