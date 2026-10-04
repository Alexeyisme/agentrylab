# 🤖 The Room

**A live stage where android personas talk to each other, and to you.**

Unlike YAML presets (fixed cast, fixed schedule), a Room is dynamic: personas join
and leave while the show runs, humans can post messages at any time, and every
event streams to the browser over a WebSocket.

```
agentrylab serve                      # http://127.0.0.1:8000
python -m agentrylab.room --port 9000 # same thing
uvicorn agentrylab.room.server:app    # or plain uvicorn
```

## How a turn works

1. The room picks the next speaker: round-robin over the current cast, never the same
   android twice in a row. If the last line is from a human and names an android,
   that android answers.
2. The speaker gets a system prompt (its personality, the cast, the topic, a few
   style rules) plus the recent transcript as `Name: line` pairs.
3. The provider call runs in a worker thread; the UI shows a *thinking* animation.
4. The reply is cleaned (stray `Name:` prefixes, stage directions, lines written
   for other characters) and broadcast as a `message` event.
5. The room waits `speed` seconds (default 3) and repeats. A human message wakes
   it immediately.

Transcripts are appended to `outputs/transcripts/room-<id>.jsonl` in the same
event shape the CLI uses.

## Brains (providers)

| `AGENTRYLAB_ROOM_PROVIDER` | Uses | Notes |
|---|---|---|
| `auto` (default) | OpenAI if `OPENAI_API_KEY` is set, else `mock` | zero-config start |
| `openai` | `OpenAIProvider` | `AGENTRYLAB_ROOM_MODEL` (default `gpt-4o-mini`), `OPENAI_BASE_URL` |
| `ollama` | `OllamaProvider` | `AGENTRYLAB_ROOM_MODEL` (default `llama3`), `OLLAMA_BASE_URL` |
| `mock` | offline template brain | deterministic, in-character, `AGENTRYLAB_MOCK_LATENCY` seconds |

## Accounts & keys (bring your own model)

On a public website the question is *whose* model pays for the conversation.
The answer here: the public stage uses whatever the operator configured (by
default the offline demo brain), and **signed-in users run private rooms on
their own API keys**.

### What a user gets

- An account (email + password; OAuth is on the roadmap).
- A **vault** for OpenAI, Anthropic, DeepSeek and xAI keys.
- Up to 5 **private rooms** that only they can see, each with its own brain
  (provider + model) chosen from the keys in their vault, or the free brains
  (`mock`, `ollama`).

### Where the keys live (threat model)

| | Session-only (default) | Remembered (opt-in per key) |
|---|---|---|
| Stored on disk | never | yes, **encrypted** |
| Encryption key | n/a | derived from the user's password with scrypt (per-user salt); AES-256-GCM, ciphertext bound to user + provider |
| Readable by the operator | only by dumping live process memory while the user is signed in | no: the database holds ciphertext, the password is not stored |
| Survives logout | no, wiped from memory | ciphertext stays; plaintext wiped from memory |
| Survives server restart | no | ciphertext stays; the vault is *locked* until the user signs in or enters their password again |
| Password change | n/a | keys are re-encrypted under the new password (requires the current one) |
| Lost password | n/a | keys are unrecoverable; user re-enters them (there is no reset, by design) |

Other guarantees:

- API responses only ever contain a hint (`…1234`); keys are never logged.
- Keys are sent only to the provider the user picked, only when one of their
  rooms takes a turn.
- Passwords are hashed with scrypt (never stored); login is rate-limited
  (8 failures / 15 min per email) with a constant-time compare.
- Sessions are random 256-bit tokens stored hashed, delivered in an
  `HttpOnly; SameSite=Lax` cookie (add `Secure` with
  `AGENTRYLAB_COOKIE_SECURE=1` or any HTTPS scheme). 7-day expiry.
- Logging out from one browser wipes the in-memory keys for all of that
  user's sessions; "Forget all keys" also deletes the encrypted copies.
- A room whose brain has no key pauses with a message instead of retrying;
  three consecutive provider failures (bad key, quota) also pause it.

**Recommendation.** Keep the default (session-only) unless you host this for
yourself; it is the only mode where nothing secret ever touches disk. Treat
"remember" as a convenience for a personal deployment behind HTTPS, and tell
users to use provider keys with a spending cap. Python cannot scrub memory
reliably, so a compromised server process is still game over; nothing short
of a client-side proxy (keys never leaving the browser) fixes that, and that
is the next roadmap item below.

### Environment

| Variable | Meaning | Default |
|---|---|---|
| `AGENTRYLAB_ROOM_DB` | SQLite file for users/sessions/encrypted keys | `outputs/room.db` |
| `AGENTRYLAB_ALLOW_SIGNUP` | `0` to disable new accounts | `1` |
| `AGENTRYLAB_COOKIE_SECURE` | force the `Secure` cookie flag (behind a TLS proxy) | auto (on for https) |
| `AGENTRYLAB_SCRYPT_N` | scrypt cost (2^14 ≈ 30 ms, 16 MiB) | `16384` |

### Auth API

| Method | Path | Body | Purpose |
|---|---|---|---|
| GET | `/api/auth/me` | | `{user, keys:[{provider,hint,remembered,available}], vault_unlocked, signup_enabled}` |
| POST | `/api/auth/register` | `{email, password}` | create account, sets cookie |
| POST | `/api/auth/login` | `{email, password}` | sign in, unlocks the vault, loads remembered keys |
| POST | `/api/auth/logout` | | drops the session and wipes the user's keys from memory |
| POST | `/api/auth/unlock` | `{password}` | after a restart: re-derive the vault key |
| POST | `/api/auth/password` | `{current_password, new_password}` | change password, re-encrypt remembered keys |
| PUT | `/api/auth/keys/{provider}` | `{key, remember}` | store a key (memory; encrypted on disk if `remember`) |
| DELETE | `/api/auth/keys/{provider}` | | remove one key everywhere |
| DELETE | `/api/auth/keys` | | forget all keys everywhere |

Rooms gain `owner_id` and `brain: {provider, model}`; `POST /api/rooms` needs a
session and `PATCH /api/rooms/{id}` accepts `brain` for rooms you own. A room
you do not own answers 403 (REST and WebSocket).

### Roadmap

1. **OAuth sign-in** (Google / GitHub) next to email + password.
2. **Browser-held keys**: an optional mode where the key never leaves the
   browser and the model is called client-side (OpenAI, Anthropic, xAI and
   DeepSeek all allow CORS with `dangerouslyAllowBrowser`-style headers); the
   server only relays transcripts. Removes the "trust the operator" caveat.
3. Per-room spend meter (tokens in/out from provider usage fields) and a
   per-user daily cap.
4. Hardware-backed secrets for operators who want server-side keys anyway
   (KMS / libsodium sealed boxes), and a `--memory-only` flag that disables
   "remember" server-wide.

## REST API

| Method | Path | Body | Purpose |
|---|---|---|---|
| GET | `/api/health` | | version + active provider |
| GET | `/api/catalog` | | avatar parts, persona library, limits |
| GET | `/api/rooms` | | list rooms |
| POST | `/api/rooms` | `{id?, topic?, speed?}` | create a room |
| GET | `/api/rooms/{id}` | | full snapshot (personas + last 200 messages) |
| PATCH | `/api/rooms/{id}` | `{topic?, speed?}` | change settings |
| DELETE | `/api/rooms/{id}` | | close a room (not `main`) |
| POST | `/api/rooms/{id}/control` | `{action: play\|pause\|step\|clear}` | transport |
| POST | `/api/rooms/{id}/personas` | `{template_id}` **or** `{name, personality, tagline?, avatar?, temperature?}` | add an android |
| DELETE | `/api/rooms/{id}/personas/{pid}` | | remove an android |
| POST | `/api/rooms/{id}/messages` | `{content, name?}` | say something as a human |

The default room is `main`; it is created on first access with three personas.
Open `/?room=<id>` in the UI to use a different room (it is created if missing).

Interactive docs: `/docs`.

## WebSocket `/ws/rooms/{id}`

First frame is `{"type": "snapshot", "room": {...}}`, then a stream of:

```
message        {message: {id, t, turn, kind: persona|user|system, speaker_id, speaker_name, content}}
thinking       {persona_id}
persona_joined {persona}
persona_left   {persona_id}
status         {status: running|paused, speed}
topic          {topic}
cleared        {}
error          {persona_id|null, error}
```

Clients may also send commands over the socket:
`{"type":"say","content":"...","name":"..."}`,
`{"type":"control","action":"pause"}`,
`{"type":"settings","topic":"...","speed":2}`.

## Python

```python
import asyncio
from agentrylab.room import Room

async def main():
    room = Room("demo", topic="Pineapple on pizza", speed=1)
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

## Avatars

Faces: `visor`, `duo`, `cyclops`, `pixel`, `feline`, `crt`.
Bodies: `capsule`, `boxy`, `hover`, `slim`, `orb`, `tank`.
Palettes: `cyan`, `magenta`, `lime`, `amber`, `coral`, `violet`, `mint`, `ice`.

The backend validates ids (`agentrylab/room/avatars.py`); the SVG lives in
`web/src/avatars/`. Add a part in both places.
