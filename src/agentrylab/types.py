from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict


class Event(TypedDict, total=False):
    """Transcript event shape emitted by the Engine and stores.

    Keys:
      t: Unix timestamp (float seconds)
      iter: Iteration index (int)
      agent_id: Node id that produced the output
      role: Logical role ("agent" | "moderator" | "summarizer" | "advisor")
      content: Text or dict payload
      metadata: Optional metadata dict (citations, usage, provider info)
      actions: Optional control action dict (for moderator)
      latency_ms: Optional latency in milliseconds for the node call
    """

    t: float
    iter: int
    agent_id: str
    role: str
    content: Any
    metadata: Optional[Dict[str, Any]]
    actions: Optional[Dict[str, Any]]
    latency_ms: float


class ProgressInfo(TypedDict, total=False):
    iter: int
    elapsed_s: float
