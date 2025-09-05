from __future__ import annotations
from typing import Any, Dict, Type, Union
import logging
from .base import NodeBase
from .agent import AgentNode
from .moderator import ModeratorNode
from .summarizer import SummarizerNode
from .advisor import AdvisorNode
from .user import UserNode

ROLE_TO_NODE: Dict[str, Type[NodeBase]] = {
    "agent": AgentNode,
    "moderator": ModeratorNode,
    "summarizer": SummarizerNode,
    "advisor": AdvisorNode,
    "user": UserNode,
}

# Type alias for returned node
NodeType = Union[AgentNode, ModeratorNode, SummarizerNode, AdvisorNode]

def make_node(cfg: Any, provider: Any, tools: Dict[str, Any]) -> NodeType:
    """
    Factory: instantiate a Node based on its role.
    Args:
        cfg: Pydantic config object for the node (must have role attr)
        provider: bound LLMProvider instance
        tools: dict of available tools keyed by tool id
    Returns:
        A node instance of the appropriate subclass.
    """
    role = getattr(cfg, "role", None)
    if role not in ROLE_TO_NODE:
        logging.getLogger(__name__).error("Unknown or unsupported role '%s' for node id '%s'", role, getattr(cfg, "id", "?"))
        raise ValueError(f"Unknown or unsupported role: {role!r}")
    node_cls = ROLE_TO_NODE[role]
    return node_cls(cfg=cfg, provider=provider, tools=tools)
