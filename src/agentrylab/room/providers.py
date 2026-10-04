"""Provider selection for rooms, plus an offline mock brain.

Two kinds of brains exist:

* the **server default** (``build_provider``), chosen by environment variables
  and used by the public stage; and
* **user brains** (``build_user_provider``), created per room from the owner's
  own API key held in the in-memory vault (see ``auth.py``).

Environment:

  AGENTRYLAB_ROOM_PROVIDER  auto | openai | ollama | mock      (default: auto)
  AGENTRYLAB_ROOM_MODEL     model name for openai/ollama      (optional)
  OPENAI_API_KEY            picked up in auto mode
  OLLAMA_BASE_URL           used by the ollama adapter
  AGENTRYLAB_MOCK_LATENCY   seconds of fake "thinking" in the mock brain
"""

from __future__ import annotations

import hashlib
import os
import random
import re
import time
from typing import Any, Dict, List, Optional

from agentrylab.runtime.providers.base import LLMProvider, Message

MOCK_MODEL = "mock-brain-1"

# Providers a user can bring their own key for. ``base_url`` marks the
# OpenAI-compatible ones that reuse the OpenAI adapter.
KEY_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openai": dict(
        id="openai",
        label="OpenAI",
        default_model="gpt-4o-mini",
        models=["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
        key_hint="sk-…",
        docs="https://platform.openai.com/api-keys",
    ),
    "anthropic": dict(
        id="anthropic",
        label="Anthropic",
        default_model="claude-opus-5-5",
        models=["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5"],
        key_hint="sk-ant-…",
        docs="https://platform.claude.com/settings/keys",
    ),
    "deepseek": dict(
        id="deepseek",
        label="DeepSeek",
        default_model="deepseek-chat",
        models=["deepseek-chat", "deepseek-reasoner"],
        key_hint="sk-…",
        docs="https://platform.deepseek.com/api_keys",
        base_url="https://api.deepseek.com/v1",
    ),
    "xai": dict(
        id="xai",
        label="xAI",
        default_model="grok-4",
        models=["grok-4", "grok-3", "grok-3-mini"],
        key_hint="xai-…",
        docs="https://console.x.ai",
        base_url="https://api.x.ai/v1",
    ),
}

# Brains that need no key.
FREE_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "mock": dict(id="mock", label="Demo brain (offline)", default_model=MOCK_MODEL, models=[MOCK_MODEL]),
    "ollama": dict(id="ollama", label="Ollama (local)", default_model="llama3", models=["llama3", "llama3.1", "mistral", "qwen2.5"]),
}

ALL_PROVIDERS: Dict[str, Dict[str, Any]] = {**KEY_PROVIDERS, **FREE_PROVIDERS}


class BrainUnavailable(RuntimeError):
    """Raised when a room's brain cannot be built (typically: no key in the vault)."""


class MockProvider(LLMProvider):
    """Deterministic, key-free stand-in that improvises in-character lines.

    It reads the persona name, voice words and the last line of the transcript
    from the messages the room composes, then stitches a reply from templates.
    Good enough to make the stage feel alive while you decide on a real model.
    A small artificial latency keeps the "thinking" animation visible.
    """

    _OPENERS = [
        "{last_name} just said '{snippet}', and honestly that proves my point.",
        "Interesting take, {last_name}.",
        "Hold that thought.",
        "I've been chewing on '{topic}' all day.",
        "Nobody asked, but '{topic}' deserves a second look.",
        "{last_name}, you're closer than you think.",
        "Let me put it this way.",
        "Picture it.",
        "See, this is where {last_name} and I part ways.",
        "Fine, I'll say it.",
        "Here's the thing about '{topic}'.",
    ]
    _CORES = [
        "It all comes down to {voice1}.",
        "This is really a question of {voice1} versus {voice2}.",
        "You can't talk about '{topic}' without talking about {voice1}.",
        "{voice1} is doing all the heavy lifting here.",
        "{voice2}, obviously.",
        "I'd trade the whole argument for a little {voice1}.",
        "Strip away the noise and what's left is {voice1}.",
        "Every version of this ends in {voice2}.",
    ]
    _CLOSERS = [
        "And that, friends, is {voice2}.",
        "Which is why I keep saying: {voice1}.",
        "So let's not pretend otherwise.",
        "Ask me how I know.",
        "I rest my case. For now.",
        "Someone write that down.",
        "I will be taking questions.",
        "Change my mind, {last_name}.",
        "Anyway. Who's next?",
    ]

    def __init__(self, *, model: str = MOCK_MODEL, latency: Optional[float] = None, **kwargs: Any) -> None:
        kwargs.pop("api_key", None)
        super().__init__(model=model, **kwargs)
        self.retries = 0
        if latency is None:
            latency = float(os.getenv("AGENTRYLAB_MOCK_LATENCY", "1.1"))
        self.latency = max(0.0, latency)

    def _send_chat(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        name = _between(system, "You are speaking as ", "\n") or "Unit"
        topic = (_between(system, "Topic: ", "\n") or "all of this").strip().rstrip(".?!")
        voice = [v.strip() for v in (_between(system, "Voice: ", "\n") or "").split(",") if v.strip()]
        if not voice:
            voice = ["the vibe", "timing", "common sense"]

        transcript = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), ""
        )
        transcript = transcript.split("\n\nNow ", 1)[0]
        last_name, snippet = _last_line(transcript, exclude=name)

        seed_src = f"{name}|{transcript[-240:]}"
        rng = random.Random(int(hashlib.sha1(seed_src.encode()).hexdigest()[:12], 16))
        v1, v2 = rng.sample(voice, 2) if len(voice) >= 2 else (voice[0], voice[0])
        ctx = {
            "last_name": last_name or "everyone",
            "snippet": snippet or topic,
            "topic": topic,
            "voice1": v1,
            "voice2": v2,
        }
        openers = self._OPENERS if last_name else [o for o in self._OPENERS if "{last_name}" not in o and "{snippet}" not in o]
        parts = [rng.choice(openers)]
        if rng.random() < 0.85:
            parts.append(rng.choice(self._CORES))
        if rng.random() < 0.8:
            parts.append(rng.choice(self._CLOSERS))
        sentences = [_cap(p.format(**ctx)) for p in parts]
        if self.latency:
            time.sleep(self.latency * (0.6 + 0.8 * rng.random()))
        return {"content": " ".join(sentences)}


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _between(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    i += len(start)
    j = text.find(end, i)
    return text[i:] if j < 0 else text[i:j]


def _last_line(transcript: str, *, exclude: str) -> tuple[str, str]:
    for line in reversed(transcript.strip().splitlines()):
        if ":" not in line:
            continue
        who, _, what = line.partition(":")
        who = who.strip()
        if who and who != exclude:
            words = what.strip().split()
            return who, " ".join(words[:7]) + ("…" if len(words) > 7 else "")
    return "", ""


# ----------------------------------------------------------------------------
# Server default brain (environment-driven)
# ----------------------------------------------------------------------------
def resolve_provider_kind() -> str:
    kind = (os.getenv("AGENTRYLAB_ROOM_PROVIDER") or "auto").strip().lower()
    if kind == "auto":
        return "openai" if os.getenv("OPENAI_API_KEY") else "mock"
    if kind not in {"openai", "ollama", "mock"}:
        raise ValueError(f"AGENTRYLAB_ROOM_PROVIDER must be auto|openai|ollama|mock, got '{kind}'")
    return kind


def build_provider(kind: Optional[str] = None, *, temperature: Optional[float] = None) -> LLMProvider:
    kind = kind or resolve_provider_kind()
    model = os.getenv("AGENTRYLAB_ROOM_MODEL")
    if kind == "openai":
        return build_user_provider("openai", model, os.getenv("OPENAI_API_KEY"), temperature=temperature)
    if kind == "ollama":
        return build_user_provider("ollama", model, None, temperature=temperature)
    return MockProvider(temperature=temperature)


def describe_provider(kind: Optional[str] = None) -> Dict[str, Any]:
    kind = kind or resolve_provider_kind()
    model = os.getenv("AGENTRYLAB_ROOM_MODEL") or ALL_PROVIDERS[kind]["default_model"]
    return {"kind": kind, "model": model, "demo": kind == "mock"}


# ----------------------------------------------------------------------------
# User brains (bring-your-own-key)
# ----------------------------------------------------------------------------
def build_user_provider(
    kind: str,
    model: Optional[str],
    api_key: Optional[str],
    *,
    temperature: Optional[float] = None,
) -> LLMProvider:
    """Build a provider for ``kind`` using ``api_key``.

    Raises ``BrainUnavailable`` when a key is required but missing, so the room
    can explain the problem instead of hammering a 401.
    """
    spec = ALL_PROVIDERS.get(kind)
    if spec is None:
        raise BrainUnavailable(f"unknown provider '{kind}'")
    model = validate_model_name(model or spec["default_model"])
    if kind == "mock":
        return MockProvider(temperature=temperature)
    if kind == "ollama":
        from agentrylab.runtime.providers.ollama import OllamaProvider

        return OllamaProvider(model=model, temperature=temperature, timeout=120)
    if not api_key:
        raise BrainUnavailable(f"No {spec['label']} API key in your vault. Add one under Brains & keys.")
    if kind == "anthropic":
        from agentrylab.runtime.providers.anthropic import AnthropicProvider

        return AnthropicProvider(model=model, api_key=api_key, temperature=temperature, timeout=120)
    from agentrylab.runtime.providers.openai import OpenAIProvider

    return OpenAIProvider(
        model=model,
        api_key=api_key,
        base_url=spec.get("base_url"),
        temperature=temperature,
        timeout=90,
        vendor=spec["label"],
    )


_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:\-/]{0,80}$")


def validate_model_name(model: str) -> str:
    model = (model or "").strip()
    if not _MODEL_RE.match(model):
        raise ValueError("model name contains unsupported characters")
    return model
