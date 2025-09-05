from __future__ import annotations

from typing import Any, Dict, List, Optional

from agentrylab.runtime.providers.base import Message
from .base import NodeBase, NodeOutput


class SummarizerNode(NodeBase):
    """Summarizer node: produces concise running summaries.

    Responsibilities:
      • Build messages from state with a summarizer-specific system prompt.
      • Call provider once; no tool execution by default.
      • Validate optional constraints (length/neutrality) if configured in cfg.
    """

    role_name = "summarizer"

    # ------------------------- NodeBase hooks -------------------------
    def build_messages(self, state: Any) -> List[Message]:
        # Often use reduced history / running summaries
        return state.compose_messages(self.cfg, role_hint=self.role_name)

    def postprocess(self, raw: Dict[str, Any], state: Any) -> NodeOutput:
        content, meta = state.extract_content_and_metadata(raw, expect_json=False)
        return NodeOutput(role=self.role_name, content=content, metadata=meta)

    def validate(self, out: NodeOutput, state: Any) -> None:
        # Optional: enforce length/neutrality caps from config
        max_chars: Optional[int] = getattr(self.cfg, "max_summary_chars", None)
        if isinstance(max_chars, int) and max_chars > 0 and isinstance(out.content, str):
            if len(out.content) > max_chars:
                # Truncate overly long summaries deterministically
                trimmed = out.content[: max_chars].rstrip()
                # NOTE: We rewrap into a new NodeOutput to keep dataclass frozen semantics
                state.replace_last_output_with_trimmed_summary(
                    role=self.role_name,
                    content=trimmed,
                    original=out,
                )
        # Additional policy checks may live in state.contracts if desired
        if hasattr(state, "contracts") and hasattr(state.contracts, "validate_summary_output"):
            state.contracts.validate_summary_output(out, self.cfg)

    def llm_params(self, state: Any) -> Dict[str, Any]:
        # Summaries typically deterministic & concise
        params: Dict[str, Any] = {}
        temp = getattr(self.cfg, "temperature", None)
        if temp is not None:
            params["temperature"] = temp
        return params
    