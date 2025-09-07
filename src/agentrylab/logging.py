# Logging & tracing configuration
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Mapping, Optional


_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


def _coerce_level(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return _LEVELS.get(value.upper(), logging.INFO)
    return logging.INFO


def setup_logging(cfg: Optional[Mapping[str, Any]] = None, trace: Optional[Mapping[str, Any]] = None) -> None:
    """Configure logging according to preset runtime.{logs,trace}.

    Args:
        cfg: typically `preset.runtime.logs` dict
            - level: str|int (default: INFO)
            - format: str (default: "%(asctime)s %(levelname)s %(name)s: %(message)s")
            - datefmt: str (optional)
            - file: path to write logs (optional; stdout if missing)
        trace: typically `preset.runtime.trace` dict
            - enabled: bool (default: False)
            - file: path to write structured trace JSON lines (optional)
            - sample: float in [0,1] to sample traces (optional)
    """
    cfg = cfg or {}
    level = _coerce_level(cfg.get("level", "INFO"))
    fmt = cfg.get("format", "%(asctime)s %(levelname)s %(name)s: %(message)s")
    datefmt = cfg.get("datefmt")
    log_file = cfg.get("file")

    handlers = None  # let basicConfig decide stdout handler when None
    if log_file:
        Path(os.path.dirname(log_file) or ".").mkdir(parents=True, exist_ok=True)
        handlers = [logging.FileHandler(log_file, encoding="utf-8")]

    logging.basicConfig(level=level, format=fmt, datefmt=datefmt, handlers=handlers)
    
    # Configure httpx logging to be less verbose
    # Move HTTP request logs to trace level for cleaner output
    httpx_logger = logging.getLogger("httpx")
    if level <= logging.INFO:
        # If main logging is INFO or more verbose, suppress httpx INFO logs
        httpx_logger.setLevel(logging.WARNING)
    else:
        # If main logging is DEBUG, show httpx DEBUG too
        httpx_logger.setLevel(logging.DEBUG)

    # Optional redaction of secrets (best-effort)
    if bool(cfg.get("redact_secrets", False)):
        class _RedactFilter(logging.Filter):
            def __init__(self) -> None:
                super().__init__(name="")
                # Collect commonly used secrets from env
                self._secrets = [
                    os.getenv("OPENAI_API_KEY", ""),
                    os.getenv("WOLFRAM_APP_ID", ""),
                    os.getenv("OLLAMA_API_KEY", ""),
                ]
                self._secrets = [s for s in self._secrets if s]

            def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
                try:
                    if self._secrets and isinstance(record.msg, str):
                        msg = record.msg
                        for secret in self._secrets:
                            if secret and secret in msg:
                                msg = msg.replace(secret, "***")
                        record.msg = msg
                except Exception:
                    pass
                return True

        logging.getLogger().addFilter(_RedactFilter())

    # Attach trace config to a dedicated logger for structured events
    tracer = logging.getLogger("agentrylab.trace")
    tracer.propagate = False  # keep trace separate from main logs
    # Ensure at least one handler; reuse main root handler if no trace file
    if trace and trace.get("enabled"):
        t_file = trace.get("file")
        if t_file:
            Path(os.path.dirname(t_file) or ".").mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(t_file, encoding="utf-8")
            fh.setFormatter(logging.Formatter("%(message)s"))  # JSON lines only
            tracer.handlers = [fh]
        else:
            # fallback: inherit a stream handler with raw messages
            if not tracer.handlers:
                tracer.addHandler(logging.StreamHandler())
        tracer.setLevel(logging.INFO)
    else:
        tracer.disabled = True


def emit_trace(event: str, **fields: Any) -> None:
    """Emit a single structured trace row to `agentrylab.trace` as JSON.

    Example:
        emit_trace("node_end", node_id="pro", latency_ms=123.4)
    """
    logger = logging.getLogger("agentrylab.trace")
    if logger.disabled:
        return
    try:
        payload = {"event": event, **fields}
        logger.info(json.dumps(payload, ensure_ascii=False))
    except Exception:
        # tracing must never break the run
        pass
