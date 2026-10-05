# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-10-04
### 🤖 The Room: a zero-player android stage (web UI)
- **New `agentrylab serve`**: FastAPI server with REST + WebSocket API and a built-in web UI
- **Live rooms**: add/remove personas while the conversation runs; humans can join and are answered by name
- **12-persona library** plus a builder for custom personalities with selectable faces, bodies and colours
- **Procedural SVG androids** with mood-driven micro-animations (blink, bob, thinking pulse, talking mouths, gesturing arms)
- **Offline demo brain**: runs without any API key; OpenAI/Ollama picked up from the environment
- **New `web/` frontend**: Vite + React 19 + TypeScript + Tailwind v4 + Motion + Zustand, built in CI
- New optional extra `agentrylab[web]`; docs in `src/agentrylab/docs/ROOM.md`

### 🔐 Accounts and bring-your-own-key vault
- **Email + password accounts** (scrypt, rate-limited login, HttpOnly session cookies)
- **Key vault** for OpenAI, Anthropic, DeepSeek and xAI: keys live in server memory only and are wiped on sign-out, "forget", or restart; opt-in "remember" stores them AES-256-GCM encrypted under a password-derived key
- **Private rooms** per user that run on the owner's keys; brain (provider + model) switchable per room; rooms pause with a clear message when a key is missing or failing
- New `AnthropicProvider` (official SDK) and OpenAI-compatible DeepSeek/xAI wiring

### 📚 Documentation
- `ROOM.md` rewritten: architecture map, turn lifecycle, brains, threat model, full REST/WS reference, operating notes, roadmap
- `.env.example`, updated CLI/CONFIG/ARCHITECTURE guides, CONTRIBUTING repository map, SECURITY hardening checklist, OpenAPI summaries on every endpoint

## [0.1.7] - 2025-01-27
### 🎭 Complete Telegram API Implementation
- **Full Telegram API**: Complete async implementation with event streaming
- **Comprehensive Final Summaries**: Debates now generate structured summaries with evidence and recommendations
- **Multi-agent Coordination**: Pro, Con, Moderator, and Summarizer working together seamlessly
- **Production-ready**: Robust error handling, cleanup, and comprehensive test coverage (79%)
- **Enhanced Documentation**: Clear usage examples and API documentation

### 🔧 Technical Improvements
- **Async Event Streaming**: Real-time conversation monitoring with proper async handling
- **Final Summary Generation**: `run_on_last=true` configuration for comprehensive debate conclusions
- **New API Methods**: `get_final_summary()` for accessing structured debate outcomes
- **Test Suite**: 102 tests passing with 61% coverage, including async test support
- **CI/CD Ready**: GitHub Actions configured with pytest-asyncio for async test support

### 📚 Documentation & Examples
- **run_debates_demo.py**: Complete demonstration of debate functionality
- **Enhanced Presets**: Updated debates.yaml with comprehensive final summary features
- **API Reference**: Detailed documentation for all Telegram API methods

## [0.1.6] - 2025-01-27
### 🚀 Telegram Bot Integration
- **Added TelegramAdapter**: New telegram module for Telegram bot integration
- **Enhanced multi-agent support**: Better integration with external bot frameworks
- **Improved API compatibility**: Enhanced support for real-time conversation management

## [0.1.4] - 2025-01-27
### 🚀 Performance & Reliability Improvements
- **Fixed empty response issues**: Switched debates and standup_club presets from llama3 to gpt-4o-mini for all agents
- **Eliminated HTTP noise**: Restored httpx logging suppression for clean, professional output
- **Consistent multi-agent performance**: All agents now use reliable gpt-4o-mini provider
- **Production-ready presets**: Both debates and standup_club now deliver consistent, high-quality output

### 🔧 Technical Fixes
- **Provider optimization**: Replaced ollama_llama3 with openai_gpt4o_mini in debates.yaml and standup_club.yaml
- **Logging improvements**: HTTP request logs moved to WARNING level for cleaner user experience
- **Zero empty responses**: Eliminated blank outputs that were causing moderator STEP_BACK actions
- **Enhanced reliability**: Multi-agent scenarios now perform consistently without degradation

### 📊 Quality Improvements
- **Professional debates**: Well-structured arguments with real citations and balanced perspectives
- **High-quality comedy**: Creative, varied jokes without repetitive content
- **Active advisor feedback**: punch_up advisor now provides consistent, useful suggestions
- **Stable performance**: No more declining quality over multiple iterations

## [0.1.3] - 2025-01-27
### 🎨 User Experience Improvements
- **Cleaner output by default**: Disabled trace logging in all 10 presets for better first-time user experience
- **Enhanced README**: Added fun preset descriptions with emojis and personality
- **Strategic keywords**: Updated PyPI keywords with 20 targeted tags for better discoverability
- **Documentation fixes**: Replaced all placeholder environment variables with proper `--objective` parameter usage

### 🔧 Technical Improvements
- **Trace logging control**: All presets now have `trace: { enabled: false }` by default
- **Better discoverability**: Enhanced PyPI keywords covering multi-agent, LLM, research, experimentation
- **Consistent CLI usage**: All examples now use `--objective` parameter instead of environment variables
- **Professional appearance**: Cleaner output for production use while maintaining debugging capability

### 📚 Documentation Updates
- **README.md**: Added engaging preset descriptions right after main tagline
- **All preset files**: Cleaned objective definitions to use proper defaults instead of env var placeholders
- **PRESET_TIPS.md**: Updated to show proper CLI usage patterns
- **CLI.md**: Verified examples use correct parameter syntax

### 🎯 Impact
- **Better onboarding**: New users get clean, professional output immediately
- **Improved discoverability**: Enhanced PyPI search ranking and GitHub topic visibility
- **Consistent experience**: All documentation examples work out-of-the-box
- **Production ready**: Default settings optimized for real-world usage

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
