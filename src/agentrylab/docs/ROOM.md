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
