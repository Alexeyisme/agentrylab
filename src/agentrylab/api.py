from __future__ import annotations

"""Python API entry points for Agentry Lab.

Public helpers:
  - init(config, *, experiment_id=None, prompt=None, resume=True) -> Lab
  - run(config, *, prompt=None, experiment_id=None, rounds=None, resume=True, stream=False, on_event=None) -> tuple[Lab, LabStatus]
"""

from typing import Any, Dict, Optional, Tuple, Callable

from agentrylab.config.loader import load_config
from agentrylab.lab import Lab, LabStatus, init_lab
from agentrylab.types import ProgressInfo
from agentrylab.persistence.store import Store


def init(
    config: str | Dict[str, Any] | Any,
    *,
    experiment_id: Optional[str] = None,
    prompt: Optional[str] = None,
    user_messages: Optional[list[str] | str] = None,
    resume: bool = True,
) -> Lab:
    """Initialize a Lab from a config path/dict or Preset object.

    Args:
        config: YAML path, dict, or an already-validated Preset-like object.
        experiment_id: Optional logical run/thread id (resume-able).
        prompt: Optional objective to set on the config (used by nodes if enabled).
        resume: If True, attempt to load checkpoint for experiment_id and merge.
    """
    cfg = load_config(config) if isinstance(config, (str, dict)) else config
    if prompt:
        try:
            setattr(cfg, "objective", prompt)
        except Exception:
            # Best-effort: ignore if cfg is immutable
            pass
    lab = Lab(cfg, thread_id=experiment_id, resume=resume)
    # Seed initial user message(s) into state history for context composition
    if user_messages:
        msgs = [user_messages] if isinstance(user_messages, str) else list(user_messages)
        for m in msgs:
            try:
                lab.state.history.append({"agent_id": "user", "role": "user", "content": str(m)})
            except Exception:
                pass
    return lab


def run(
    config: str | Dict[str, Any] | Any,
    *,
    prompt: Optional[str] = None,
    experiment_id: Optional[str] = None,
    rounds: Optional[int] = None,
    resume: bool = True,
    stream: bool = False,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    timeout_s: Optional[float] = None,
    stop_when: Optional[Callable[[Dict[str, Any]], bool]] = None,
    on_tick: Optional[Callable[[ProgressInfo], None]] = None,
    on_round: Optional[Callable[[ProgressInfo], None]] = None,
) -> Tuple[Lab, LabStatus]:
    """Convenience: init and run the lab once.

    Returns (lab, final_status). If stream=True and on_event is provided, calls the
    callback with each new transcript event during execution.
    """
    lab = init(config, experiment_id=experiment_id, prompt=prompt, resume=resume)
    status = lab.run(
        rounds=rounds,
        stream=stream,
        on_event=on_event,
        timeout_s=timeout_s,
        stop_when=stop_when,
        on_tick=on_tick,
        on_round=on_round,
    )
    return lab, status


def list_threads(
    config: str | Dict[str, Any] | Any,
) -> list[tuple[str, float]]:
    """Return list of (thread_id, updated_at) known to the persistence store for this config.

    Accepts the same `config` kinds as `init`: path, dict, or Preset‑like object.
    """
    cfg = load_config(config) if isinstance(config, (str, dict)) else config
    store = Store(cfg)
    return store.list_threads()
