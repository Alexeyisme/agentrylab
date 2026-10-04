from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from agentrylab.room import PERSONA_LIBRARY, Persona, Room, RoomManager
from agentrylab.room.personas import persona_from_template
from agentrylab.room.providers import MockProvider
from agentrylab.room.room import _addressed_persona, _clean_reply
from agentrylab.room.server import create_app
from agentrylab.runtime.providers.base import Message


# ------------------------------------------------------------------ helpers
class EchoProvider(MockProvider):
    """Returns a predictable line so tests can assert on content."""

    calls: List[List[Message]] = []

    def _send_chat(self, messages, *, tools=None, **kwargs):  # type: ignore[override]
        EchoProvider.calls.append(messages)
        system = messages[0]["content"]
        name = system.split("You are speaking as ", 1)[1].split("\n", 1)[0]
        return {"content": f"{name}: hello from {name}"}


def echo_factory(_: Persona) -> EchoProvider:
    return EchoProvider()


async def wait_for(predicate, timeout: float = 3.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition not met in time")
        await asyncio.sleep(0.01)


async def drain(queue: asyncio.Queue) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    while not queue.empty():
        item = queue.get_nowait()
        if item is not None:  # None is the close sentinel
            out.append(item)
    return out


# ----------------------------------------------------------------- personas
def test_library_templates_are_valid_and_unique():
    ids = [t.id for t in PERSONA_LIBRARY]
    assert len(ids) == len(set(ids))
    assert len(PERSONA_LIBRARY) >= 8
    for t in PERSONA_LIBRARY:
        assert t.name and t.personality and t.voice


def test_persona_from_template_gets_fresh_id_and_overrides():
    a = persona_from_template("comedian")
    b = persona_from_template("comedian", name="Chuckles")
    assert a.id != b.id
    assert a.id != "comedian"
    assert a.template_id == "comedian"
    assert b.name == "Chuckles"
    with pytest.raises(KeyError):
        persona_from_template("nope")


def test_persona_avatar_validation():
    with pytest.raises(ValueError):
        Persona(name="X", personality="y", avatar={"face": "nope"})  # type: ignore[arg-type]


# ----------------------------------------------------------- mock provider
def test_mock_provider_speaks_in_voice():
    p = MockProvider()
    msgs = [
        Message(
            role="system",
            content="You are speaking as Dr. Volt\nTopic: hot dogs\nVoice: data, mechanism\nRules: x\n",
        ),
        Message(role="user", content="Transcript so far:\nRimshot: a sandwich is a state of mind\n\nNow Dr. Volt replies:"),
    ]
    out = p.chat(msgs)
    text = out["content"]
    assert text and text[0].isupper()
    assert "data" in text or "mechanism" in text or "Rimshot" in text or "hot dogs" in text
    # deterministic for same inputs
    assert p.chat(msgs)["content"] == text


# ------------------------------------------------------------------- room
def test_clean_reply_strips_name_and_other_lines():
    personas = {"a": persona_from_template("poet", name="Lumen"), "b": persona_from_template("kid", name="Pip")}
    assert _clean_reply("Lumen: *sighs* moonlight.\nPip: wow", "Lumen", personas) == "moonlight."
    assert _clean_reply('"quoted"', "Lumen", personas) == "quoted"


def test_addressed_persona_prefers_earliest_mention():
    personas = {"a": persona_from_template("poet", name="Lumen"), "b": persona_from_template("kid", name="Pip")}
    assert _addressed_persona("hey pip, and lumen", personas).name == "Pip"
    assert _addressed_persona("nobody", personas) is None


async def test_room_rotates_speakers_and_streams_events():
    EchoProvider.calls.clear()
    room = Room("t", topic="testing", speed=0.5, provider_factory=echo_factory)
    q = room.subscribe()
    room.start()
    try:
        room.add_from_library("comedian")
        room.add_from_library("poet")
        await wait_for(lambda: len([m for m in room.messages if m.kind == "persona"]) >= 3)
    finally:
        await room.close()
    spoken = [m for m in room.messages if m.kind == "persona"]
    names = [m.speaker_name for m in spoken[:3]]
    assert names[0] != names[1] and names[1] != names[2]
    # the "Name:" prefix echoed by the provider is cleaned
    assert spoken[0].content == f"hello from {spoken[0].speaker_name}"
    events = await drain(q)
    kinds = [e["type"] for e in events]
    assert "persona_joined" in kinds and "thinking" in kinds and "message" in kinds
    # the second speaker saw the first line in its transcript
    second_call = EchoProvider.calls[1]
    assert spoken[0].speaker_name in second_call[1]["content"]


async def test_user_message_is_answered_by_addressed_persona():
    room = Room("u", speed=5.0, provider_factory=echo_factory)
    room.start()
    try:
        room.pause()
        a = room.add_from_library("skeptic")  # Nope-9
        room.add_from_library("chef")  # Sous-Bot
        room.post_user_message("Sous-Bot, what's for dinner?", name="Alex")
        assert room.messages[-1].kind == "user" and room.messages[-1].speaker_name == "Alex"
        room.step()
        await wait_for(lambda: any(m.kind == "persona" for m in room.messages))
        reply = [m for m in room.messages if m.kind == "persona"][-1]
        assert reply.speaker_name == "Sous-Bot"
        # paused: no further turns
        await asyncio.sleep(0.2)
        assert len([m for m in room.messages if m.kind == "persona"]) == 1
        room.remove_persona(a.id)
        assert a.id not in room.personas
        with pytest.raises(KeyError):
            room.remove_persona(a.id)
    finally:
        await room.close()


async def test_room_waits_when_empty_and_resumes_on_join():
    room = Room("e", speed=0.5, provider_factory=echo_factory)
    room.start()
    try:
        await asyncio.sleep(0.1)
        assert room.messages == []
        room.add_from_library("kid")
        await wait_for(lambda: any(m.kind == "persona" for m in room.messages))
    finally:
        await room.close()


async def test_room_survives_provider_errors():
    class Boom(MockProvider):
        def _send_chat(self, messages, *, tools=None, **kwargs):  # type: ignore[override]
            raise RuntimeError("fried circuit")

    room = Room("b", speed=0.5, provider_factory=lambda _p: Boom())
    q = room.subscribe()
    room.start()
    try:
        room.add_from_library("overlord")
        await wait_for(lambda: any(e["type"] == "error" for e in list(q._queue)))  # type: ignore[attr-defined]
    finally:
        await room.close()
    assert any(m.kind == "system" and "glitched" in m.content for m in room.messages)
    assert room.status == "running"


def test_speed_is_clamped():
    room = Room("s", speed=999)
    assert room.speed == 30.0
    room.set_speed(0.01)
    assert room.speed == 0.5


# ----------------------------------------------------------------- server
@pytest.fixture()
def client(tmp_path):
    mgr = RoomManager(provider_factory=echo_factory, transcript_dir=tmp_path, seed_default=False)
    app = create_app(manager=mgr, serve_ui=False)
    with TestClient(app) as c:
        yield c


def test_api_catalog_and_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"]
    cat = client.get("/api/catalog").json()
    assert {"faces", "bodies", "palettes"} <= set(cat["avatars"])
    assert any(p["id"] == "comedian" for p in cat["library"])


def test_api_room_lifecycle(client):
    snap = client.get("/api/rooms/main").json()
    assert snap["id"] == "main" and snap["personas"] == []

    r = client.post("/api/rooms/main/personas", json={"template_id": "comedian", "name": "Giggles"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert r.json()["name"] == "Giggles"

    r = client.post(
        "/api/rooms/main/personas",
        json={"name": "Custom", "personality": "You are custom.", "avatar": {"face": "crt", "body": "orb", "palette": "lime"}},
    )
    assert r.status_code == 201 and r.json()["avatar"]["face"] == "crt"

    assert client.post("/api/rooms/main/personas", json={"name": "NoPrompt"}).status_code == 422
    assert client.post("/api/rooms/main/personas", json={"template_id": "ghost"}).status_code == 404

    r = client.post("/api/rooms/main/messages", json={"content": "hi all", "name": "Alex"})
    assert r.status_code == 201 and r.json()["kind"] == "user"

    r = client.post("/api/rooms/main/control", json={"action": "pause"})
    assert r.json()["status"] == "paused"
    r = client.patch("/api/rooms/main", json={"topic": "cats", "speed": 2})
    assert r.json()["topic"] == "cats" and r.json()["speed"] == 2

    assert client.delete(f"/api/rooms/main/personas/{pid}").status_code == 204
    assert client.delete(f"/api/rooms/main/personas/{pid}").status_code == 404
    assert client.delete("/api/rooms/main").status_code == 400

    r = client.post("/api/rooms", json={"id": "Side Room!", "topic": "x"})
    assert r.status_code == 201 and r.json()["id"] == "side-room"
    assert client.post("/api/rooms", json={"id": "side-room"}).status_code == 409
    assert len(client.get("/api/rooms").json()) == 2
    assert client.delete("/api/rooms/side-room").status_code == 204
    assert client.get("/api/rooms/side-room").status_code == 404


def test_websocket_streams_snapshot_and_events(client):
    with client.websocket_connect("/ws/rooms/main") as ws:
        first = ws.receive_json()
        assert first["type"] == "snapshot" and first["room"]["id"] == "main"
        ws.send_json({"type": "control", "action": "pause"})
        ev = ws.receive_json()
        assert ev["type"] == "status" and ev["status"] == "paused"
        ws.send_json({"type": "say", "content": "hello there", "name": "Alex"})
        ev = ws.receive_json()
        assert ev["type"] == "message" and ev["message"]["content"] == "hello there"
        client.post("/api/rooms/main/personas", json={"template_id": "poet"})
        ev = ws.receive_json()
        assert ev["type"] == "persona_joined" and ev["persona"]["template_id"] == "poet"


def test_websocket_unknown_room(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/rooms/does-not-exist") as ws:
            ws.receive_json()
