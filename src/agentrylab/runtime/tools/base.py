from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Mapping, TypedDict, Union, cast

# ----------------------------- Public types ------------------------------

class ToolError(RuntimeError):
    """Raised when a tool fails in an expected, recoverable way."""


class ToolMeta(TypedDict, total=False):
    """Optional metadata returned by tools."""
    citations: List[str]        # URLs or identifiers supporting the result
    provider: str               # external service/provider id (e.g., "ddg", "wolfram")
    latency_ms: float           # measured latency if available
    extra: Mapping[str, Any]    # free-form per-tool metadata


class ToolResult(TypedDict, total=False):
    """Standard envelope for tool outputs.

    Required:
      - ok: indicates success/failure
      - data: the structured payload for the caller (string, dict, list, ...)
    Optional:
      - meta: ToolMeta with citations/latency/etc.
      - error: human-readable error message if ok == False
    """
    ok: bool
    data: Union[str, Dict[str, Any], List[Any], None]
    meta: ToolMeta
    error: str


# ------------------------------- Base ------------------------------------

class Tool(ABC):
    """Abstract base class for pluggable tools.

    Concrete tools must implement `run(**kwargs) -> ToolResult` and should:
      • Return a `ToolResult` with `ok=True` on success and structured `data`.
      • Include `meta.citations` when results are sourced from the web or papers.
      • Raise `ToolError` for expected failures (bad args, not found, etc.).

    The base `__call__` wraps `run()` to enforce the standard envelope and
    normalize exceptions.
    """

    def __init__(self, **params: Any) -> None:
        # Persist constructor params so schedulers/engine can introspect
        self.params: Dict[str, Any] = dict(params)

    # Main entry point used by AgentNode / Engine
    def __call__(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with best-effort retries/backoff.

        Precedence for control params: per-call kwargs > constructor params > defaults.
        Retries are applied only on exceptions (ToolError or unexpected Exception).
        If a ToolResult is returned (even with ok=False), it is not retried.
        """
        self.validate_args(kwargs)

        # Resolve retry/backoff controls and remove them from kwargs passed to run()
        retries: int = int(kwargs.pop("retries", self.params.get("retries", 0)))
        backoff: float = float(kwargs.pop("backoff", self.params.get("backoff", 0.3)))

        attempt = 0
        while attempt <= retries:
            try:
                result = self.run(**kwargs)

                # Normalize the envelope
                if not isinstance(result, dict):
                    # Allow plain strings/objects as convenience; wrap them
                    return cast(ToolResult, {"ok": True, "data": result})

                ok = bool(result.get("ok", True))
                data = result.get("data")
                meta = result.get("meta")
                error = result.get("error")
                out: ToolResult = cast(ToolResult, {"ok": ok, "data": data})
                if isinstance(meta, dict):
                    out["meta"] = meta  # type: ignore[index]
                if not ok and isinstance(error, str):
                    out["error"] = error  # type: ignore[index]
                return out
            except (ToolError, Exception) as e:
                if attempt >= retries:
                    # Final failure → normalized error envelope
                    msg = str(e) if isinstance(e, ToolError) else f"internal-error: {e}"
                    return cast(ToolResult, {"ok": False, "data": None, "error": msg})
                # Exponential backoff before retrying
                sleep_s = max(0.0, backoff) * (2 ** attempt)
                if sleep_s > 0:
                    time.sleep(sleep_s)
                attempt += 1

    # -------------------- Hooks for subclasses ----------------------------
    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool.

        Return a `ToolResult`. If raising, prefer `ToolError` for expected issues.
        """
        raise NotImplementedError

    def validate_args(self, kwargs: Mapping[str, Any]) -> None:
        """Validate input kwargs; raise `ToolError` on invalid args.

        Default is permissive. Override in concrete tools if needed.
        """
        return