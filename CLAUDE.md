# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

AgentryLab is a Python package with two runtimes that share provider adapters:

1. **The lab engine** (`agentrylab.runtime`, `lab.py`, `api.py`, `cli/`): YAML presets describe a fixed cast of LLM "nodes" and a schedule; `Engine.tick()` runs them with transcripts (JSONL) and checkpoints (SQLite). Driven by `agentrylab run …` or `agentrylab.init()/run()`.
2. **The Room** (`agentrylab.room`, `web/`): a live stage where android personas talk to each other and to humans in the browser. Personas join/leave while it runs, signed-in users bring their own API keys, and events stream over a WebSocket. Driven by `agentrylab serve`.

Guiding rule from `.cursor/rules`: keep it simple and easily extendable.

## First ten minutes

```bash
pip install -e '.[dev]' && ruff check . && python -m pytest -q      # expect ~140 passed
cd web && npm install && npm run build && cd ..                     # expect web/dist
agentrylab serve                                                    # open http://127.0.0.1:8000
```

With no `OPENAI_API_KEY` the public stage runs on the offline demo brain, so the
UI is fully exercisable without any secrets. `/docs` shows the API. Sign up with
any email and a password of 8+ characters to try the vault and private rooms; a
made-up API key is fine for the UI flow (the room pauses after the provider
rejects it, which is the intended behaviour).

## Commands

```bash
pip install -e '.[dev]'            # Python deps incl. web server, test and lint tooling
ruff check .                       # lint (CI runs this; only E rules, line length ignored)
python -m pytest -q                # full suite (~140 tests, no network, ~10 s)
python -m pytest -q tests/test_room.py        # one file
python -m pytest -q tests/test_auth.py -k remembered   # one test by keyword
python -m pytest --cov=src/agentrylab --cov-branch --cov-report=term-missing -q   # what CI runs

cd web && npm install && npm run build   # frontend → web/dist (tsc + vite); CI runs this too
cd web && npm run dev                    # HMR on :5173, proxies /api and /ws to :8000
cd web && npm run typecheck              # tsc only

agentrylab serve [--reload]              # Room on :8000; serves web/dist if built
agentrylab run standup_club.yaml --objective "topic" --max-iters 4   # lab engine
make web-bundle                          # copy web/dist into the package for wheels
```

Tests are plain `pytest` with `asyncio_mode = "auto"`: write `async def test_…` for Room loop tests, no decorator needed. `tests/test_room.py` and `tests/test_auth.py` set `AGENTRYLAB_SCRYPT_N=4096` at import so password hashing is fast; keep that line if you add a test module that imports `agentrylab.room.auth`.

## Architecture: lab engine

- `config/loader.py` validates YAML into Pydantic models (`Preset`, `Agent`, `Provider`, …). Providers, tools and schedulers are referenced by fully-qualified class path in the YAML and imported dynamically in `lab.py` (`_build_providers`, `_build_tools`, `_build_scheduler`); nothing is hardcoded.
- `runtime/nodes/` are role classes (`AgentNode`, `ModeratorNode`, `SummarizerNode`, `AdvisorNode`, `UserNode`) built by `nodes/factory.py` from the YAML `role`. `NodeBase.__call__` = build messages → `provider.chat` → postprocess → validate. `AgentNode` adds a JSON tool-call loop (`{"tool": id, "args": {...}}` in the model output).
- `runtime/state.py` (`State`) composes the message window for a node and tracks tool budgets; `runtime/engine.py` asks the scheduler which nodes run this tick, applies outputs, honours moderator actions (`STOP`, `STEP_BACK` rollback), and persists via `persistence/store.py`.
- `runtime/providers/base.py` (`LLMProvider`) owns retries/backoff and normalises every vendor response to `{"content", "metadata", "raw"}`; subclasses only implement `_send_chat`. `OpenAIProvider` also serves any OpenAI-compatible API via `base_url` + `vendor`; `AnthropicProvider` uses the official SDK (optional dependency, imported lazily).
- `telegram/adapter.py` is an older async wrapper around `Lab` for chat-bot integrations; it is independent of the Room.

## Architecture: the Room

Read `src/agentrylab/docs/ROOM.md` first; it has the diagram, turn lifecycle, API and threat model. The parts that take several files to see:

- **One asyncio task per room** (`room/room.py`, `Room._loop`). All mutation (add/remove persona, post message, pause, brain change) happens on the event loop; only `provider.chat` runs in `asyncio.to_thread`. Consequently **every FastAPI handler in `room/server.py` must be `async def`**: a sync handler runs in a threadpool and `Room` methods then touch asyncio objects from the wrong thread (`RuntimeError: no running event loop`).
- **Brains and keys.** A room has `Brain(provider, model)`. `RoomManager` is constructed with a `provider_factory(persona, room)`; the real one in `server.create_app` looks the owner's key up in the in-memory `KeyVault` and calls `providers.build_user_provider`. Providers are cached per persona in `Room._providers` and must be dropped (`invalidate_providers`, `RoomManager.invalidate_user`) whenever a key or brain changes. A missing key raises `BrainUnavailable` → the room pauses with a system message; three other failures in a row also pause it.
- **Secrets never leave memory.** `room/auth.py`: passwords scrypt-hashed, sessions stored hashed, keys held per user in `KeyVault`; "remembered" keys are AES-GCM encrypted under a scrypt key derived from the password (so a restart locks the vault until `/api/auth/unlock`). Endpoints return only `key_hint(...)`; never add a code path that logs, persists or returns a plaintext key, and never include provider error bodies verbatim (see `_error_text` in the OpenAI adapter).
- **Access control** is in `server._room` / `_owned_room` / the WebSocket handler: public `main` room for everyone, private rooms only for `owner_id`. Room creation needs a session.
- **Mock brain.** `providers.MockProvider` parses the system prompt the room composes (`You are speaking as …`, `Topic: …`, `Voice: …` lines) to improvise in-character replies offline. Changing the prompt format in `Room._compose` breaks it; tests cover both.
- **Frontend state** lives entirely in `web/src/store.ts` (zustand + the WebSocket client). Components never fetch; they call store actions, and the server echoes results back as socket events, so there is no optimistic state. Each android's `mood` (`idle | thinking | talking`) and `lookAt` (`-1 | 0 | 1`, toward whoever has the floor) are derived in `Stage.tsx` from `thinking`/`speaking`, and every animation in `web/src/avatars/` is a function of those props (faces/bodies read `still`/`lookAt` via `avatars/context.ts`).

## Testing recipes

- **Room logic**: build `Room(..., provider_factory=lambda persona, room: FakeProvider())`, `room.start()` inside an `async def` test, drive it with `add_from_library` / `post_user_message` / `pause` / `step`, and poll `room.messages` with a short `wait_for` loop; always `await room.close()` in `finally`. A fake is a `MockProvider` subclass overriding `_send_chat` (see `EchoProvider` in `tests/test_room.py`).
- **HTTP/WebSocket**: `create_app(manager=RoomManager(provider_factory=..., transcript_dir=tmp_path, seed_default=False), serve_ui=False, auth_store=AuthStore(tmp_path / "auth.db"), vault=KeyVault())` with `fastapi.testclient.TestClient`; the client keeps the session cookie, so register once and then call the authed endpoints. `client.websocket_connect("/ws/rooms/main")` yields events in order after the snapshot.
- **Auth/crypto**: unit-test `AuthStore` and the `encrypt_key`/`decrypt_key`/`derive_kek` helpers directly; `tests/test_auth.py` is the reference.
- **Frontend**: there are no automated UI tests. Verify changes with `npm run typecheck` and, for visuals, a headless Playwright script against a running server (see `web/README.md` → Smoke-testing).

## Known gaps (deliberate, documented)

- Rooms, casts and the key vault are in-process memory: a restart empties the stage (transcripts and accounts persist). Run one uvicorn worker.
- No frontend test suite; no OAuth; model names for DeepSeek/xAI are best guesses and user-editable.
- The roadmap (browser-held keys, spend meter, persistent rooms) is in `src/agentrylab/docs/ROOM.md` → Roadmap.

## Change checklists (things that live in two places)

| If you change… | Also update… |
|---|---|
| a face/body/palette id | both `room/avatars.py` and `web/src/avatars/{faces,bodies}.tsx` / `palettes.ts` |
| a WebSocket event or REST shape | `web/src/types.ts`, `store.applyEvent`, and the tables in `docs/ROOM.md` |
| an environment variable | `.env.example`, `docs/ROOM.md` → Environment, README table |
| the version | `pyproject.toml` **and** `src/agentrylab/version.py`, plus `CHANGELOG.md` |
| a provider or default model | `room/providers.py` catalog (`KEY_PROVIDERS`/`FREE_PROVIDERS`), `build_user_provider`, `docs/ROOM.md` → Brains |
| the room's system prompt | `MockProvider._send_chat` parsing and `tests/test_room.py` |
| an endpoint | keep `tags=`/`summary=` on the decorator (OpenAPI), and the REST table in `docs/ROOM.md` |

## Frontend gotchas

- Motion treats `x`/`y` on SVG elements as CSS translate, not the attribute: set the attribute for position and animate `x: [0, 26, 0]` relative to it. A single-value `animate` (e.g. `{ x: 0 }` or `{ scaleX: 0.5 }`) with `repeat: Infinity` needs a matching `initial`, otherwise Motion replays attribute→target forever. Motion cannot interpolate path `d`; crossfade several paths or scale instead.
- Put `className="tb"` on any SVG group you scale/rotate so it transforms around its own box (`transform-box: fill-box` in `index.css`).
- `@types/react` 19 removed the global `JSX` namespace; use `ReactElement`/`ReactNode` from `react`.
- Google Fonts are linked in `index.html`; the UI falls back to system fonts offline.

## Docs map

`README.md` (overview) → `src/agentrylab/docs/README.md` (index) → `ROOM.md` (web runtime), `CLI.md`, `CONFIG.md` (preset YAML), `ARCHITECTURE.md`, `PERSISTENCE.md`; `web/README.md` (frontend); `SECURITY.md` (secrets model, operator checklist); `CONTRIBUTING.md` (repo map, recipes for new personas/parts/providers/presets). Keep `ROOM.md` authoritative for anything in the Room.
