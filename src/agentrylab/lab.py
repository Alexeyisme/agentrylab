from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid
import time
import importlib
import logging

# Config & builders
from agentrylab.config.loader import load_config  # expects Preset-like object
# Engine & runtime
from agentrylab.runtime.engine import Engine
from agentrylab.runtime.state import State
from agentrylab.runtime.scheduler.base import Scheduler
from agentrylab.runtime.providers.base import LLMProvider  # protocol/ABC
from agentrylab.runtime.tools.base import Tool
from agentrylab.runtime.nodes.factory import make_node
# Persistence
from agentrylab.persistence.store import Store  # facade that wraps checkpoints + transcript


# ---------- Public types ----------
@dataclass(frozen=True)
class LabStatus:
    thread_id: str
    is_active: bool
    iter: int
    last_message_at: Optional[float]
    summary: Optional[str]  # up to you: running summary or last moderator summary


# ---------- Public API ----------
class Lab:
    """
    Thin façade over the runtime. Owns one thread/run.
    """
    def __init__(self, cfg: Any, *, thread_id: Optional[str] = None, resume: bool = True):
        self.cfg = cfg
        self.thread_id = thread_id or _new_thread_id(cfg)
        self.store: Store = _build_store(cfg)

        # Build providers/tools registries
        self.providers: Dict[str, LLMProvider] = _build_providers(cfg)
        self.tools: Dict[str, Tool] = _build_tools(cfg)

        # Build nodes from agents/advisors/moderator/summarizer
        nodes: Dict[str, Any] = {}

        def _add_node(node_cfg: Any) -> None:
            node_id = getattr(node_cfg, "id", None)
            if not node_id:
                raise ValueError("Each node must have an 'id'")
            if node_id in nodes:
                raise ValueError(f"Duplicate node id detected: {node_id}")
            prov_key = getattr(node_cfg, "provider")
            if prov_key not in self.providers:
                raise ValueError(f"Unknown provider id '{prov_key}' for node '{node_id}'")
            provider = self.providers[prov_key]
            tool_ids = getattr(node_cfg, "tools", []) or []
            missing = [tid for tid in tool_ids if tid not in self.tools]
            if missing:
                raise ValueError(
                    f"Node '{node_id}' references unknown tool id(s): {missing}. Define them in preset.tools."
                )
            bound_tools = {tid: self.tools[tid] for tid in tool_ids}
            nodes[node_id] = make_node(node_cfg, provider, bound_tools)

        for agent_cfg in getattr(cfg, "agents", []) or []:
            _add_node(agent_cfg)

        for adv_cfg in getattr(cfg, "advisors", []) or []:
            _add_node(adv_cfg)

        if getattr(cfg, "moderator", None) is not None:
            _add_node(cfg.moderator)

        if getattr(cfg, "summarizer", None) is not None:
            _add_node(cfg.summarizer)

        # Scheduler
        self.scheduler: Scheduler = _build_scheduler(cfg)

        # State & engine
        self.state = State(thread_id=self.thread_id, cfg=cfg)
        # Attempt to resume from checkpoint (best-effort; controlled by flag)
        if resume:
            try:
                snapshot = self.store.load_checkpoint(self.thread_id)
            except Exception:
                snapshot = None
            if isinstance(snapshot, dict) and snapshot and "_pickled" not in snapshot:
                protected = {"thread_id", "cfg"}
                for k, v in snapshot.items():
                    if k in protected:
                        continue
                    try:
                        setattr(self.state, k, v)
                    except Exception:
                        pass
                logging.getLogger(__name__).info(
                    "Resumed thread %s: iter=%s history_len=%s",
                    self.thread_id,
                    getattr(self.state, "iter", None),
                    len(getattr(self.state, "history", []) or []),
                )
        self.engine = Engine(
            preset_cfg=cfg,
            nodes=nodes,
            scheduler=self.scheduler,
            store=self.store,
            state=self.state,
        )

        self._active = False
        self._last_ts: Optional[float] = None

    # -------- lifecycle --------
    def start(self, *, max_iters: Optional[int] = None) -> LabStatus:
        """
        Run until max_iters or engine stop flag. Idempotent if already active.
        """
        if self._active is False:
            self._active = True

        target_iters = (self.state.iter + max_iters) if max_iters is not None else None

        while self._active:
            if target_iters is not None and self.state.iter >= target_iters:
                break
            if getattr(self.state, "stop_flag", False):
                break

            self.engine.tick()  # one scheduler slice; handles nodes, actions, persistence
            self._last_ts = time.time()

        return self.get_status()

    # -------- ergonomic Python API --------
    def run(
        self,
        *,
        rounds: Optional[int] = None,
        stream: bool = False,
        on_event: Optional[callable] = None,
        timeout_s: Optional[float] = None,
        stop_when: Optional[callable] = None,
        on_tick: Optional[callable] = None,
        on_round: Optional[callable] = None,
    ) -> LabStatus:
        """Run for N rounds (iterations). Optionally stream events.

        Args:
            rounds: number of iterations to run (alias for max_iters).
            stream: if True, step the engine and surface new events via `on_event`.
            on_event: callback accepting a single transcript event dict.
        """
        if not stream:
            return self.start(max_iters=rounds)

        # Streaming: fetch tail after each tick and emit only new entries
        printed = 0
        n = int(rounds) if rounds is not None else 0
        iters = n if n > 0 else 1_000_000_000  # effectively unbounded if rounds is None
        start_ts = time.time()
        # mirror start(): mark active during run
        self._active = True
        for _ in range(iters):
            if getattr(self.state, "stop_flag", False):
                break
            if timeout_s is not None and (time.time() - start_ts) >= timeout_s:
                break
            self.engine.tick()
            self._last_ts = time.time()
            # time-based callbacks
            if on_tick is not None or on_round is not None:
                info = {
                    "iter": getattr(self.state, "iter", 0),
                    "elapsed_s": time.time() - start_ts,
                }
                try:
                    if on_tick is not None:
                        on_tick(info)
                    if on_round is not None:
                        on_round(info)
                except Exception:
                    pass
            # Read transcript; fallback to in-memory history
            try:
                events = self.store.read_transcript(self.state.thread_id)
            except Exception:
                events = getattr(self.state, "history", [])
            new = events[printed:]
            if new and on_event is not None:
                for ev in new:
                    try:
                        on_event(ev)
                    except Exception:
                        pass
                    if stop_when is not None:
                        try:
                            if stop_when(ev):
                                printed += len(new)
                                return self.get_status()
                        except Exception:
                            pass
                printed += len(new)
        # mark inactive at end
        self._active = False
        return self.get_status()

    def stream(self, *, rounds: Optional[int] = None, timeout_s: Optional[float] = None, stop_when: Optional[callable] = None, on_tick: Optional[callable] = None, on_round: Optional[callable] = None):
        """Generator yielding transcript events while running for `rounds`.

        Example:
            for ev in lab.stream(rounds=3):
                ...
        """
        printed = 0
        n = int(rounds) if rounds is not None else 0
        iters = n if n > 0 else 1_000_000_000
        start_ts = time.time()
        self._active = True
        for _ in range(iters):
            if getattr(self.state, "stop_flag", False):
                break
            if timeout_s is not None and (time.time() - start_ts) >= timeout_s:
                break
            self.engine.tick()
            self._last_ts = time.time()
            if on_tick is not None or on_round is not None:
                info = {
                    "iter": getattr(self.state, "iter", 0),
                    "elapsed_s": time.time() - start_ts,
                }
                try:
                    if on_tick is not None:
                        on_tick(info)
                    if on_round is not None:
                        on_round(info)
                except Exception:
                    pass
            try:
                events = self.store.read_transcript(self.state.thread_id)
            except Exception:
                events = getattr(self.state, "history", [])
            new = events[printed:]
            for ev in new:
                if stop_when is not None:
                    try:
                        if stop_when(ev):
                            yield ev
                            self._active = False
                            return
                    except Exception:
                        pass
                yield ev
            printed += len(new)
        self._active = False

    # Convenience aliases
    @property
    def status(self) -> LabStatus:
        return self.get_status()

    def history(self, *, limit: int = 50) -> List[Dict[str, Any]]:
        return self.get_history(limit=limit)

    def clean(
        self,
        thread_id: Optional[str] = None,
        *,
        delete_transcript: bool = True,
        delete_checkpoint: bool = True,
    ) -> None:
        """Delete persisted outputs for a thread (transcript and/or checkpoint).

        Args:
            thread_id: Target thread id; defaults to this lab's `thread_id`.
            delete_transcript: When True, remove the JSONL transcript file.
            delete_checkpoint: When True, delete the checkpoint snapshot.
        """
        tid = thread_id or self.thread_id
        if delete_checkpoint:
            try:
                self.store.delete_checkpoint(tid)
            except Exception:
                pass
        if delete_transcript:
            try:
                self.store.delete_transcript(tid)
            except Exception:
                pass

    # -------- user input injection --------
    def post_user_message(self, content: str, *, user_id: str = "user", persist: bool = True) -> None:
        """Append a user message into history (and transcript if persist=True).

        This enables user participation without scheduling a UserNode. Agents
        will see the message on the next turn via compose_messages.
        """
        # Append to in-memory history immediately for next-turn context
        entry: Dict[str, Any] = {
            "agent_id": user_id,
            "role": "user",
            "content": str(content),
        }
        try:
            self.state.history.append(entry)
        except Exception:
            pass
        # Also enqueue into the state queue for future consumption if needed
        try:
            self.state.enqueue_user_message(user_id, str(content))
        except Exception:
            pass
        # Optionally persist to transcript immediately for visibility in tools/CLI
        if persist:
            try:
                from time import time as _now
                t = _now()
                self.store.append_transcript(
                    self.state.thread_id,
                    {
                        "t": t,
                        "iter": getattr(self.state, "iter", 0),
                        "agent_id": user_id,
                        "role": "user",
                        "content": str(content),
                        "metadata": None,
                        "actions": None,
                    },
                )
            except Exception:
                pass

    def extend(self, *, add_iters: int) -> LabStatus:
        """
        Continue for `add_iters` more iterations (no-op if already stopped).
        """
        if add_iters <= 0:
            return self.get_status()
        if not self._active and getattr(self.state, "stop_flag", False):
            # explicitly allow extension after a STOP? For MVP, stop means stop.
            return self.get_status()

        self._active = True
        target = self.state.iter + add_iters
        while self._active and self.state.iter < target and not getattr(self.state, "stop_flag", False):
            self.engine.tick()
            self._last_ts = time.time()

        return self.get_status()

    def stop(self) -> None:
        """
        Soft stop: flips internal flag; engine will stop after current iteration.
        """
        self._active = False
        setattr(self.state, "stop_flag", True)

    def is_active(self) -> bool:
        return self._active and not getattr(self.state, "stop_flag", False)

    def get_status(self) -> LabStatus:
        return LabStatus(
            thread_id=self.thread_id,
            is_active=self.is_active(),
            iter=getattr(self.state, "iter", 0),
            last_message_at=self._last_ts,
            summary=getattr(self.state, "running_summary", None),
        )

    def get_history(self, *, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Returns most recent `limit` transcript events (engine already appends to store).
        """
        try:
            return self.store.read_transcript(self.thread_id, limit=limit)
        except Exception:
            # Fallback to in-memory if store not ready
            hist = getattr(self.state, "history", [])
            return hist[-limit:]


# ---------- Helper API ----------
def init_lab(
    config_path_or_dict: Union[str, Dict[str, Any], Any], *, thread_id: Optional[str] = None, resume: bool = True
) -> Lab:
    """
    Load the YAML (with env interpolation), validate via Pydantic schema, and return a ready Lab.
    """
    # Accept either a path/dict or an already-validated Preset-like object
    if isinstance(config_path_or_dict, (str, Path, dict)):
        cfg = load_config(config_path_or_dict)
    else:
        cfg = config_path_or_dict
    return Lab(cfg, thread_id=thread_id, resume=resume)


# ---------- Builders (pure functions) ----------
def _new_thread_id(cfg: Any) -> str:
    base = getattr(cfg, "id", "run")
    return f"{base}-{uuid.uuid4().hex[:8]}"

def _build_store(cfg: Any) -> Store:
    # `Store` is a façade—configure from cfg.persistence / cfg.persistence_tools if present.
    # For MVP: Store can accept the cfg and create SQLite(JSONL) sinks internally.
    return Store(cfg)

def _build_providers(cfg: Any) -> Dict[str, LLMProvider]:
    def _to_kwargs(obj: Any) -> Dict[str, Any]:
        # Works for Pydantic models and plain dataclasses/objects
        if hasattr(obj, "model_dump"):
            data = obj.model_dump()
        else:
            data = {k: v for k, v in vars(obj).items() if not k.startswith("_")}
        # Strip framework keys
        for k in ("id", "type", "impl"):
            if k in data:
                data.pop(k)
        return data

    out: Dict[str, LLMProvider] = {}
    for p in getattr(cfg, "providers", []):
        impl = getattr(p, "impl", None) or getattr(p, "type", None)
        if not impl:
            raise ValueError(f"Provider '{getattr(p, 'id', '?')}' missing 'impl' or 'type'")

        # Require fully-qualified class path (e.g., "agentrylab.runtime.providers.openai.OpenAIProvider")
        if "." not in impl:
            raise ValueError(
                f"Provider impl '{impl}' must be a fully-qualified class path "
                f"(e.g. 'agentrylab.runtime.providers.openai.OpenAIProvider')"
            )

        try:
            module_name, class_name = impl.rsplit(".", 1)
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
        except Exception as e:
            raise ValueError(f"Could not load provider impl '{impl}': {e}") from e

        if not issubclass(cls, LLMProvider):
            raise TypeError(f"Provider class {cls} does not implement LLMProvider interface")

        kwargs = _to_kwargs(p)
        out[p.id] = cls(**kwargs)
    return out

def _build_tools(cfg: Any) -> Dict[str, Tool]:
    out: Dict[str, Tool] = {}
    for t in getattr(cfg, "tools", []):
        impl = getattr(t, "impl", None) or getattr(t, "type", None)
        params = getattr(t, "params", {}) or {}

        try:
            # Support shorthand names like "ddg_search" by expanding to fqcn if desired
            if "." not in impl:
                raise ValueError(
                    f"Tool impl '{impl}' must be a fully-qualified class path (e.g. 'agentrylab.runtime.tools.ddg.DuckDuckGoSearchTool')"
                )
            module_name, class_name = impl.rsplit(".", 1)
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
        except Exception as e:
            raise ValueError(f"Could not load tool impl '{impl}': {e}") from e

        if not issubclass(cls, Tool):
            raise TypeError(f"Tool class {cls} does not implement Tool interface")

        out[t.id] = cls(**params)
    return out

def _build_scheduler(cfg: Any) -> Scheduler:
    """
    Build a Scheduler dynamically from configuration.

    Expected config shapes (preferred first):

    runtime:
      scheduler:
        impl: yourpkg.runtime.scheduler.custom.MyScheduler   # fully-qualified class path
        params: { ... }                                      # kwargs for constructor

    or (fallback location):

    scheduler:
      impl: yourpkg.runtime.scheduler.custom.MyScheduler
      params: { ... }

    Notes:
    - This function intentionally does **not** hardcode any scheduler paths.
    - If you want round-robin or every-n, provide the appropriate class in `impl` and
      pass its constructor kwargs in `params` (e.g., `order` or `schedule`).
    """
    rt = getattr(cfg, "runtime", None)
    sched_block = None
    if rt and hasattr(rt, "scheduler"):
        sched_block = getattr(rt, "scheduler")
    elif hasattr(cfg, "scheduler"):
        sched_block = getattr(cfg, "scheduler")

    if not sched_block or not hasattr(sched_block, "impl") or not getattr(sched_block, "impl"):
        raise ValueError(
            "No scheduler.impl specified. Please set `runtime.scheduler.impl` (or `scheduler.impl`) "
            "to a fully-qualified class path implementing the Scheduler base class, e.g.\n"
            "  runtime:\n"
            "    scheduler:\n"
            "      impl: agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler\n"
            "      params:\n"
            "        order: [pro, con, moderator, summarizer]"
        )

    impl = getattr(sched_block, "impl")
    params = getattr(sched_block, "params", {}) or {}

    if "." not in impl:
        raise ValueError(
            f"Scheduler impl '{impl}' must be a fully-qualified class path "
            f"(e.g. 'agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler')"
        )

    module_name, class_name = impl.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
    except Exception as e:
        raise ValueError(f"Could not load scheduler impl '{impl}': {e}") from e

    if not issubclass(cls, Scheduler):
        raise TypeError(f"Scheduler class {cls} does not implement Scheduler base class")

    return cls(**params)
