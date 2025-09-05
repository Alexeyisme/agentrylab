from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, TypedDict


# ---- Public types ----------------------------------------------------------

class Message(TypedDict, total=False):
    role: str                 # "system" | "user" | "assistant" | "tool"
    content: str
    name: str
    tool_call_id: str
    metadata: Dict[str, Any]

@dataclass(frozen=True)
class ChatResult:
    content: str                      # normalized text content
    metadata: Optional[Dict[str, Any]] = None  # e.g., {"citations": [...]} from providers/tools
    raw: Optional[Dict[str, Any]] = None       # full raw provider payload (for debugging)


class LLMProviderError(RuntimeError):
    pass


# ---- Abstract Provider base ------------------------------------------------

class LLMProvider(ABC):
    """Strict base class all providers must implement.

    Concrete providers (OpenAI, Ollama, etc.) implement `_send_chat` (and optionally
    `_send_chat_stream`). This base handles retries, backoff, timeout, and normalizes
    outputs into a `ChatResult` dict-like structure used by the engine.
    """

    # Reasonable defaults; instances can override via kwargs
    DEFAULT_TIMEOUT_S: float = 60.0
    DEFAULT_RETRIES: int = 1
    DEFAULT_BACKOFF_S: float = 0.2

    def __init__(
        self,
        *,
        model: str,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
        backoff: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.headers: Dict[str, str] = dict(headers or {})
        self.timeout = float(timeout) if timeout is not None else self.DEFAULT_TIMEOUT_S
        self.retries = int(retries) if retries is not None else self.DEFAULT_RETRIES
        self.backoff = float(backoff) if backoff is not None else self.DEFAULT_BACKOFF_S
        # keep any extra kwargs for provider-specific needs
        self.extra: Dict[str, Any] = dict(kwargs)

    # -------------------- Public API --------------------
    def chat(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Synchronous chat. Providers must return a dict with at least `content`.

        Returns a normalized dict: {"content": str, "metadata": dict|None, "raw": dict|None}
        (We return a plain dict instead of the `ChatResult` dataclass for JSONL friendliness.)
        """
        self._validate_messages(messages)
        attempt = 0
        last_err: Optional[BaseException] = None
        while attempt <= self.retries:
            try:
                raw = self._send_chat(messages, tools=tools, **kwargs)
                content, metadata = self._extract_content_and_metadata(raw)
                return {"content": content, "metadata": metadata, "raw": raw}
            except Exception as e:  # provider-specific exceptions bubble here
                last_err = e
                if attempt >= self.retries:
                    raise LLMProviderError(str(e)) from e
                # linear/exponential backoff (simple exponential)
                sleep_s = self.backoff * (2 ** attempt)
                time.sleep(sleep_s)
                attempt += 1
        # should not reach here
        raise LLMProviderError(str(last_err) if last_err else "Unknown provider error")

    def stream_chat(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Iterator[Dict[str, Any]]:
        """Streaming chat (optional). Yields chunk dicts with `delta`, may end with a final object.
        Base class raises NotImplementedError; providers override if they support streaming.
        """
        raise NotImplementedError("stream_chat is not implemented for this provider")

    # -------------------- To be implemented by subclasses --------------------
    @abstractmethod
    def _send_chat(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Perform a single provider chat call and return the raw provider response.
        Must raise on errors/timeouts.
        """

    # Optional: provider may override to support streaming
    def _send_chat_stream(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]],
        **kwargs: Any,
    ) -> Iterator[Dict[str, Any]]:
        raise NotImplementedError

    # -------------------- Helpers & validation --------------------
    def _validate_messages(self, messages: List[Message]) -> None:
        if not isinstance(messages, list) or not messages:
            raise ValueError("messages must be a non-empty list")
        for m in messages:
            if not isinstance(m, dict):
                raise TypeError("each message must be a dict-compatible mapping")
            if "role" not in m or "content" not in m:
                raise ValueError("each message requires 'role' and 'content'")

    def _extract_content_and_metadata(self, raw: Mapping[str, Any]) -> tuple[str, Optional[Dict[str, Any]]]:
        """Best-effort normalization across providers.

        Attempts to extract normalized content and optional metadata from common response formats:
          • Direct: {"content": str|list, "metadata"?: {...}}
          • OpenAI-like: {"choices":[{"message": {"content": str|list, "metadata"?: {...}}}], ...}
          • Ollama-like: {"message": {"content": str|list, "metadata"?: {...}}, ...}
          • Grok/xAI-like: {"output_text": str} | {"output": str} | {"content": [blocks]}
          • Anthropic/Generic list blocks: {"content": [{"text": ...} | {"value": ...} | str, ...]}

        If nothing matches, returns a JSON representation of `raw` for debuggability.
        """

        def _join_content(value: Any) -> Optional[str]:
            """Join content that may be a string or a list of text blocks.
            Recognizes items with keys like 'text', 'value', or nested 'content'."""
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                parts: List[str] = []
                for item in value:
                    if isinstance(item, str):
                        parts.append(item)
                    elif isinstance(item, Mapping):
                        if isinstance(item.get("text"), str):
                            parts.append(item["text"])  # type: ignore[index]
                        elif isinstance(item.get("value"), str):
                            parts.append(item["value"])  # type: ignore[index]
                        elif isinstance(item.get("content"), str):
                            parts.append(item["content"])  # type: ignore[index]
                if parts:
                    return "\n".join(parts)
            return None

        # ---- 1) Direct content on the top-level ----
        if "content" in raw:
            joined = _join_content(raw.get("content"))
            if joined is not None:
                md = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else None
                return str(joined), md

        # ---- 2) OpenAI-like shape ----
        choices = raw.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {}) if isinstance(choices[0], Mapping) else {}
            if isinstance(msg, Mapping):
                joined = _join_content(msg.get("content"))
                if joined is None:
                    joined = ""
                md = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else None
                return str(joined), md

        # ---- 3) Ollama-like shape ----
        msg = raw.get("message")
        if isinstance(msg, Mapping) and "content" in msg:
            joined = _join_content(msg.get("content")) or ""
            md = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else None
            return str(joined), md

        # ---- 4) Grok / xAI common fields ----
        out_txt = raw.get("output_text")
        if isinstance(out_txt, str) and out_txt:
            return out_txt, None
        out2 = raw.get("output")
        if isinstance(out2, str) and out2:
            return out2, None
        joined = _join_content(raw.get("content"))
        if joined is not None:
            return str(joined), None

        # ---- Fallback: readable JSON ----
        try:
            return json.dumps(raw, ensure_ascii=False), None
        except Exception:
            return str(raw), None
