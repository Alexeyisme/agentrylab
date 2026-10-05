from __future__ import annotations

"""Anthropic Messages API provider, via the official ``anthropic`` SDK.

The SDK is an optional dependency (installed with ``agentrylab[web]``); the
module imports it lazily so the core package keeps working without it.
"""

from typing import Any, Dict, List, Mapping, Optional

from .base import LLMProvider, LLMProviderError, Message

DEFAULT_ANTHROPIC_MODEL = "claude-opus-5-5"

# Models that accept the server-side refusal fallback parameter ("default" form).
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1"}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider(LLMProvider):
    """LLMProvider adapter for Claude.

    Short conversational replies are the use case here, so requests run at
    ``effort: low`` with a modest ``max_tokens``; override per call via kwargs.
    """

    def __init__(
        self,
        *,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
        backoff: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model=model,
            base_url=base_url,
            temperature=temperature,
            headers=headers,
            timeout=timeout,
            retries=retries,
            backoff=backoff,
            **kwargs,
        )
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover - depends on optional extra
            raise LLMProviderError("The Anthropic provider needs the 'anthropic' package: pip install anthropic") from e
        self._client = anthropic.Anthropic(
            api_key=api_key,
            base_url=base_url,
            timeout=self.timeout,
            max_retries=0,  # the LLMProvider base already retries
            default_headers=dict(headers or {}) or None,
        )

    def _split_messages(self, messages: List[Message]) -> tuple[str, List[Dict[str, str]]]:
        system_parts: List[str] = []
        convo: List[Dict[str, str]] = []
        for m in messages:
            role = m.get("role", "user")
            content = str(m.get("content", "") or "")
            if role == "system":
                system_parts.append(content)
            elif role == "assistant":
                convo.append({"role": "assistant", "content": content})
            elif role == "tool":
                convo.append({"role": "user", "content": f"TOOL: {content}"})
            else:
                convo.append({"role": "user", "content": content})
        if not convo or convo[0]["role"] != "user":
            convo.insert(0, {"role": "user", "content": "(begin)"})
        return "\n\n".join(system_parts), convo

    def _send_chat(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        import anthropic

        system, convo = self._split_messages(messages)
        params: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": int(kwargs.get("max_tokens") or self.extra.get("max_tokens") or 1024),
            "messages": convo,
            "output_config": {"effort": kwargs.get("effort") or self.extra.get("effort") or "low"},
        }
        if system:
            params["system"] = system
        # Current Claude models reject sampling parameters; only pass temperature
        # to the older generations that still accept it.
        temperature = kwargs.get("temperature", self.temperature)
        if temperature is not None and self.model.startswith(("claude-haiku-4-5", "claude-sonnet-4", "claude-opus-4-5", "claude-3")):
            params["temperature"] = max(0.0, min(1.0, float(temperature)))

        try:
            if self.model in _FALLBACK_MODELS:
                response = self._client.beta.messages.create(
                    betas=[_FALLBACK_BETA], fallbacks="default", **params
                )
            else:
                response = self._client.messages.create(**params)
        except anthropic.AuthenticationError as e:
            raise LLMProviderError("Anthropic rejected the API key") from e
        except anthropic.RateLimitError as e:
            raise LLMProviderError("Anthropic rate limit reached; try again shortly") from e
        except anthropic.APIStatusError as e:
            raise LLMProviderError(f"Anthropic error ({e.status_code}): {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LLMProviderError(f"Could not reach Anthropic: {e}") from e

        if response.stop_reason == "refusal":
            detail = getattr(getattr(response, "stop_details", None), "explanation", None)
            raise LLMProviderError(f"Claude declined this request{': ' + detail if detail else ''}")

        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        return {"content": text, "metadata": {"model": response.model, "stop_reason": response.stop_reason}}
