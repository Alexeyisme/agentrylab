# Contributing to Agentry Lab

Thanks for your interest in improving Agentry Lab! PRs are welcome, from quick bug fixes and docs edits to new presets, personas, providers and UI polish.

## Quick start (Python)

- Fork the repo and create a feature branch
- Python 3.11/3.12 recommended
- Create a venv and install dev deps (includes the web server and test tooling):
  - `python -m venv .venv && . .venv/bin/activate`
  - `python -m pip install -U pip`
  - `python -m pip install -e '.[dev]'`
- Run lint and tests:
  - `ruff check .`
  - `pytest -q`

## Quick start (web UI)

The Room's frontend lives in `web/` (Vite + React + TypeScript + Tailwind + Motion).

- `cd web && npm install`
- `npm run dev` for hot reload on http://localhost:5173 (proxies `/api` and `/ws` to a server started with `agentrylab serve --reload`)
- `npm run build` writes `web/dist`, which `agentrylab serve` picks up automatically
- `npm run typecheck` is what CI runs (plus the build)

Stack, folder layout and the animation model are described in [`web/README.md`](web/README.md).

## Repository map

| Path | What lives there |
|---|---|
| `src/agentrylab/lab.py`, `api.py` | Python API (`init`, `run`, `Lab`) |
| `src/agentrylab/runtime/` | Engine, nodes, schedulers, providers, tools for YAML presets |
| `src/agentrylab/presets/` | Packaged YAML presets |
| `src/agentrylab/room/` | The Room: live rooms, personas, accounts, key vault, FastAPI server |
| `src/agentrylab/cli/` | Typer CLI (`run`, `say`, `status`, `serve`, …) |
| `src/agentrylab/docs/` | User documentation ([index](src/agentrylab/docs/README.md)) |
| `web/` | Frontend |
| `tests/` | Pytest suite; `test_room.py` and `test_auth.py` cover the web runtime without network |

## Common contributions

- **A new persona**: add an entry to `PERSONA_LIBRARY` in `src/agentrylab/room/personas.py` (name, tagline, personality prompt, avatar parts, noun-like `voice` words for the demo brain). Tests check ids are unique and fields are filled.
- **A new avatar part**: add the id in `src/agentrylab/room/avatars.py`, draw it in `web/src/avatars/faces.tsx` or `bodies.tsx` honouring the `mood` prop, and register it in the `FACES`/`BODIES` map.
- **A new provider**: subclass `LLMProvider` in `src/agentrylab/runtime/providers/`, implement `_send_chat`, and (for the Room) add a catalog entry in `src/agentrylab/room/providers.py` plus a branch in `build_user_provider`.
- **A new preset**: drop a YAML file into `src/agentrylab/presets/`; see [CONFIG.md](src/agentrylab/docs/CONFIG.md).

## Project philosophy

- Lightweight and readable: prefer clarity over cleverness
- Minimal ceremony: keep APIs small, docs helpful, examples runnable
- Solid tests: prioritise deterministic tests without network access (the Room tests inject fake providers; never call a real API in tests)
- Secrets stay secret: never log API keys, never return them from an endpoint, never write them to transcripts (see [SECURITY.md](SECURITY.md))

## Before you open a PR

- Add or update tests to cover your change
- Keep changes focused; smaller PRs are easier to review
- Update README / docs when changing public APIs, endpoints, events or behaviour (`src/agentrylab/docs/ROOM.md` for anything in the Room)
- Run `ruff check .`, `pytest -q`, and `cd web && npm run build` if you touched the UI

## Commit style

Conventional and descriptive is great:
- `fix: correct tool budget counter update`
- `feat: add Lab.clean() API`
- `docs: expand Python API examples`

## Running examples

Some presets and the real brains need API keys. Put them in a local `.env` (see [`.env.example`](.env.example)); the file is git-ignored.

## Release flow (maintainers)

- Releases run via GitHub Actions on tag push (see `.github/workflows/release.yml`)
- Bump the version in `pyproject.toml` **and** `src/agentrylab/version.py`, update `CHANGELOG.md`, build the UI into the package with `make web-bundle` if the wheel should ship it, then tag: `git tag -a vX.Y.Z -m 'vX.Y.Z' && git push --tags`

## Questions?

Open a discussion or issue on GitHub.
