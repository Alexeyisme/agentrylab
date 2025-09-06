# Changelog

All notable changes to this project will be documented in this file.

## [0.1.2] - 2025-01-27
### 🚀 Major Improvements
- **Complete preset optimization**: All 10 presets now production-ready with optimal provider assignments
- **Strategic provider strategy**: llama3 for single-agent tasks, GPT-4o-mini for complex multi-agent workflows
- **README.md rewrite**: New catchy, hacky, sarcastic crazy scientist vibe with accurate examples
- **Preset consolidation**: Removed 7 redundant/underperforming presets, kept 10 optimized ones

### 🎯 Preset Optimizations
- **research.yaml**: Switched to GPT-4o-mini, removed problematic moderator, added seed content
- **argue.yaml**: Switched agent1 to GPT-4o-mini, added empty response prevention
- **drifty_thoughts.yaml**: Switched all agents to GPT-4o-mini for reliable multi-agent performance
- **therapy_session.yaml**: Switched all agents to GPT-4o-mini
- **brainstorm_buddies.yaml**: Switched all agents to GPT-4o-mini
- **debates.yaml**: Added empty response prevention to pro agent
- **solo_chat_user.yaml**: Fixed user role linting, increased timeout, added empty response prevention
- **ddg_quick_summary.yaml**: Fixed objective text usage, added empty response prevention
- **small_talk.yaml**: Added topic adherence and empty response prevention
- **standup_club.yaml**: Already optimized (hybrid approach working well)

### 🗑️ Preset Cleanup
- **Removed**: argue_llama.yaml, brainstorm.yaml, follow_up.yaml, simple_chat.yaml, solo_chat.yaml, standup_club_llama.yaml, user_in_the_loop.yaml
- **Consolidated**: Multiple variants merged into single optimized presets
- **Result**: Clean, focused preset collection with 10 production-ready environments

### 🐛 Bug Fixes
- **Empty response prevention**: Added explicit instructions to prevent llama3 empty responses
- **Timeout increases**: Increased provider timeouts from 10s to 30s for better reliability
- **Objective text usage**: Fixed ddg_quick_summary.yaml to use actual objective text
- **User role handling**: Fixed linting issues with user role in solo_chat_user.yaml
- **System prompt optimization**: Simplified prompts for better llama3 compatibility

### 📚 Documentation
- **README.md**: Complete rewrite with crazy scientist vibe, accurate examples, clear provider sections
- **CLI.md**: Updated examples to use existing presets only
- **Examples**: All documentation now uses real, working preset names

### 🔧 Technical Improvements
- **Provider strategy**: Intelligent assignment based on task complexity
- **Error handling**: Better empty response detection and prevention
- **Performance**: Optimized timeouts and context windows
- **Reliability**: All presets tested and verified working
- **Enhanced logging**: Added comprehensive trace logging for agent input context debugging

## [0.1.1] - 2025-09-05
### Added
- CLI accepts packaged preset names (e.g., `solo_chat.yaml`) in addition to file paths
- Llama‑only variants: `argue_llama.yaml`, `standup_club_llama.yaml`
- Provider notes in mixed presets (argue, standup_club, debates)
- New simple presets verified locally: `solo_chat.yaml`, `simple_chat.yaml`, `brainstorm.yaml`

### Changed
- README examples updated to use name‑based presets
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
