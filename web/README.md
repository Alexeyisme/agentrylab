# AgentryLab Room — web UI

Vite 6 + React 19 + TypeScript + Tailwind CSS v4 + [Motion](https://motion.dev) + Zustand.
No component library: every control is a few Tailwind classes, every animation is Motion.

## Develop

```bash
# terminal 1: API (any provider; no key = demo brain)
pip install -e '.[web]'
agentrylab serve --reload

# terminal 2: UI with hot reload, proxies /api and /ws to :8000
cd web
npm install
npm run dev          # http://localhost:5173
```

| Script | Purpose |
|---|---|
| `npm run dev` | Vite dev server with HMR; `AGENTRYLAB_API=http://host:port` changes the proxy target |
| `npm run build` | Typecheck + production build into `web/dist` |
| `npm run typecheck` | `tsc` only (what CI runs before the build) |
| `npm run preview` | Serve the production build locally |

`agentrylab serve` picks up `web/dist` automatically (or `AGENTRYLAB_WEB_DIST`).
`make web-bundle` copies the build into the Python package so a wheel ships the UI.

## Layout

```
src/
  main.tsx, App.tsx     bootstrap; App owns the layout and which modal is open
  index.css             Tailwind import, design tokens (@theme), glass/floor/noise helpers
  types.ts              wire types shared with the backend (Persona, Message, RoomEvent, Me, …)
  api.ts                thin fetch wrapper for every REST endpoint
  store.ts              zustand store: room state, auth state, WebSocket client (auto-reconnect), actions
  avatars/
    palettes.ts         accent colours (keep in sync with agentrylab/room/avatars.py)
    faces.tsx           6 heads: eyes blink, gaze wanders while thinking, mouths animate while talking
    bodies.tsx          6 bodies: chest light pulses, arms gesture, thrusters/treads move
    Android.tsx         composes face + body, ambient bob, head tilt, floor glow — driven by `mood`
  components/
    TopBar.tsx          topic, transport (play/pause/step/speed), add button, brain badge, rooms menu, user menu
    Stage.tsx           the room: androids in a responsive grid, speech bubbles, the human guest
    AndroidCard.tsx     one android + nameplate + bubble/thinking dots + remove button + personality tooltip
    SpeechBubble.tsx    word-by-word typewriter bubble
    Guest.tsx           the human on stage (silhouette + last line)
    ChatLog.tsx         transcript panel with mini avatars; auto-scrolls when near the bottom
    Composer.tsx        name + message input; Enter sends
    AddPersonaModal.tsx library grid + "build your own" with live preview
    AuthModal.tsx       sign in / create account
    KeysModal.tsx       "Brains & keys": per-provider key rows, remember toggle, unlock banner, forget all
    RoomsMenu.tsx       room switcher dropdown, NewRoomModal, BrainPicker (provider + model)
    BrainBadge.tsx      which model drives the room; owners click it to switch
    Modal.tsx           shared dialog shell + form primitives (Field, inputCls, primaryBtn, ErrorLine)
    Toasts.tsx          bottom-left notifications
```

## How state flows

1. `App` calls `store.init()`: loads `/api/catalog` and `/api/auth/me`, lists rooms,
   then opens the WebSocket for the room in `?room=` (default `main`).
2. The first socket frame is a full snapshot; every later event is applied by
   `store.applyEvent()` (messages, thinking, joins/leaves, status, topic, brain, errors).
3. Each android's **mood** (`idle` / `thinking` / `talking`) is derived in `Stage`
   from `thinking` and `speaking` in the store. `talking` lasts while the bubble's
   typewriter runs, then `finishedSpeaking()` flips it back to idle.
4. User actions call REST through `api.ts`; the server echoes the result as a
   socket event, so the UI never has to update state optimistically.
5. Auth state (`me`) drives what is visible: the Sign in button vs. the user
   menu, which brains are selectable, whether a room's brain badge is editable.
   Private rooms the user cannot access close the socket with code 4003 and the
   UI bounces back to the public stage.

## Adding things

- **A face or body**: draw it in `faces.tsx` / `bodies.tsx` as a function of
  `{ accent, mood, seed }`, use `className="tb"` on anything you scale so it
  scales around its own centre, register it in `FACES` / `BODIES`, and add the
  id to the Python catalog in `agentrylab/room/avatars.py`.
- **A new event type**: extend `RoomEvent` in `types.ts` and handle it in
  `store.applyEvent`; TypeScript will point at the missing case.
- **A new endpoint**: add a function to `api.ts` and an action to the store;
  components only ever talk to the store.

## Conventions

- Dark theme only; colours are tokens in `index.css` (`ink-*`, `shell-*`, `fog-*`).
- Fonts: Space Grotesk (display) and JetBrains Mono (labels), loaded from Google
  Fonts with system fallbacks.
- Keep components free of fetch calls and WebSocket code; that lives in the store.
- Never render an API key: the backend only returns a `…1234` hint, and the key
  inputs are `type="password"` with autocomplete off.
