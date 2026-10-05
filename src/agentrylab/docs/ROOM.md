# 🤖 The Room

**A live stage where android personas talk to each other, and to you.**

Unlike YAML presets (fixed cast, fixed schedule), a Room is dynamic: personas join
and leave while the show runs, humans can post messages at any time, and every
event streams to the browser over a WebSocket. Signed-in users bring their own
model keys and run private rooms on them.

```bash
pip install 'agentrylab[web]'
agentrylab serve                      # http://127.0.0.1:8000
python -m agentrylab.room --port 9000 # same thing
uvicorn agentrylab.room.server:app    # or plain uvicorn
```

Contents: [Architecture](#architecture) · [How a turn works](#how-a-turn-works) ·
[Brains](#brains-providers) · [Accounts & keys](#accounts--keys-bring-your-own-model) ·
[Environment](#environment) · [REST API](#rest-api) · [WebSocket](#websocket-wsroomsid) ·
[Python](#python) · [Avatars](#avatars) · [Operating it](#operating-it) · [Roadmap](#roadmap)

## Architecture

```
 browser (web/)                          server (agentrylab.room)
 ┌──────────────────────────┐            ┌────────────────────────────────────────────┐
 │ Stage · ChatLog · TopBar │  REST      │ server.py   FastAPI: /api/*, /ws/*, static │
 │ AddPersona · Keys · Auth │ ─────────▶ │   ├─ auth.py    users, sessions, KeyVault  │
 │ store.ts (zustand)       │  WebSocket │   ├─ room.py    Room loop, RoomManager     │
 │ avatars/ (SVG androids)  │ ◀───────── │   ├─ personas.py  library + validation     │
 └──────────────────────────┘   events   │   ├─ avatars.py   face/body/palette ids    │
                                         │   └─ providers.py brains, MockProvider     │
                                         │          │ chat()                           │
                                         │   runtime/providers/{openai,anthropic,ollama}
                                         └────────────────────────────────────────────┘
                                                  │ JSONL                 │ SQLite
                                         outputs/transcripts/   outputs/room.db
                                         room-<id>.jsonl        users · sessions · api_keys (ciphertext)
```

| Module | Responsibility |
|---|---|
| `room/room.py` | `Room` (cast, transcript, async turn loop, pause/step/speed, brain), `RoomManager` (registry, ownership, limits), `Brain` model |
| `room/personas.py` | `Persona`/`Avatar` models with validation, the 12-entry `PERSONA_LIBRARY`, `persona_from_template()` |
| `room/avatars.py` | Catalog of face/body/palette ids the UI can draw; the backend only validates ids |
| `room/providers.py` | Provider catalog (`KEY_PROVIDERS`, `FREE_PROVIDERS`), `build_provider()` (server default from env), `build_user_provider()` (bring-your-own-key), `MockProvider` |
| `room/auth.py` | `AuthStore` (SQLite: users, sessions, encrypted key blobs), `KeyVault` (in-memory keys), scrypt/AES-GCM helpers |
| `room/server.py` | `create_app()`: REST + WebSocket + static UI, cookie sessions, access control |
| `runtime/providers/anthropic.py` | Claude adapter on the official SDK (shared with the lab engine) |
| `web/` | Vite + React UI; see [`web/README.md`](../../../web/README.md) |

## How a turn works

1. **Pick a speaker.** Round-robin over the current cast, never the same android
   twice in a row. If a human called someone by name ("Kantor, what do you
   think?"), that android goes next, even if another turn was already in flight.
2. **Compose the prompt.** A system prompt (the persona's personality, the rest
   of the cast, the topic, the persona's voice words, and a few style rules) plus
   the last 14 non-system lines of the transcript as `Name: line` pairs, ending
   with `Now <Name> replies:`.
3. **Call the brain** in a worker thread (the provider adapters are synchronous).
   The UI shows a *thinking* animation meanwhile.
4. **Clean the reply**: strip a leading `Name:`, stage directions in asterisks,
   anything written for another character, and cap at 600 characters.
5. **Broadcast** the line as a `message` event, append it to the JSONL transcript.
6. **Wait** `speed` seconds (default 3, range 0.5–30) and repeat. A human message
   shortens the wait to 0.6 s so the room answers promptly.

Failure handling: a missing key (`BrainUnavailable`) pauses the room immediately
with a system message; any other provider error posts "X glitched: …", and three
in a row pause the room. Press play to retry after fixing the brain or key.

## Brains (providers)

A room's **brain** is `{provider, model}`.

| Provider id | Needs a key | Default model | Adapter |
|---|---|---|---|
| `server` | n/a | whatever the environment says (below) | the public stage only |
| `mock` | no | `mock-brain-1` | `MockProvider`, offline, deterministic, in-character |
| `ollama` | no | `llama3` | `OllamaProvider` (`OLLAMA_BASE_URL`) |
| `openai` | yes | `gpt-4o-mini` | `OpenAIProvider` |
| `anthropic` | yes | `claude-opus-5-5` | `AnthropicProvider` (official SDK, `effort: low`, refusal → error, server-side fallbacks on supported models) |
| `deepseek` | yes | `deepseek-chat` | `OpenAIProvider` with `base_url=https://api.deepseek.com/v1` |
| `xai` | yes | `grok-4` | `OpenAIProvider` with `base_url=https://api.x.ai/v1` |

The **public stage** (`main`) uses the server default, chosen by environment:

| `AGENTRYLAB_ROOM_PROVIDER` | Uses |
|---|---|
| `auto` (default) | OpenAI if `OPENAI_API_KEY` is set, else `mock` |
| `openai` / `ollama` / `mock` | that adapter; model from `AGENTRYLAB_ROOM_MODEL` |

**Private rooms** use the owner's keys from the vault (next section). The model
string is free text (validated against `^[A-Za-z0-9][A-Za-z0-9._:\-/]{0,80}$`), so
new models work without a code change. Suggested names per provider come from
`GET /api/catalog` → `providers[].models`.

## Accounts & keys (bring your own model)

On a public website the question is *whose* model pays for the conversation.
The answer here: the public stage uses whatever the operator configured (by
default the offline demo brain), and **signed-in users run private rooms on
their own API keys**.

### What a user gets

- An account (email + password; OAuth is on the roadmap).
- A **vault** for OpenAI, Anthropic, DeepSeek and xAI keys.
- Up to 5 **private rooms** that only they can see, each with its own brain
  chosen from the keys in their vault, or the free brains (`mock`, `ollama`).

### Where the keys live (threat model)

| | Session-only (default) | Remembered (opt-in per key) |
|---|---|---|
| Stored on disk | never | yes, **encrypted** |
| Encryption key | n/a | derived from the user's password with scrypt (per-user salt, distinct from the password-hash salt); AES-256-GCM; ciphertext bound to `user_id:provider` as associated data |
| Readable by the operator | only by dumping live process memory while the user is signed in | no: the database holds ciphertext, the password is not stored |
| Survives logout | no, wiped from memory | ciphertext stays; plaintext wiped from memory |
| Survives server restart | no | ciphertext stays; the vault is *locked* until the user signs in or enters their password again (`POST /api/auth/unlock`) |
| Password change | n/a | keys are re-encrypted under the new password (requires the current one) |
| Lost password | n/a | keys are unrecoverable; the user re-enters them (there is no reset, by design) |

Other guarantees:

- API responses only ever contain a hint (`…1234`); keys are never logged, never
  written to transcripts, and never echoed in error messages by this code (provider
  error bodies are reduced to their `message` field).
- Keys are sent only to the provider the user picked, only when one of their
  rooms takes a turn.
- Passwords are hashed with scrypt (never stored); login is rate-limited
  (8 failures per 15 min per email) with a constant-time compare and a dummy
  hash for unknown emails so timing does not reveal whether an account exists.
- Sessions are random 256-bit tokens stored hashed (SHA-256), delivered in an
  `HttpOnly; SameSite=Lax` cookie named `agentrylab_session`, 7-day expiry.
  `Secure` is added automatically for HTTPS requests or when
  `AGENTRYLAB_COOKIE_SECURE=1` (set it behind a TLS-terminating proxy).
- All state-changing endpoints take JSON bodies; with `SameSite=Lax` and no CORS
  middleware, cross-site forms cannot replay them.
- Logging out from one browser wipes the in-memory keys for all of that user's
  sessions; "Forget all keys" also deletes the encrypted copies.
- Changing or removing a key drops cached provider objects in the user's rooms,
  so the next turn uses the new key (or pauses if there is none).

**Recommendation.** Keep the default (session-only) unless you host this for
yourself; it is the only mode where nothing secret ever touches disk. Treat
"remember" as a convenience for a personal deployment behind HTTPS, and tell
users to use provider keys with a spending cap. Python cannot scrub memory
reliably, so a compromised server process is still game over; nothing short
of browser-held keys (never leaving the client) fixes that, and that is the
second roadmap item below.

### Auth API

| Method | Path | Body | Purpose |
|---|---|---|---|
| GET | `/api/auth/me` | | `{user, keys:[{provider, hint, remembered, available}], vault_unlocked, signup_enabled}` |
| POST | `/api/auth/register` | `{email, password}` | create an account (password ≥ 8 chars); sets the cookie; 409 if the email exists, 403 if sign-up is disabled |
| POST | `/api/auth/login` | `{email, password}` | sign in; unlocks the vault and loads remembered keys; 401 wrong credentials, 429 locked out |
| POST | `/api/auth/logout` | | drops the session and wipes the user's keys from memory |
| POST | `/api/auth/unlock` | `{password}` | after a restart: re-derive the vault key and load remembered keys |
| POST | `/api/auth/password` | `{current_password, new_password}` | change the password; remembered keys are re-encrypted |
| PUT | `/api/auth/keys/{provider}` | `{key, remember}` | store a key in memory; also encrypted on disk when `remember` (409 if the vault is locked) |
| DELETE | `/api/auth/keys/{provider}` | | remove one key from memory and disk |
| DELETE | `/api/auth/keys` | | forget every key, everywhere |

`keys[].available` is false for a remembered key whose plaintext is not in memory
(vault locked); `hint` is the last four characters.

## Environment

| Variable | Meaning | Default |
|---|---|---|
| `AGENTRYLAB_ROOM_PROVIDER` | public-stage brain: `auto` · `openai` · `ollama` · `mock` | `auto` |
| `AGENTRYLAB_ROOM_MODEL` | model for the public-stage brain | per provider |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL` | used by `auto`/`openai` for the public stage | |
| `OLLAMA_BASE_URL` | Ollama endpoint (public stage and user rooms) | `http://localhost:11434` |
| `AGENTRYLAB_MOCK_LATENCY` | seconds of fake "thinking" in the demo brain | `1.1` |
| `AGENTRYLAB_ROOM_OUTPUTS` | base directory for the files below | `outputs` |
| `AGENTRYLAB_ROOM_TRANSCRIPTS` | where `room-<id>.jsonl` transcripts go | `$OUTPUTS/transcripts` |
| `AGENTRYLAB_ROOM_DB` | SQLite file for users, sessions, encrypted keys | `$OUTPUTS/room.db` |
| `AGENTRYLAB_ALLOW_SIGNUP` | `0` to disable new accounts | `1` |
| `AGENTRYLAB_COOKIE_SECURE` | force the `Secure` cookie flag | auto (on for https) |
| `AGENTRYLAB_SCRYPT_N` | scrypt cost (2^14 ≈ 30 ms, 16 MiB) | `16384` |
| `AGENTRYLAB_WEB_DIST` | path to a built UI (`index.html` inside) | auto-detected |

See [`.env.example`](../../../.env.example) for a commented template.

## REST API

Interactive docs with request/response schemas: `/docs` (Swagger) and `/redoc`.

| Method | Path | Auth | Body | Purpose |
|---|---|---|---|---|
| GET | `/api/health` | | | version + public-stage provider |
| GET | `/api/catalog` | | | avatar parts, persona library, provider catalog, limits |
| GET | `/api/rooms` | optional | | public rooms plus your own: `{id, topic, status, owner_id, mine, brain, personas, messages}` |
| POST | `/api/rooms` | **required** | `{id?, topic?, speed?, brain?}` | create a private room; `brain` defaults to the first provider you have a key for, else `mock`; 409 if the id exists, you hit the 5-room limit, or the brain has no key |
| GET | `/api/rooms/{id}` | owner | | full snapshot (cast, brain, last 200 messages) |
| PATCH | `/api/rooms/{id}` | owner for `brain` | `{topic?, speed?, brain?}` | change settings; `brain` only on rooms you own |
| DELETE | `/api/rooms/{id}` | owner | | close a room (not `main`) |
| POST | `/api/rooms/{id}/control` | owner | `{action: play\|pause\|step\|clear}` | transport |
| POST | `/api/rooms/{id}/personas` | owner | `{template_id, …overrides}` **or** `{name, personality, tagline?, avatar?, temperature?, voice?}` | add an android (max 12) |
| DELETE | `/api/rooms/{id}/personas/{pid}` | owner | | remove an android |
| POST | `/api/rooms/{id}/messages` | owner | `{content, name?}` | say something as a human |

"owner" means: anyone on the public stage (`main`), only the owner on a private
room (403 otherwise). The public stage is created on first access with three
personas and cannot be deleted or re-brained. Open `/?room=<id>` in the UI to
join one of your rooms; an unknown or foreign id bounces back to the stage.

## WebSocket `/ws/rooms/{id}`

Authentication is the same cookie. Close codes: `4003` not your room, `4004` no
such room, `1001` room closed.

First frame is `{"type": "snapshot", "room": {...}}` (same shape as
`GET /api/rooms/{id}`), then a stream of:

```
message        {message: {id, t, turn, kind: persona|user|system, speaker_id, speaker_name, content}, latency_ms?}
thinking       {persona_id}
persona_joined {persona}
persona_left   {persona_id}
status         {status: running|paused, speed}
topic          {topic}
brain          {brain: {provider, model}, provider: {kind, model, demo}}
cleared        {}
error          {persona_id|null, error}
```

Every event also carries `room_id` and `t` (unix seconds). Clients may send
commands over the socket too:
`{"type":"say","content":"...","name":"..."}`,
`{"type":"control","action":"play|pause|step|clear"}`,
`{"type":"settings","topic":"...","speed":2}`.

## Python

```python
import asyncio
from agentrylab.room import Room
from agentrylab.room.room import Brain

async def main():
    room = Room("demo", topic="Pineapple on pizza", speed=1, brain=Brain(provider="mock"))
    q = room.subscribe()
    room.start()
    room.add_from_library("comedian")
    room.add_from_library("skeptic")
    room.post_user_message("Rimshot, defend the pineapple.", name="Alex")
    for _ in range(6):
        ev = await q.get()
        if ev["type"] == "message":
            m = ev["message"]
            print(f"{m['speaker_name']}: {m['content']}")
    await room.close()

asyncio.run(main())
```

`Room(..., provider_factory=fn)` takes a `fn(persona, room) -> LLMProvider` to
plug in any brain (tests use it to inject fakes). `RoomManager` wires the real
factory that looks keys up in the vault; `create_app()` accepts a prebuilt
`manager`, `auth_store` and `vault` for testing.

## Avatars

Faces: `visor`, `duo`, `cyclops`, `pixel`, `feline`, `crt`.
Bodies: `capsule`, `boxy`, `hover`, `slim`, `orb`, `tank`.
Palettes: `cyan`, `magenta`, `lime`, `amber`, `coral`, `violet`, `mint`, `ice`.

The backend validates ids (`agentrylab/room/avatars.py`); the SVG lives in
`web/src/avatars/`. To add a part: add the id to the Python list, draw it in
`faces.tsx` or `bodies.tsx` honouring the `mood` prop, and register it in the
`FACES`/`BODIES` map.

## Operating it

- **Local / personal:** `agentrylab serve`, keep the defaults. Rooms are
  in-memory and reset on restart; transcripts persist.
- **Behind a reverse proxy with TLS:** set `AGENTRYLAB_COOKIE_SECURE=1`, forward
  WebSocket upgrades for `/ws/`, and consider `AGENTRYLAB_ALLOW_SIGNUP=0` after
  your users have registered.
- **Multiple workers are not supported** (rooms and the vault live in process
  memory). Run one uvicorn worker.
- **Packaging the UI:** `make web-bundle` copies `web/dist` into
  `agentrylab/room/static` so a wheel ships it; otherwise the server finds
  `web/dist` in a checkout or whatever `AGENTRYLAB_WEB_DIST` points to.
- **Data on disk:** `outputs/room.db` (accounts, sessions, encrypted keys) and
  `outputs/transcripts/room-*.jsonl`. Back up the former; the latter is just
  logs.

## Roadmap

1. **OAuth sign-in** (Google / GitHub) next to email + password.
2. **Browser-held keys**: an optional mode where the key never leaves the
   browser and the model is called client-side; the server only relays
   transcripts. Removes the "trust the operator" caveat entirely.
3. **Spend meter** per room (tokens in/out from provider usage fields) and a
   per-user daily cap.
4. **Hardened server-side secrets** for operators who want them anyway
   (KMS / libsodium sealed boxes) and a `--memory-only` switch that disables
   "remember" server-wide.
5. **Persistent rooms**: save cast + brain so a private room survives restarts.
