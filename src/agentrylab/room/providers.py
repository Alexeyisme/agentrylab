"""Provider selection for rooms, plus an offline mock brain.

The room reuses the lab's provider adapters. Which one is used is decided by
environment variables so the website works out of the box:

  AGENTRYLAB_ROOM_PROVIDER  auto | openai | ollama | mock      (default: auto)
  AGENTRYLAB_ROOM_MODEL     model name for openai/ollama      (optional)
  OPENAI_API_KEY            picked up in auto mode
  OLLAMA_BASE_URL           used by the ollama adapter

``auto`` picks OpenAI when an API key is present and falls back to the mock
otherwise, so a fresh clone shows a lively room without any configuration.
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
        from agentrylab.runtime.providers.openai import OpenAIProvider

        return OpenAIProvider(
            model=model or "gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=temperature,
            timeout=60,
        )
    if kind == "ollama":
        from agentrylab.runtime.providers.ollama import OllamaProvider

        return OllamaProvider(model=model or "llama3", temperature=temperature, timeout=120)
    return MockProvider(temperature=temperature)


def describe_provider(kind: Optional[str] = None) -> Dict[str, Any]:
    kind = kind or resolve_provider_kind()
    model = os.getenv("AGENTRYLAB_ROOM_MODEL") or {
        "openai": "gpt-4o-mini",
        "ollama": "llama3",
        "mock": MOCK_MODEL,
    }[kind]
    return {"kind": kind, "model": model, "demo": kind == "mock"}
