from __future__ import annotations
from typing import Dict, List, Any

from .base import Scheduler


class EveryNScheduler(Scheduler):
    """
    Scheduler that triggers each agent every N turns.

    Accepts either of the following schedule shapes:
      - Mapping agent_id -> int (where the int is `every_n`), e.g. {"pro": 1, "moderator": 2}
      - Mapping agent_id -> dict, with keys: {every_n:int, run_on_last?:bool, non_blocking?:bool}

    It also tolerates the Engine passing a top-level schedule list of entries
    like [{id:"pro", every_n:1, ...}], and will normalize it internally.
    """

    def __init__(self, schedule: Dict[str, Any]):
        super().__init__(schedule=schedule)
        self.schedule: Dict[str, Dict[str, Any]] = {}
        self.update_schedule(schedule)

    # Normalize and set internal schedule
    def update_schedule(self, schedule: Dict[str, Any]) -> None:
        normalized: Dict[str, Dict[str, Any]] = {}
        for agent, cfg in (schedule or {}).items():
            if isinstance(cfg, int):
                normalized[agent] = {"every_n": int(cfg)}
            elif isinstance(cfg, dict):
                d = dict(cfg)
                # If someone passed just a number under an unknown key, try to coerce
                if "every_n" not in d and len(d) == 1:
                    try:
                        only_val = next(iter(d.values()))
                        if isinstance(only_val, int):
                            d["every_n"] = only_val
                    except Exception:
                        pass
                normalized[agent] = d
        self.schedule = normalized

    def configure(self, *, agents: List[str], schedule: Any = None) -> None:  # type: ignore[override]
        """Engine calls this before first turn.

        We ignore `agents` for cadence logic but accept an optional `schedule` which may be:
          - dict-of-int or dict-of-dict (as above), or
          - list of entries with keys (id, every_n, run_on_last, non_blocking)
        """
        super().configure(agents=agents)
        if schedule is None:
            # Fallback: ensure we at least keep constructor-provided mapping
            if not getattr(self, "schedule", {}):
                init_map = self.params.get("schedule") if isinstance(self.params, dict) else None
                if isinstance(init_map, dict):
                    self.update_schedule(init_map)
            return
        if isinstance(schedule, list):
            # Convert array of entries into mapping
            m: Dict[str, Dict[str, Any]] = {}
            for ent in schedule:
                if not isinstance(ent, dict):
                    continue
                aid = ent.get("id")
                if not isinstance(aid, str):
                    continue
                d: Dict[str, Any] = {}
                if isinstance(ent.get("every_n"), int):
                    d["every_n"] = ent["every_n"]
                if isinstance(ent.get("run_on_last"), bool):
                    d["run_on_last"] = ent["run_on_last"]
                if isinstance(ent.get("non_blocking"), bool):
                    d["non_blocking"] = ent["non_blocking"]
                if d:
                    m[aid] = d
            self.update_schedule(m)
        elif isinstance(schedule, dict):
            self.update_schedule(schedule)
        # If normalization resulted in an empty schedule, fall back to constructor params
        if not self.schedule:
            init_map = self.params.get("schedule") if isinstance(self.params, dict) else None
            if isinstance(init_map, dict):
                self.update_schedule(init_map)

    def next(self, turn_idx: int, agents: List[str]) -> List[str]:
        result: List[str] = []
        for agent in agents:
            cfg = self.schedule.get(agent, {})
            n = 0
            if isinstance(cfg, dict):
                n = int(cfg.get("every_n", 0) or 0)
            elif isinstance(cfg, int):
                n = int(cfg)
            if n > 0 and (turn_idx + 1) % n == 0:
                result.append(agent)
        return result

    def should_run_on_last(self, agent_id: str) -> bool:
        cfg = self.schedule.get(agent_id, {})
        if isinstance(cfg, dict):
            return bool(cfg.get("run_on_last", False))
        return False

    def is_non_blocking(self, agent_id: str) -> bool:
        cfg = self.schedule.get(agent_id, {})
        if isinstance(cfg, dict):
            return bool(cfg.get("non_blocking", False))
        return False
