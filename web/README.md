# AgentryLab Room — web UI

Vite + React 19 + TypeScript + Tailwind CSS v4 + [Motion](https://motion.dev) + Zustand.

```bash
# terminal 1: API (any provider; no key = demo brain)
pip install -e '.[web]'
agentrylab serve --reload

# terminal 2: UI with hot reload, proxies /api and /ws to :8000
cd web
npm install
npm run dev          # http://localhost:5173
```

`npm run build` writes `web/dist`; `agentrylab serve` picks it up automatically
(or point `AGENTRYLAB_WEB_DIST` at any build). `make web-bundle` copies the build
into the Python package so a wheel ships the UI.

## Layout

```
src/
  avatars/        procedural SVG androids
    faces.tsx     6 heads: eyes blink, gaze wanders while thinking, mouths animate while talking
    bodies.tsx    6 bodies: chest light pulses, arms gesture, thrusters/treads move
    Android.tsx   composes face + body, ambient bob, head tilt, floor glow — driven by `mood`
  components/
    Stage.tsx     the room: androids, speech bubbles, the human guest
    AndroidCard   one android + nameplate + bubble + remove/tooltip
    SpeechBubble  word-by-word typewriter
    ChatLog, Composer, TopBar, AddPersonaModal (library + builder), Toasts
  store.ts        zustand store + WebSocket client (auto-reconnect)
  api.ts          REST calls
```

Every animation is a function of a persona's **mood** (`idle` / `thinking` / `talking`),
which the store derives from server events, so new parts only need to honour that
prop to get the full behaviour.
