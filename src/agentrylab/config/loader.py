from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic.functional_validators import field_validator

# Note: Only runtime.message_contract is consumed by State; any top-level
# message_contract blocks in presets are ignored by the runtime.


class MessageContract(BaseModel):
    """Minimal message contract used by State to validate agent outputs.

    Only the `require_metadata` and `min_citations` knobs are enforced by the
    current runtime; additional fields are tolerated but unused.
    """
    require_metadata: bool = False
    min_citations: int = 1


# ----------------------------- Providers -----------------------------
class Provider(BaseModel):
    id: str
    impl: str = Field(..., description="Fully-qualified class path implementing LLMProvider")
    type: Optional[str] = Field(None, description="Optional shorthand/type; tolerated but unused")

    # Common LLM kwargs
    # Note: many providers require `model`; implementations may reject a
    # missing model at runtime.
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = None
    headers: Optional[Dict[str, str]] = None
    timeout: Optional[float] = None
    retries: Optional[int] = None
    backoff: Optional[float] = None

    # Provider-specific extras (passed via **kwargs)
    options: Optional[Dict[str, Any]] = None
    extra: Optional[Dict[str, Any]] = None

    model_config = dict(extra="allow")  # tolerate additional provider keys


# ------------------------------- Tools -------------------------------
class ToolBudget(BaseModel):
    per_run_min: int | None = 0
    per_run_max: int | None = None
    per_iteration_min: int | None = 0
    per_iteration_max: int | None = None


class Tool(BaseModel):
    id: str
    impl: str = Field(..., description="Fully-qualified class path implementing Tool")
    type: Optional[str] = None
    description: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    budget: Optional[ToolBudget] = None

    model_config = dict(extra="allow")


# ------------------------------- Nodes -------------------------------
Role = Literal["agent", "advisor", "moderator", "summarizer", "user"]


class BaseNode(BaseModel):
    id: str
    role: Role
    provider: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    tools: List[str] = Field(default_factory=list)

    model_config = dict(extra="allow")


class Agent(BaseNode):
    role: Literal["agent"] = "agent"
    allow_parallel_tools: bool = True
    fail_open_on_tool_error: bool = False
    tool_max_iters: int = 2


class Advisor(BaseNode):
    role: Literal["advisor"] = "advisor"
    non_blocking: bool = True


class Moderator(BaseNode):
    role: Literal["moderator"] = "moderator"


class Summarizer(BaseNode):
    role: Literal["summarizer"] = "summarizer"
    max_summary_chars: Optional[int] = None


class User(BaseNode):
    role: Literal["user"] = "user"


# ----------------------------- Scheduler -----------------------------
class SchedulerBlock(BaseModel):
    impl: str = Field(..., description="Fully-qualified class path implementing Scheduler")
    params: Dict[str, Any] = Field(default_factory=dict)


class Runtime(BaseModel):
    turn_order: Optional[Literal["round_robin"]] = None
    scheduler: Optional[SchedulerBlock] = None
    trace: Optional[Dict[str, Any]] = None
    logs: Optional[Dict[str, Any]] = None
    message_contract: Optional[MessageContract] = None

    model_config = dict(extra="allow")


class ScheduleEntry(BaseModel):
    id: str
    every_n: Optional[int] = None
    run_on_last: Optional[bool] = None
    non_blocking: Optional[bool] = None


# ---------------------------- Persistence ----------------------------
class Persistence(BaseModel):
    # Support either simple paths or the richer list-based config; tolerate extras
    transcript_path: Optional[str] = Field(default=None)
    sqlite_path: Optional[str] = Field(default=None)
    transcript: Optional[List[str]] = None
    checkpoints: Optional[List[str]] = None

    model_config = dict(extra="allow")


# ----------------------------- Preset root ----------------------------
class Preset(BaseModel):
    id: Optional[str] = None

    providers: List[Provider] = Field(default_factory=list)
    tools: List[Tool] = Field(default_factory=list)

    # Nodes
    agents: List[Agent | User] = Field(default_factory=list)
    advisors: List[Advisor] = Field(default_factory=list)
    moderator: Optional[Moderator] = None
    summarizer: Optional[Summarizer] = None

    # Orchestration
    runtime: Optional[Runtime] = None
    schedule: List[ScheduleEntry] = Field(default_factory=list)

    # Storage
    persistence: Optional[Persistence] = None
    persistence_tools: Optional[Dict[str, Any]] = None

    # Allow extra top-level keys like version, name, logs, room_rules, etc.
    model_config = dict(extra="allow")

    @field_validator("providers", "tools", "agents", "advisors", mode="before")
    @classmethod
    def _ensure_list(cls, v: Any):
        return [] if v is None else v

    @field_validator("runtime", mode="before")
    @classmethod
    def _runtime_default(cls, v: Any):
        return {} if v is None else v


# ----------------------------- Loader -----------------------------
import os
import re
import yaml

ENV_RE = re.compile(r"\$\{([^}:]+)(?::([^}]+))?\}")


def _env_interp_scalar(s: str) -> str:
    return ENV_RE.sub(lambda m: os.getenv(m.group(1), m.group(2) or ""), s)


def _env_interp_deep(obj: Any) -> Any:
    if isinstance(obj, str):
        return _env_interp_scalar(obj)
    if isinstance(obj, list):
        return [_env_interp_deep(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _env_interp_deep(v) for k, v in obj.items()}
    return obj


def load_config(path_or_dict: Union[str, Path, dict]) -> Preset:
    """Load a YAML or dict config, env-interpolate, and validate with Pydantic."""
    if isinstance(path_or_dict, (str, Path)):
        text = Path(path_or_dict).read_text(encoding="utf-8")
        raw = yaml.safe_load(text) or {}
    elif isinstance(path_or_dict, dict):
        raw = dict(path_or_dict)
    else:
        raise TypeError("load_config expects path or dict")

    raw = _env_interp_deep(raw)

    # Normalize heterogeneous node lists into typed fields expected by runtime
    def _normalize_nodes(doc: Dict[str, Any]) -> Dict[str, Any]:
        # Determine lint strictness (controls log level of normalization messages)
        lint_strict = False
        try:
            rt = doc.get("runtime") or {}
            if isinstance(rt, dict):
                lint_strict = bool(rt.get("lint_strict", False))
        except Exception:
            lint_strict = False
        def _log(msg: str) -> None:
            import logging
            logger = logging.getLogger(__name__)
            (logger.warning if lint_strict else logger.info)(msg)
        try:
            agents = list(doc.get("agents") or [])
        except Exception:
            agents = []
        new_agents: List[Dict[str, Any]] = []
        moderator_obj: Optional[Dict[str, Any]] = None
        summarizer_obj: Optional[Dict[str, Any]] = None
        advisors_in_agents: List[Dict[str, Any]] = []

        for item in agents:
            role = (item or {}).get("role") if isinstance(item, dict) else None
            if role == "agent":
                new_agents.append(item)
            elif role == "moderator" and moderator_obj is None:
                moderator_obj = item
            elif role == "summarizer" and summarizer_obj is None:
                summarizer_obj = item
            elif role == "advisor":
                advisors_in_agents.append(item)
            else:
                # Unrecognized → keep in agents to avoid data loss, but log
                _log(f"Unknown or missing role in agents list: {item}")
                new_agents.append(item)

        if new_agents:
            doc["agents"] = new_agents
        # Only set if not already provided explicitly
        if moderator_obj is not None and not doc.get("moderator"):
            doc["moderator"] = moderator_obj
        else:
            if moderator_obj is not None and doc.get("moderator"):
                _log("Duplicate moderator definition found in agents and top-level; keeping top-level")
        if summarizer_obj is not None and not doc.get("summarizer"):
            doc["summarizer"] = summarizer_obj
        else:
            if summarizer_obj is not None and doc.get("summarizer"):
                _log("Duplicate summarizer definition found in agents and top-level; keeping top-level")
        # Merge any advisor items into top-level advisors array
        if advisors_in_agents:
            adv = list(doc.get("advisors") or [])
            adv.extend(advisors_in_agents)
            doc["advisors"] = adv
        return doc

    if isinstance(raw, dict):
        raw = _normalize_nodes(raw)

    return Preset.model_validate(raw)
