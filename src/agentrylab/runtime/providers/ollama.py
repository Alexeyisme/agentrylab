from __future__ import annotations

"""Ollama provider adapter.

Docs: https://github.com/ollama/ollama/blob/main/docs/api.md#chat
This adapter targets the `/api/chat` endpoint and returns the raw JSON; the
`LLMProvider` base normalizes `message.content` into `{"content": ...}`.
"""

import json
from typing import Any, Dict, Iterator, List, Mapping, Optional
import os

import httpx

from .base import LLMProvider, Message, LLMProviderError
from ...logging import emit_trace


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


class OllamaProvider(LLMProvider):
    """LLMProvider implementation for Ollama chat API."""

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
        # Allow environment override for base URL
        base = base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)

        super().__init__(
            model=model,
            base_url=base,
            temperature=temperature,
            headers=headers,
            timeout=timeout,
            retries=retries,
            backoff=backoff,
            **kwargs,
        )

    # -------------------- Core request builders --------------------
    def _build_payload(self, messages: List[Message], *, stream: bool, **kwargs: Any) -> Dict[str, Any]:
        """Compose the JSON payload for Ollama /api/chat.

        Supports passing `options` and common keys via provider extra or per-call kwargs.
        """
        msg_list = [
            {"role": m.get("role", "user"), "content": m.get("content", "")}
            for m in messages
        ]
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": msg_list,
            "stream": bool(stream),
        }

        # options (temperature etc.)
        options: Dict[str, Any] = {}
        if self.temperature is not None:
            options["temperature"] = self.temperature
        # merge options from provider.extra and per-call kwargs
        for src in (self.extra.get("options"), kwargs.get("options")):
            if isinstance(src, Mapping):
                options.update(src)
        if options:
            payload["options"] = options

        # pass-through supported fields if provided (won't error if unknown)
        passthrough_keys = ("keep_alive", "format", "template", "num_ctx", "seed")
        for key in passthrough_keys:
            if key in self.extra and self.extra[key] is not None:
                payload[key] = self.extra[key]
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]

        return payload

    def _endpoint(self) -> str:
        base = (self.base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        return f"{base}/api/chat"

    # -------------------- LLMProvider required methods --------------------
    def _send_chat(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]],  # not used yet; reserved for future
        **kwargs: Any,
    ) -> Dict[str, Any]:
        url = self._endpoint()
        payload = self._build_payload(messages, stream=False, **kwargs)
        # Use a short-lived client to ensure timeouts/headers are applied consistently
        with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            emit_trace("provider_request", provider="ollama", model=self.model, url=url)
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            emit_trace("provider_response", provider="ollama", model=self.model, status_code=resp.status_code, response_size=len(str(data)))
        if isinstance(data, Mapping) and data.get("error"):
            emit_trace("provider_error", provider="ollama", error=str(data.get("error")))
            raise LLMProviderError(str(data.get("error")))
        return data  # raw JSON; base class will normalize content/metadata

    # Optional streaming support
    def stream_chat(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Iterator[Dict[str, Any]]:
        """Stream tokens from Ollama.

        Yields dicts with `delta` while streaming, and a final dict with `content` when done.
        """
        url = self._endpoint()
        payload = self._build_payload(messages, stream=True, **kwargs)

        buffer: List[str] = []
        with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    # each chunk typically has { "message": {"content": "..."}, "done": bool }
                    msg = obj.get("message") if isinstance(obj, Mapping) else None
                    if isinstance(msg, Mapping):
                        delta = msg.get("content")
                        if isinstance(delta, str) and delta:
                            buffer.append(delta)
                            yield {"delta": delta, "raw": obj}
                    if obj.get("done"):
                        final_text = "".join(buffer)
                        yield {"content": final_text, "raw": obj}
                        return
