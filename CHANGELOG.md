# Changelog

All notable changes to this project will be documented in this file.

## [0.1.1.dev0] - Unreleased
### Added
- Llama‑only variants: `argue_llama.yaml`, `standup_club_llama.yaml`
- Provider notes in mixed presets (argue, standup_club, debates)
- New simple presets verified locally: `solo_chat.yaml`, `simple_chat.yaml`, `brainstorm.yaml`

### Changed
- Minor preset tweaks for clarity and local friendliness

## [0.1.0] - 2025-09-05
Initial public release.

- Python API: `init`/`init_lab`, `run`, `Lab.run/stream/clean/history/status`, `list_threads`
- Streaming controls: `on_event`, `timeout_s`, `stop_when`, `on_tick`/`on_round` (typed `ProgressInfo`)
- Persistence: JSONL transcripts + SQLite checkpoints; `lab.clean()`; docs for schemas/fields
- CLI: `run`, `status`, `validate`, `extend`, `reset`, `ls` with streaming and resume
- Tool budgets: per-run and per-iteration (global and per-tool); enforced by `State`
- Runtime: Agent/Moderator/Summarizer/Advisor nodes; scheduler (Round‑Robin, Every‑N); engine actions (STOP/STEP_BACK)
- Providers: OpenAI, Ollama adapters; Tools: ddgs, Wolfram Alpha
- Packaged presets: debates.yaml and helpers (`agentrylab.presets.path`)
- Tests: broad coverage including CLI, budgets, actions, persistence shapes; green on CI
- Docs: README (CLI + Python quickstarts, recipes), CLI/Persistence/Architecture guides
- Packaging: PEP 621 pyproject, dev extras, CI for lint/tests, release workflow (tags → PyPI)

[0.1.0]: https://github.com/Alexeyisme/agentrylab/releases/tag/v0.1.0
