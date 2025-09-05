from __future__ import annotations

from typing import Any, Dict, List
import jsonschema

from agentrylab.runtime.providers.base import Message
from agentrylab.runtime.actions import CONTINUE, STOP, STEP_BACK
from .base import NodeBase, NodeOutput


# JSON contract matching the preset's moderator output
MOD_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "drift": {"type": "number"},
        "action": {"enum": [CONTINUE, STOP, STEP_BACK]},
        "rollback": {"type": "integer", "minimum": 0},
        "citations": {"type": "array", "items": {"type": "string", "format": "uri"}},
        "clear_summaries": {"type": "boolean"},
    },
    "required": ["summary", "drift", "action", "rollback", "citations"],
    "additionalProperties": False,
}


class ModeratorNode(NodeBase):
    """Policy/controller node that emits control actions and a structured summary.

    The model is expected to respond **only with JSON** that validates against
    `MOD_SCHEMA`. We keep the raw JSON in `content` and translate the control
    portion into `actions` for the engine.
    """

    role_name = "moderator"

    # ------------------------- NodeBase hooks -------------------------
    def build_messages(self, state: Any) -> List[Message]:
        return state.compose_messages(self.cfg, role_hint=self.role_name)

    def postprocess(self, raw: Dict[str, Any], state: Any) -> NodeOutput:
        payload = state.parse_json_response(raw)  # enforce JSON-only moderator
        # Fill required defaults if the model omitted them
        if "rollback" not in payload or not isinstance(payload.get("rollback"), int):
            payload["rollback"] = 0
        if "citations" not in payload or not isinstance(payload.get("citations"), list):
            payload["citations"] = []
        if "action" not in payload or payload.get("action") not in (CONTINUE, STOP, STEP_BACK):
            payload["action"] = CONTINUE

        # Actions for the engine to interpret
        actions = {
            "type": payload.get("action"),
            "rollback": payload.get("rollback", 0),
            "clear_summaries": payload.get("clear_summaries", False),
        }
        return NodeOutput(role=self.role_name, content=payload, actions=actions)

    def validate(self, out: NodeOutput, state: Any) -> None:
        jsonschema.validate(out.content, MOD_SCHEMA)

    def llm_params(self, state: Any) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        temp = getattr(self.cfg, "temperature", None)
        if temp is not None:
            params["temperature"] = temp
        return params
