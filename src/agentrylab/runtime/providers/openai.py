from __future__ import annotations

"""OpenAI Chat Completions provider adapter.

Uses HTTP via httpx to call /v1/chat/completions. We avoid the SDK dependency.
"""

from typing import Any, Dict, List, Mapping, Optional
import os

import httpx

from .base import LLMProvider, Message, LLMProviderError
from ...logging import emit_trace


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


class OpenAIProvider(LLMProvider):
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
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        # Allow environment override for base URL
        base = base_url or os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)

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
        self.api_key = api_key
        # Ensure Authorization header if api_key provided
        if api_key:
            self.headers.setdefault("Authorization", f"Bearer {api_key}")
        self.headers.setdefault("Content-Type", "application/json")

    def _endpoint(self) -> str:
        base = (self.base_url or DEFAULT_OPENAI_BASE_URL).rstrip("/")
        return f"{base}/chat/completions"

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "") or ""
            # OpenAI may not accept 'tool' role directly; coerce to 'user'
            if role == "tool":
                out.append({"role": "user", "content": f"TOOL: {content}"})
            else:
                out.append({"role": role, "content": str(content)})
        return out

    def _send_chat(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]],  # unused for now
        **kwargs: Any,
    ) -> Dict[str, Any]:
        url = self._endpoint()
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        # Pass through common optional params if provided (extra or per-call kwargs)
        for key in (
            "response_format",
            "max_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
        ):
            if key in self.extra:
                payload[key] = self.extra[key]
            if key in kwargs:
                payload[key] = kwargs[key]

        with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            emit_trace("provider_request", provider="openai", model=self.model, url=url)
            resp = client.post(url, json=payload)
            try:
                resp.raise_for_status()
            except Exception as e:
                emit_trace("provider_error", provider="openai", error=str(e), status_code=resp.status_code)
                raise LLMProviderError(f"OpenAI error ({resp.status_code}): {resp.text}") from e
            data = resp.json()
            emit_trace("provider_response", provider="openai", model=self.model, status_code=resp.status_code, response_size=len(str(data)))
        return data
