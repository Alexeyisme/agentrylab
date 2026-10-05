"""FastAPI server: REST control surface, WebSocket event stream, static UI.

Run with ``agentrylab serve`` or ``python -m agentrylab.room``.

Accounts and API keys: see ``auth.py`` for the security model. In short,
keys are held in memory per signed-in user and wiped on logout/restart;
"remembered" keys are stored encrypted under the user's password.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agentrylab.runtime.providers.base import LLMProvider
from agentrylab.version import __version__

from .auth import (
    SESSION_TTL_S,
    AuthError,
    AuthStore,
    KeyVault,
    LockedOut,
    User,
    aad_for,
    derive_kek,
    encrypt_key,
    key_hint,
    load_remembered_keys,
)
from .avatars import AVATAR_CATALOG
from .personas import PERSONA_LIBRARY, Avatar, Persona
from .providers import ALL_PROVIDERS, KEY_PROVIDERS, build_provider, build_user_provider, describe_provider
from .room import MAX_SPEED, MIN_SPEED, Brain, Room, RoomManager

logger = logging.getLogger(__name__)

COOKIE_NAME = "agentrylab_session"


# ------------------------------------------------------------------ schemas
class RoomCreate(BaseModel):
    id: Optional[str] = None
    topic: Optional[str] = None
    speed: float = 3.0
    brain: Optional[Brain] = None


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
    brain: Optional[Brain] = None


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class Unlock(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class KeyIn(BaseModel):
    key: str = Field(min_length=8, max_length=512)
    remember: bool = False


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
    auth_store: Optional[AuthStore] = None,
    vault: Optional[KeyVault] = None,
) -> FastAPI:
    outputs = Path(os.getenv("AGENTRYLAB_ROOM_OUTPUTS", "outputs"))
    store = auth_store or AuthStore(os.getenv("AGENTRYLAB_ROOM_DB", str(outputs / "room.db")))
    vault = vault or KeyVault()
    signup_enabled = os.getenv("AGENTRYLAB_ALLOW_SIGNUP", "1").lower() not in {"0", "false", "no"}
    cookie_secure_env = os.getenv("AGENTRYLAB_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}

    def provider_factory(persona: Persona, room: Room) -> LLMProvider:
        brain = room.brain
        if brain.provider == "server":
            return build_provider(temperature=persona.temperature)
        key = vault.get(room.owner_id, brain.provider) if room.owner_id else None
        return build_user_provider(brain.provider, brain.model, key, temperature=persona.temperature)

    if manager is None:
        manager = RoomManager(
            provider_factory=provider_factory,
            transcript_dir=transcript_dir
            if transcript_dir is not None
            else Path(os.getenv("AGENTRYLAB_ROOM_TRANSCRIPTS", str(outputs / "transcripts"))),
        )
    elif manager._provider_factory is None:
        manager._provider_factory = provider_factory
    mgr: RoomManager = manager

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        mgr.get_or_create_default()
        try:
            yield
        finally:
            await mgr.close_all()
            store.close()

    app = FastAPI(
        title="AgentryLab Room",
        version=__version__,
        lifespan=lifespan,
        description=(
            "Live rooms of android personas. Anyone can watch and talk on the public "
            "stage (`main`); signed-in users keep API keys in a memory-only vault and run "
            "private rooms on their own brains. Full guide: docs/ROOM.md."
        ),
        openapi_tags=[
            {"name": "meta", "description": "Health, catalog of avatars, personas and providers."},
            {"name": "auth", "description": "Accounts, sessions and the API-key vault. Keys are never returned, only a hint."},
            {"name": "rooms", "description": "Create, inspect and control rooms. Private rooms answer 403 to non-owners."},
            {"name": "personas", "description": "Add or remove androids on a stage."},
            {"name": "messages", "description": "Human messages into a room."},
        ],
    )
    app.state.manager = mgr
    app.state.auth = store
    app.state.vault = vault

    # ------------------------------------------------------------- auth deps
    def current_user(request: Request) -> Optional[User]:
        return store.user_for_session(request.cookies.get(COOKIE_NAME))

    def require_user(user: Optional[User] = Depends(current_user)) -> User:
        if user is None:
            raise HTTPException(401, "sign in first")
        return user

    def set_cookie(response: Response, request: Request, token: str) -> None:
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=SESSION_TTL_S,
            httponly=True,
            samesite="lax",
            secure=cookie_secure_env or request.url.scheme == "https",
            path="/",
        )

    def me_payload(user: Optional[User]) -> Dict[str, Any]:
        if user is None:
            return {"user": None, "keys": [], "vault_unlocked": False, "signup_enabled": signup_enabled}
        remembered = {p: hint for p, _n, _c, hint in store.list_key_blobs(user.id)}
        in_memory = set(vault.providers(user.id))
        keys = []
        for pid in KEY_PROVIDERS:
            if pid in in_memory or pid in remembered:
                k = vault.get(user.id, pid)
                keys.append(
                    {
                        "provider": pid,
                        "hint": key_hint(k) if k else remembered.get(pid, "…"),
                        "remembered": pid in remembered,
                        "available": pid in in_memory,
                    }
                )
        return {
            "user": {"id": user.id, "email": user.email},
            "keys": keys,
            "vault_unlocked": vault.is_unlocked(user.id),
            "signup_enabled": signup_enabled,
        }

    def _room(room_id: str, user: Optional[User]) -> Room:
        if room_id == RoomManager.DEFAULT_ROOM:
            return mgr.get_or_create_default()
        room = mgr.get(room_id)
        if room is None:
            raise HTTPException(404, f"room '{room_id}' not found")
        if room.owner_id is not None and (user is None or user.id != room.owner_id):
            raise HTTPException(403, "this room belongs to someone else")
        return room

    def _owned_room(room_id: str, user: Optional[User]) -> Room:
        room = _room(room_id, user)
        if room.owner_id is None:
            raise HTTPException(403, "the public stage cannot be reconfigured")
        return room

    def _check_brain(brain: Brain, user: User) -> None:
        if brain.provider in KEY_PROVIDERS and vault.get(user.id, brain.provider) is None:
            label = KEY_PROVIDERS[brain.provider]["label"]
            raise HTTPException(409, f"add your {label} API key under Brains & keys first")
        if brain.provider == "server":
            raise HTTPException(422, "pick a provider for your own room")

    # ------------------------------------------------------------- meta
    @app.get("/api/health", tags=["meta"], summary="Health and public-stage brain")
    async def health() -> Dict[str, Any]:
        return {"ok": True, "version": __version__, "provider": describe_provider()}

    @app.get("/api/catalog", tags=["meta"], summary="Avatar parts, persona library, provider catalog and limits")
    async def catalog() -> Dict[str, Any]:
        return {
            "avatars": AVATAR_CATALOG,
            "library": [p.model_dump() for p in PERSONA_LIBRARY],
            "provider": describe_provider(),
            "providers": list(ALL_PROVIDERS.values()),
            "limits": {
                "min_speed": MIN_SPEED,
                "max_speed": MAX_SPEED,
                "max_personas": 12,
                "max_rooms": RoomManager.MAX_ROOMS_PER_USER,
            },
        }

    # ------------------------------------------------------------- auth
    @app.get("/api/auth/me", tags=["auth"], summary="Who am I, which keys do I hold, is the vault unlocked")
    async def me(user: Optional[User] = Depends(current_user)) -> Dict[str, Any]:
        return me_payload(user)

    @app.post("/api/auth/register", status_code=201, tags=["auth"], summary="Create an account and sign in")
    async def register(body: Credentials, request: Request, response: Response) -> Dict[str, Any]:
        if not signup_enabled:
            raise HTTPException(403, "sign-up is disabled on this server")
        try:
            user = store.create_user(body.email, body.password)
        except AuthError as e:
            raise HTTPException(409 if "exists" in str(e) else 422, str(e))
        vault.unlock(user.id, derive_kek(body.password, user.kek_salt))
        set_cookie(response, request, store.create_session(user.id))
        return me_payload(user)

    @app.post("/api/auth/login", tags=["auth"], summary="Sign in; unlocks the vault and loads remembered keys")
    async def login(body: Credentials, request: Request, response: Response) -> Dict[str, Any]:
        try:
            user = await asyncio.to_thread(store.verify_password, body.email, body.password)
        except LockedOut as e:
            raise HTTPException(429, str(e))
        except AuthError as e:
            raise HTTPException(422, str(e))
        if user is None:
            raise HTTPException(401, "wrong email or password")
        vault.unlock(user.id, derive_kek(body.password, user.kek_salt))
        load_remembered_keys(store, vault, user)
        mgr.invalidate_user(user.id)
        set_cookie(response, request, store.create_session(user.id))
        return me_payload(user)

    @app.post("/api/auth/logout", tags=["auth"], summary="Sign out and wipe this user's keys from server memory")
    async def logout(request: Request, response: Response, user: Optional[User] = Depends(current_user)) -> Dict[str, Any]:
        token = request.cookies.get(COOKIE_NAME)
        if token:
            store.delete_session(token)
        if user is not None:
            # Logging out anywhere wipes the in-memory keys everywhere.
            vault.forget(user.id)
            mgr.invalidate_user(user.id)
        response.delete_cookie(COOKIE_NAME, path="/")
        return {"ok": True}

    @app.post("/api/auth/unlock", tags=["auth"], summary="Unlock the vault after a server restart")
    async def unlock(body: Unlock, user: User = Depends(require_user)) -> Dict[str, Any]:
        """Re-derive the vault key after a server restart (session cookie survived, memory did not)."""
        try:
            verified = await asyncio.to_thread(store.verify_password, user.email, body.password)
        except LockedOut as e:
            raise HTTPException(429, str(e))
        if verified is None:
            raise HTTPException(401, "wrong password")
        vault.unlock(user.id, derive_kek(body.password, user.kek_salt))
        load_remembered_keys(store, vault, user)
        mgr.invalidate_user(user.id)
        return me_payload(user)

    @app.post("/api/auth/password", tags=["auth"], summary="Change password and re-encrypt remembered keys")
    async def change_password(body: PasswordChange, user: User = Depends(require_user)) -> Dict[str, Any]:
        try:
            verified = await asyncio.to_thread(store.verify_password, user.email, body.current_password)
        except LockedOut as e:
            raise HTTPException(429, str(e))
        if verified is None:
            raise HTTPException(401, "current password is wrong")
        try:
            store.change_password(user.id, body.new_password)
        except AuthError as e:
            raise HTTPException(422, str(e))
        # Re-encrypt remembered keys under the new password-derived key.
        kek = derive_kek(body.new_password, user.kek_salt)
        vault.unlock(user.id, kek)
        for pid, _n, _c, _h in store.list_key_blobs(user.id):
            plain = vault.get(user.id, pid)
            if plain is None:
                store.delete_key_blob(user.id, pid)  # cannot re-encrypt what we no longer hold
                continue
            nonce, ct = encrypt_key(kek, plain, aad_for(user.id, pid))
            store.save_key_blob(user.id, pid, nonce, ct, key_hint(plain))
        return me_payload(user)

    # ------------------------------------------------------------- keys
    @app.put("/api/auth/keys/{provider}", tags=["auth"], summary="Store an API key (memory; encrypted on disk if remember=true)")
    async def put_key(provider: str, body: KeyIn, user: User = Depends(require_user)) -> Dict[str, Any]:
        if provider not in KEY_PROVIDERS:
            raise HTTPException(404, f"unknown provider '{provider}'")
        key = body.key.strip()
        if not key or any(ch.isspace() for ch in key):
            raise HTTPException(422, "that does not look like an API key")
        vault.set(user.id, provider, key)
        if body.remember:
            kek = vault.kek(user.id)
            if kek is None:
                raise HTTPException(409, "unlock your vault (enter your password) before remembering keys")
            nonce, ct = encrypt_key(kek, key, aad_for(user.id, provider))
            store.save_key_blob(user.id, provider, nonce, ct, key_hint(key))
        else:
            store.delete_key_blob(user.id, provider)
        mgr.invalidate_user(user.id)
        return me_payload(user)

    @app.delete("/api/auth/keys/{provider}", tags=["auth"], summary="Remove one key from memory and disk")
    async def delete_key(provider: str, user: User = Depends(require_user)) -> Dict[str, Any]:
        vault.remove(user.id, provider)
        store.delete_key_blob(user.id, provider)
        mgr.invalidate_user(user.id)
        return me_payload(user)

    @app.delete("/api/auth/keys", tags=["auth"], summary="Forget every key, everywhere")
    async def forget_all_keys(user: User = Depends(require_user)) -> Dict[str, Any]:
        vault.forget(user.id)
        store.delete_key_blob(user.id)
        mgr.invalidate_user(user.id)
        return me_payload(user)

    # ------------------------------------------------------------ rooms
    @app.get("/api/rooms", tags=["rooms"], summary="List the public stage and your own rooms")
    async def list_rooms(user: Optional[User] = Depends(current_user)) -> List[Dict[str, Any]]:
        mgr.get_or_create_default()
        return [
            {
                "id": r.id,
                "topic": r.topic,
                "status": r.status,
                "owner_id": r.owner_id,
                "mine": user is not None and r.owner_id == user.id,
                "brain": r.brain.describe(),
                "personas": len(r.personas),
                "messages": len(r.messages),
            }
            for r in mgr.visible_to(user.id if user else None)
        ]

    @app.post("/api/rooms", status_code=201, tags=["rooms"], summary="Create a private room (requires sign-in)")
    async def create_room(body: RoomCreate, user: User = Depends(require_user)) -> Dict[str, Any]:
        brain = body.brain or _default_brain_for(user)
        _check_brain(brain, user)
        try:
            room = mgr.create(body.id, topic=body.topic, speed=body.speed, owner_id=user.id, brain=brain)
        except ValueError as e:
            raise HTTPException(409, str(e))
        return room.snapshot()

    def _default_brain_for(user: User) -> Brain:
        for pid in vault.providers(user.id):
            if pid in KEY_PROVIDERS:
                return Brain(provider=pid)
        return Brain(provider="mock")

    @app.get("/api/rooms/{room_id}", tags=["rooms"], summary="Full snapshot of a room")
    async def get_room(room_id: str, user: Optional[User] = Depends(current_user)) -> Dict[str, Any]:
        return _room(room_id, user).snapshot()

    @app.delete("/api/rooms/{room_id}", status_code=204, tags=["rooms"], summary="Close one of your rooms")
    async def delete_room(room_id: str, user: Optional[User] = Depends(current_user)) -> None:
        if room_id == RoomManager.DEFAULT_ROOM:
            raise HTTPException(400, "the default room cannot be deleted; clear it instead")
        _owned_room(room_id, user)
        await mgr.delete(room_id)

    @app.patch("/api/rooms/{room_id}", tags=["rooms"], summary="Change topic, speed or (owner only) brain")
    async def update_room(room_id: str, body: Settings, user: Optional[User] = Depends(current_user)) -> Dict[str, Any]:
        room = _room(room_id, user)
        if body.topic is not None:
            room.set_topic(body.topic)
        if body.speed is not None:
            room.set_speed(body.speed)
        if body.brain is not None:
            room = _owned_room(room_id, user)
            _check_brain(body.brain, user)  # type: ignore[arg-type]
            room.set_brain(body.brain)
        return room.snapshot()

    @app.post("/api/rooms/{room_id}/control", tags=["rooms"], summary="Play, pause, step one turn, or clear the transcript")
    async def control(room_id: str, body: Control, user: Optional[User] = Depends(current_user)) -> Dict[str, Any]:
        room = _room(room_id, user)
        getattr(room, body.action)()
        return {"status": room.status, "speed": room.speed}

    # --------------------------------------------------------- personas
    @app.post("/api/rooms/{room_id}/personas", status_code=201, tags=["personas"], summary="Add an android from the library or a custom one")
    async def add_persona(room_id: str, body: PersonaAdd, user: Optional[User] = Depends(current_user)) -> Dict[str, Any]:
        room = _room(room_id, user)
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

    @app.delete("/api/rooms/{room_id}/personas/{persona_id}", status_code=204, tags=["personas"], summary="Remove an android")
    async def remove_persona(room_id: str, persona_id: str, user: Optional[User] = Depends(current_user)) -> None:
        room = _room(room_id, user)
        try:
            room.remove_persona(persona_id)
        except KeyError:
            raise HTTPException(404, f"persona '{persona_id}' not in room")

    # --------------------------------------------------------- messages
    @app.post("/api/rooms/{room_id}/messages", status_code=201, tags=["messages"], summary="Say something as a human; name an android to have it answer next")
    async def post_message(room_id: str, body: UserMessage, user: Optional[User] = Depends(current_user)) -> Dict[str, Any]:
        room = _room(room_id, user)
        try:
            return room.post_user_message(body.content, name=body.name).model_dump()
        except ValueError as e:
            raise HTTPException(422, str(e))

    # -------------------------------------------------------- websocket
    @app.websocket("/ws/rooms/{room_id}")
    async def room_events(ws: WebSocket, room_id: str) -> None:
        user = store.user_for_session(ws.cookies.get(COOKIE_NAME))
        if room_id == RoomManager.DEFAULT_ROOM:
            room: Optional[Room] = mgr.get_or_create_default()
        else:
            room = mgr.get(room_id)
        if room is None:
            await ws.close(code=4004, reason="room not found")
            return
        if room.owner_id is not None and (user is None or user.id != room.owner_id):
            await ws.close(code=4003, reason="not your room")
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
    print(f"AgentryLab Room  →  http://{host}:{port}   (public stage brain: {info['kind']}/{info['model']})")
    if info["demo"]:
        print("Demo mode: no OPENAI_API_KEY found, the public stage uses the offline mock brain.")
    print("Signed-in users bring their own keys; see docs/ROOM.md → Accounts & keys.")
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
