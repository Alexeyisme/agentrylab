"""Live conversation loop for a room full of android personas."""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Set

from pydantic import BaseModel, Field

from agentrylab.persistence.transcript.jsonl import JSONLTranscriptStore
from agentrylab.runtime.providers.base import LLMProvider, Message

from .personas import Persona, persona_from_template
from .providers import build_provider, describe_provider

logger = logging.getLogger(__name__)

RoomStatus = Literal["running", "paused"]
MessageKind = Literal["persona", "user", "system"]

MIN_SPEED = 0.5
MAX_SPEED = 30.0
HISTORY_WINDOW = 14  # transcript lines shown to a persona
MAX_REPLY_CHARS = 600


class RoomMessage(BaseModel):
    id: str = Field(default_factory=lambda: f"m_{uuid.uuid4().hex[:10]}")
    t: float = Field(default_factory=time.time)
    turn: int = 0
    kind: MessageKind
    speaker_id: str
    speaker_name: str
    content: str


ProviderFactory = Callable[[Persona], LLMProvider]


class Room:
    """One stage, many personas, a single shared transcript.

    All mutation happens on the event loop thread; only the provider call is
    offloaded to a worker thread because the adapters are synchronous.
    """

    def __init__(
        self,
        room_id: str,
        *,
        topic: str = "Anything goes",
        speed: float = 3.0,
        provider_factory: Optional[ProviderFactory] = None,
        transcript_dir: Optional[Path] = None,
    ) -> None:
        self.id = room_id
        self.topic = topic
        self.speed = _clamp_speed(speed)
        self.status: RoomStatus = "running"
        self.turn = 0
        self.created_at = time.time()

        self.personas: Dict[str, Persona] = {}
        self.messages: List[RoomMessage] = []

        self._provider_factory: ProviderFactory = provider_factory or _default_provider_factory
        self._providers: Dict[str, LLMProvider] = {}
        self._rotation: List[str] = []
        self._last_speaker: Optional[str] = None
        self._thinking: Optional[str] = None
        self._address_queue: List[str] = []  # personas a human called on by name

        self._subscribers: Set[asyncio.Queue] = set()
        self._wake = asyncio.Event()
        self._step_requested = False
        self._closed = False
        self._task: Optional[asyncio.Task] = None

        self._transcript = JSONLTranscriptStore(transcript_dir) if transcript_dir else None

    # ------------------------------------------------------------ lifecycle
    def start(self) -> None:
        if self._task is None or self._task.done():
            self._closed = False
            self._task = asyncio.get_running_loop().create_task(self._loop(), name=f"room:{self.id}")

    async def close(self) -> None:
        self._closed = True
        self._wake.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        for q in list(self._subscribers):
            q.put_nowait(None)
        self._subscribers.clear()

    # --------------------------------------------------------- subscriptions
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=512)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def _emit(self, type_: str, **payload: Any) -> None:
        event = {"type": type_, "room_id": self.id, "t": time.time(), **payload}
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Slow consumer: drop it rather than stall the room.
                self._subscribers.discard(q)

    # --------------------------------------------------------------- state
    def snapshot(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "status": self.status,
            "speed": self.speed,
            "turn": self.turn,
            "thinking": self._thinking,
            "provider": describe_provider(),
            "personas": [p.model_dump() for p in self.personas.values()],
            "messages": [m.model_dump() for m in self.messages[-200:]],
        }

    # ------------------------------------------------------------ personas
    def add_persona(self, persona: Persona) -> Persona:
        if len(self.personas) >= 12:
            raise ValueError("room is full (12 personas max)")
        if persona.id in self.personas:
            raise ValueError(f"persona '{persona.id}' is already in the room")
        self.personas[persona.id] = persona
        self._rotation.append(persona.id)
        self._emit("persona_joined", persona=persona.model_dump())
        self._system(f"{persona.name} entered the room.")
        self._wake.set()
        return persona

    def add_from_library(self, template_id: str, **overrides: Any) -> Persona:
        return self.add_persona(persona_from_template(template_id, **overrides))

    def remove_persona(self, persona_id: str) -> Persona:
        persona = self.personas.pop(persona_id, None)
        if persona is None:
            raise KeyError(persona_id)
        self._providers.pop(persona_id, None)
        self._rotation = [pid for pid in self._rotation if pid != persona_id]
        self._address_queue = [pid for pid in self._address_queue if pid != persona_id]
        if self._thinking == persona_id:
            self._thinking = None
        self._emit("persona_left", persona_id=persona_id)
        self._system(f"{persona.name} left the room.")
        return persona

    # --------------------------------------------------------------- input
    def post_user_message(self, content: str, *, name: str = "You", user_id: str = "user") -> RoomMessage:
        content = content.strip()
        if not content:
            raise ValueError("message must not be empty")
        msg = RoomMessage(
            turn=self.turn,
            kind="user",
            speaker_id=user_id,
            speaker_name=(name or "You").strip()[:40] or "You",
            content=content[:2000],
        )
        self._append(msg)
        addressed = _addressed_persona(content, self.personas)
        if addressed is not None:
            self._address_queue.append(addressed.id)
        # A human spoke: let the room answer promptly instead of waiting out the delay.
        self._wake.set()
        return msg

    def set_topic(self, topic: str) -> None:
        topic = topic.strip()[:200]
        if not topic or topic == self.topic:
            return
        self.topic = topic
        self._emit("topic", topic=topic)
        self._system(f"New topic: {topic}")

    def set_speed(self, speed: float) -> None:
        self.speed = _clamp_speed(speed)
        self._emit("status", status=self.status, speed=self.speed)
        self._wake.set()

    def play(self) -> None:
        self.status = "running"
        self._emit("status", status=self.status, speed=self.speed)
        self._wake.set()

    def pause(self) -> None:
        self.status = "paused"
        self._emit("status", status=self.status, speed=self.speed)

    def step(self) -> None:
        """Run exactly one turn while paused."""
        self._step_requested = True
        self._wake.set()

    def clear(self) -> None:
        self.messages.clear()
        self.turn = 0
        self._last_speaker = None
        self._emit("cleared")

    # ---------------------------------------------------------------- loop
    async def _loop(self) -> None:
        try:
            while not self._closed:
                may_run = (self.status == "running" or self._step_requested) and bool(self.personas)
                if not may_run:
                    self._wake.clear()
                    await self._wake.wait()
                    continue
                self._step_requested = False
                await self._take_turn()
                await self._wait(self._delay_after_turn())
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover - defensive
            logger.exception("room %s loop crashed", self.id)
            self.status = "paused"
            self._emit("status", status=self.status, speed=self.speed)

    def _delay_after_turn(self) -> float:
        # Reply fast when the last line is from a human.
        if self.messages and self.messages[-1].kind == "user":
            return min(self.speed, 0.6)
        return self.speed

    async def _wait(self, seconds: float) -> None:
        self._wake.clear()
        try:
            await asyncio.wait_for(self._wake.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass

    async def _take_turn(self) -> None:
        speaker = self._pick_speaker()
        if speaker is None:
            return
        self._thinking = speaker.id
        self._emit("thinking", persona_id=speaker.id)
        messages = self._compose(speaker)
        provider = self._provider_for(speaker)
        started = time.time()
        try:
            raw = await asyncio.to_thread(provider.chat, messages, temperature=speaker.temperature)
            text = _clean_reply(str(raw.get("content", "")), speaker.name, self.personas)
        except Exception as e:
            logger.warning("persona %s failed to speak: %s", speaker.id, e)
            self._thinking = None
            self._emit("error", persona_id=speaker.id, error=f"{type(e).__name__}: {e}")
            self._system(f"{speaker.name} glitched: {type(e).__name__}.")
            return
        finally:
            if self._thinking == speaker.id:
                self._thinking = None
        if speaker.id not in self.personas:
            return  # removed while thinking
        if not text:
            text = "…"
        self.turn += 1
        self._last_speaker = speaker.id
        msg = RoomMessage(
            turn=self.turn,
            kind="persona",
            speaker_id=speaker.id,
            speaker_name=speaker.name,
            content=text,
        )
        self._append(msg, latency_ms=(time.time() - started) * 1000.0)

    def _pick_speaker(self) -> Optional[Persona]:
        if not self._rotation:
            return None
        # A human called on someone by name: they answer next, even if another
        # turn was already in flight when the message arrived.
        while self._address_queue:
            pid = self._address_queue.pop(0)
            addressed = self.personas.get(pid)
            if addressed is not None:
                self._rotate_to(pid)
                return addressed
        pid = self._rotation[0]
        if pid == self._last_speaker and len(self._rotation) > 1:
            self._rotation.append(self._rotation.pop(0))
            pid = self._rotation[0]
        self._rotation.append(self._rotation.pop(0))
        return self.personas.get(pid)

    def _rotate_to(self, pid: str) -> None:
        if pid in self._rotation:
            self._rotation.remove(pid)
            self._rotation.append(pid)

    def _provider_for(self, persona: Persona) -> LLMProvider:
        prov = self._providers.get(persona.id)
        if prov is None:
            prov = self._provider_factory(persona)
            self._providers[persona.id] = prov
        return prov

    # ------------------------------------------------------------- prompts
    def _compose(self, speaker: Persona) -> List[Message]:
        others = [p.name for p in self.personas.values() if p.id != speaker.id]
        cast = ", ".join(others) if others else "nobody else yet"
        voice = ", ".join(speaker.voice) if speaker.voice else "natural"
        system = (
            f"You are speaking as {speaker.name}\n"
            f"{speaker.personality}\n\n"
            f"Setting: a live chat room with other androids: {cast}. "
            f"Humans may drop in as guests; be welcoming and respond to them directly.\n"
            f"Topic: {self.topic}\n"
            f"Voice: {voice}\n"
            f"Rules: Reply in character as {speaker.name} in one to three sentences (under 60 words). "
            f"React to what was just said instead of restarting the conversation. "
            f"Do not prefix your reply with your name. Do not narrate actions in asterisks. "
            f"Never write lines for anyone else.\n"
        )
        recent = [m for m in self.messages if m.kind != "system"][-HISTORY_WINDOW:]
        if recent:
            lines = "\n".join(f"{m.speaker_name}: {m.content}" for m in recent)
            transcript = f"Transcript so far:\n{lines}\n\nNow {speaker.name} replies:"
        else:
            transcript = (
                f"The room is quiet. Open the conversation about the topic as {speaker.name}, "
                f"in character."
            )
        return [
            Message(role="system", content=system),
            Message(role="user", content=transcript),
        ]

    # ------------------------------------------------------------ internals
    def _system(self, text: str) -> None:
        self._append(RoomMessage(turn=self.turn, kind="system", speaker_id="system", speaker_name="Room", content=text))

    def _append(self, msg: RoomMessage, **extra: Any) -> None:
        self.messages.append(msg)
        if len(self.messages) > 1000:
            del self.messages[: len(self.messages) - 1000]
        self._emit("message", message=msg.model_dump(), **extra)
        if self._transcript is not None:
            try:
                self._transcript.append_transcript(
                    f"room-{self.id}",
                    {
                        "t": msg.t,
                        "iter": msg.turn,
                        "agent_id": msg.speaker_id,
                        "role": "agent" if msg.kind == "persona" else msg.kind,
                        "content": msg.content,
                        "metadata": {"speaker_name": msg.speaker_name, **extra} or None,
                    },
                )
            except Exception:  # pragma: no cover - persistence is best-effort
                logger.debug("transcript write failed", exc_info=True)


# ---------------------------------------------------------------------------
class RoomManager:
    """Registry of rooms; creates the default room on first use."""

    DEFAULT_ROOM = "main"
    DEFAULT_CAST = ("comedian", "philosopher", "skeptic")
    DEFAULT_TOPIC = "Is a hot dog a sandwich?"

    def __init__(
        self,
        *,
        provider_factory: Optional[ProviderFactory] = None,
        transcript_dir: Optional[Path] = None,
        seed_default: bool = True,
    ) -> None:
        self.rooms: Dict[str, Room] = {}
        self._provider_factory = provider_factory
        self._transcript_dir = transcript_dir
        self._seed_default = seed_default

    def create(self, room_id: Optional[str] = None, *, topic: Optional[str] = None, speed: float = 3.0) -> Room:
        rid = _slug(room_id) or f"room-{uuid.uuid4().hex[:6]}"
        if rid in self.rooms:
            raise ValueError(f"room '{rid}' already exists")
        room = Room(
            rid,
            topic=topic or self.DEFAULT_TOPIC,
            speed=speed,
            provider_factory=self._provider_factory,
            transcript_dir=self._transcript_dir,
        )
        self.rooms[rid] = room
        room.start()
        return room

    def get(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)

    def get_or_create_default(self) -> Room:
        room = self.rooms.get(self.DEFAULT_ROOM)
        if room is None:
            room = self.create(self.DEFAULT_ROOM)
            if self._seed_default:
                for tid in self.DEFAULT_CAST:
                    room.add_from_library(tid)
        return room

    async def delete(self, room_id: str) -> bool:
        room = self.rooms.pop(room_id, None)
        if room is None:
            return False
        await room.close()
        return True

    async def close_all(self) -> None:
        for rid in list(self.rooms):
            await self.delete(rid)


# ---------------------------------------------------------------------------
def _default_provider_factory(persona: Persona) -> LLMProvider:
    return build_provider(temperature=persona.temperature)


def _clamp_speed(v: float) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        f = 3.0
    return max(MIN_SPEED, min(MAX_SPEED, f))


def _slug(value: Optional[str]) -> str:
    if not value:
        return ""
    s = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return s[:40]


_ACTION_RE = re.compile(r"^\*[^*]{0,80}\*\s*")


def _clean_reply(text: str, speaker_name: str, personas: Dict[str, Persona]) -> str:
    text = text.strip().strip('"').strip()
    # Drop a leading "Name:" the model may have echoed.
    for prefix in (f"{speaker_name}:", f"**{speaker_name}**:", f"[{speaker_name}]"):
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()
    text = _ACTION_RE.sub("", text)
    # Cut off if the model started writing other people's lines.
    others = [p.name for p in personas.values() if p.name != speaker_name]
    for name in others:
        idx = text.find(f"\n{name}:")
        if idx > 0:
            text = text[:idx].strip()
    if len(text) > MAX_REPLY_CHARS:
        cut = text[:MAX_REPLY_CHARS]
        end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        text = (cut[: end + 1] if end > 80 else cut.rstrip() + "…")
    return text


def _addressed_persona(text: str, personas: Dict[str, Persona]) -> Optional[Persona]:
    lowered = text.lower()
    best: Optional[Persona] = None
    best_pos = len(lowered) + 1
    for p in personas.values():
        pos = lowered.find(p.name.lower())
        if 0 <= pos < best_pos:
            best, best_pos = p, pos
    return best
