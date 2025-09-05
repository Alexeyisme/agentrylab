from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

AgentId = str

class Scheduler(ABC):
    """Abstract scheduler interface.

    Implementations decide which agent(s) should act on each turn.
    Schedulers MAY be stateless (pure function of `turn_idx` and `agents`) or
    stateful (keeping internal pointers, windows, etc.).

    Engine contract:
      • Engine will call `configure(agents=...)` once before the first `next()`.
      • On each iteration, engine calls `next(turn_idx, agents)` to get an ordered
        list of agent IDs to run for that turn. Return an empty list to skip.
      • Engine MAY call `reset()` between runs/threads.
      • Engine MAY call `update(**params)` if the schedule must change at runtime.
    """

    def __init__(self, **params: Any) -> None:
        # Store constructor params for visibility / debugging in concrete impls
        self.params: Dict[str, Any] = dict(params)
        self._agents: List[AgentId] = []

    # ----- Lifecycle -----------------------------------------------------
    def configure(self, *, agents: List[AgentId]) -> None:
        """Called once before the first turn; gives the scheduler the agent list.
        Implementations can validate/normalize internal state here.
        """
        self._agents = list(agents)

    def reset(self) -> None:
        """Optional: clear any internal state (useful for reusing instances)."""
        # Default is stateless; stateful schedulers should override.
        pass

    def update(self, **params: Any) -> None:
        """Optional: update scheduler parameters at runtime.
        Default merges new params into `self.params`.
        """
        self.params.update(params)

    # ----- Core decision API --------------------------------------------
    @abstractmethod
    def next(self, turn_idx: int, agents: List[AgentId]) -> List[AgentId]:
        """Return an ordered list of agent IDs to run on `turn_idx`.

        Args:
            turn_idx: Current iteration index (0-based).
            agents: Current list of agent IDs (engine-provided; may change if
                     agents are dynamically enabled/disabled).
        Returns:
            Ordered list of agent IDs for this turn. May be empty to skip.
        """
        ...

    # ----- Introspection -------------------------------------------------
    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.name}(params={self.params!r}, agents={self._agents!r})"