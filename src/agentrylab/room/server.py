"""FastAPI server: REST control surface, WebSocket event stream, static UI.

Run with ``agentrylab serve`` or ``python -m agentrylab.room``.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agentrylab.version import __version__

from .avatars import AVATAR_CATALOG
from .personas import PERSONA_LIBRARY, Avatar, Persona
from .providers import describe_provider
from .room import MAX_SPEED, MIN_SPEED, Room, RoomManager

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ schemas
class RoomCreate(BaseModel):
    id: Optional[str] = None
    topic: Optional[str] = None
    speed: float = 3.0


class PersonaAdd(BaseModel):
    """Either reference a library template (optionally overriding fields) or
    describe a fully custom persona."""

    template_id: Optional[str] = None
    name: Optional[str] = None
    tagline: Optional[str] = None
    personality: Optional[str] = None
    avatar: Optional[Avatar] = None
    temperature: Optional[float] = None
    voice: Optional[List[str]] = None


class UserMessage(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    name: str = "You"


class Control(BaseModel):
    action: Literal["play", "pause", "step", "clear"]


class Settings(BaseModel):
    topic: Optional[str] = None
    speed: Optional[float] = Field(default=None, ge=MIN_SPEED, le=MAX_SPEED)


# --------------------------------------------------------------- factories
def find_web_dist() -> Optional[Path]:
    """Locate the built frontend, if any."""
    env = os.getenv("AGENTRYLAB_WEB_DIST")
    candidates = [Path(env)] if env else []
    here = Path(__file__).resolve()
    candidates.append(here.parent / "static")  # packaged build
    candidates.append(here.parents[3] / "web" / "dist")  # repo checkout
    for c in candidates:
        if (c / "index.html").is_file():
            return c
    return None


def create_app(
    *,
    manager: Optional[RoomManager] = None,
    serve_ui: bool = True,
    transcript_dir: Optional[Path] = None,
) -> FastAPI:
    mgr = manager or RoomManager(
        transcript_dir=transcript_dir
        if transcript_dir is not None
        else Path(os.getenv("AGENTRYLAB_ROOM_TRANSCRIPTS", "outputs/transcripts"))
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        mgr.get_or_create_default()
        try:
            yield
        finally:
            await mgr.close_all()

    app = FastAPI(title="AgentryLab Room", version=__version__, lifespan=lifespan)
    app.state.manager = mgr

    def _room(room_id: str) -> Room:
        if room_id == RoomManager.DEFAULT_ROOM:
            return mgr.get_or_create_default()
        room = mgr.get(room_id)
        if room is None:
            raise HTTPException(404, f"room '{room_id}' not found")
        return room

    # ------------------------------------------------------------- meta
    @app.get("/api/health")
    async def health() -> Dict[str, Any]:
        return {"ok": True, "version": __version__, "provider": describe_provider()}

    @app.get("/api/catalog")
    async def catalog() -> Dict[str, Any]:
        return {
            "avatars": AVATAR_CATALOG,
            "library": [p.model_dump() for p in PERSONA_LIBRARY],
            "provider": describe_provider(),
            "limits": {"min_speed": MIN_SPEED, "max_speed": MAX_SPEED, "max_personas": 12},
        }

    # ------------------------------------------------------------ rooms
    @app.get("/api/rooms")
    async def list_rooms() -> List[Dict[str, Any]]:
        mgr.get_or_create_default()
        return [
            {
                "id": r.id,
                "topic": r.topic,
                "status": r.status,
                "personas": len(r.personas),
                "messages": len(r.messages),
            }
            for r in mgr.rooms.values()
        ]

    @app.post("/api/rooms", status_code=201)
    async def create_room(body: RoomCreate) -> Dict[str, Any]:
        try:
            room = mgr.create(body.id, topic=body.topic, speed=body.speed)
        except ValueError as e:
            raise HTTPException(409, str(e))
        return room.snapshot()

    @app.get("/api/rooms/{room_id}")
    async def get_room(room_id: str) -> Dict[str, Any]:
        return _room(room_id).snapshot()

    @app.delete("/api/rooms/{room_id}", status_code=204)
    async def delete_room(room_id: str) -> None:
        if room_id == RoomManager.DEFAULT_ROOM:
            raise HTTPException(400, "the default room cannot be deleted; clear it instead")
        if not await mgr.delete(room_id):
            raise HTTPException(404, f"room '{room_id}' not found")

    @app.patch("/api/rooms/{room_id}")
    async def update_room(room_id: str, body: Settings) -> Dict[str, Any]:
        room = _room(room_id)
        if body.topic is not None:
            room.set_topic(body.topic)
        if body.speed is not None:
            room.set_speed(body.speed)
        return room.snapshot()

    @app.post("/api/rooms/{room_id}/control")
    async def control(room_id: str, body: Control) -> Dict[str, Any]:
        room = _room(room_id)
        getattr(room, body.action)()
        return {"status": room.status, "speed": room.speed}

    # --------------------------------------------------------- personas
    @app.post("/api/rooms/{room_id}/personas", status_code=201)
    async def add_persona(room_id: str, body: PersonaAdd) -> Dict[str, Any]:
        room = _room(room_id)
        overrides = body.model_dump(exclude={"template_id"}, exclude_none=True)
        try:
            if body.template_id:
                persona = room.add_from_library(body.template_id, **overrides)
            else:
                if not body.name or not body.personality:
                    raise HTTPException(422, "custom persona needs 'name' and 'personality'")
                persona = room.add_persona(Persona(**overrides))
        except KeyError as e:
            raise HTTPException(404, f"unknown template {e}")
        except ValueError as e:
            raise HTTPException(409, str(e))
        return persona.model_dump()

    @app.delete("/api/rooms/{room_id}/personas/{persona_id}", status_code=204)
    async def remove_persona(room_id: str, persona_id: str) -> None:
        room = _room(room_id)
        try:
            room.remove_persona(persona_id)
        except KeyError:
            raise HTTPException(404, f"persona '{persona_id}' not in room")

    # --------------------------------------------------------- messages
    @app.post("/api/rooms/{room_id}/messages", status_code=201)
    async def post_message(room_id: str, body: UserMessage) -> Dict[str, Any]:
        room = _room(room_id)
        try:
            return room.post_user_message(body.content, name=body.name).model_dump()
        except ValueError as e:
            raise HTTPException(422, str(e))

    # -------------------------------------------------------- websocket
    @app.websocket("/ws/rooms/{room_id}")
    async def room_events(ws: WebSocket, room_id: str) -> None:
        if room_id == RoomManager.DEFAULT_ROOM:
            room = mgr.get_or_create_default()
        else:
            room = mgr.get(room_id)
        if room is None:
            await ws.close(code=4004, reason="room not found")
            return
        await ws.accept()
        queue = room.subscribe()
        await ws.send_json({"type": "snapshot", "room": room.snapshot()})

        async def pump() -> None:
            while True:
                event = await queue.get()
                if event is None:
                    await ws.close(code=1001, reason="room closed")
                    return
                await ws.send_json(event)

        async def listen() -> None:
            # Clients may send lightweight commands over the socket too.
            while True:
                data = await ws.receive_json()
                await _handle_ws_command(room, data)

        tasks = [asyncio.create_task(pump()), asyncio.create_task(listen())]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        except WebSocketDisconnect:
            pass
        finally:
            for t in tasks:
                t.cancel()
            room.unsubscribe(queue)

    # ----------------------------------------------------------- static
    dist = find_web_dist() if serve_ui else None
    if dist is not None:
        assets = dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            candidate = (dist / path).resolve()
            if path and candidate.is_file() and dist in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    else:

        @app.get("/", include_in_schema=False)
        def no_ui() -> JSONResponse:
            return JSONResponse(
                {
                    "message": "AgentryLab Room API is running, but the web UI has not been built.",
                    "hint": "cd web && npm install && npm run build  (or set AGENTRYLAB_WEB_DIST)",
                    "docs": "/docs",
                }
            )

    return app


async def _handle_ws_command(room: Room, data: Any) -> None:
    if not isinstance(data, dict):
        return
    kind = data.get("type")
    try:
        if kind == "say":
            room.post_user_message(str(data.get("content", "")), name=str(data.get("name") or "You"))
        elif kind == "control" and data.get("action") in {"play", "pause", "step", "clear"}:
            getattr(room, data["action"])()
        elif kind == "settings":
            if "topic" in data:
                room.set_topic(str(data["topic"]))
            if "speed" in data:
                room.set_speed(float(data["speed"]))
    except (ValueError, TypeError) as e:
        room._emit("error", persona_id=None, error=str(e))


def serve(host: str = "127.0.0.1", port: int = 8000, *, reload: bool = False, log_level: str = "info") -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    info = describe_provider()
    print(f"AgentryLab Room  →  http://{host}:{port}   (brains: {info['kind']}/{info['model']})")
    if info["demo"]:
        print("Demo mode: no OPENAI_API_KEY found, personas use the offline mock brain.")
    uvicorn.run(
        "agentrylab.room.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        factory=False,
    )


# Module-level app for `uvicorn agentrylab.room.server:app`
app = create_app()
