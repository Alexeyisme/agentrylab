from __future__ import annotations
from typing import List

from .base import Scheduler


class RoundRobinScheduler(Scheduler):
    """
    Scheduler that cycles through a fixed order of agents, one per turn.

    Example:
        order = ["pro", "con", "moderator"]
        turn 0 -> ["pro"]
        turn 1 -> ["con"]
        turn 2 -> ["moderator"]
        turn 3 -> ["pro"]
    """

    def __init__(self, order: List[str]):
        """
        Args:
            order: explicit agent order (list of agent IDs).
        """
        super().__init__(order=order)
        if not order:
            raise ValueError("RoundRobinScheduler requires a non-empty order list")
        self.order: List[str] = list(order)

    def configure(self, *, agents: List[str]) -> None:
        """
        Ensure the order only contains agents that are active.
        """
        super().configure(agents=agents)
        self.order = [a for a in self.order if a in agents]

    def reset(self) -> None:
        """
        No state to reset; order is static.
        """
        return

    def next(self, turn_idx: int, agents: List[str]) -> List[str]:
        if not self.order:
            return []
        idx = turn_idx % len(self.order)
        return [self.order[idx]]