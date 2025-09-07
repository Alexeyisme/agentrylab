<p align="center">
  <a href="https://github.com/Alexeyisme/agentrylab/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Alexeyisme/agentrylab/actions/workflows/ci.yml/badge.svg" /></a>
  <a href="https://pypi.org/project/agentrylab/"><img alt="PyPI" src="https://img.shields.io/pypi/v/agentrylab.svg" /></a>
  <a href="https://pypi.org/project/agentrylab/"><img alt="License" src="https://img.shields.io/pypi/l/agentrylab.svg" /></a>
  <a href="https://pypi.org/project/agentrylab/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/agentrylab.svg" /></a>
</p>

## Agentry Lab — Multi‑Agent Orchestration Laboratory

**Agentry Lab lets you experiment with multi-agent scenarios in minutes!**

Define a room, drop in agents, give them instructions — then sit back and watch the sparks fly. Jump in yourself with interactive turns, or just let the lab run. Works equally well from the CLI or Python API.

```bash
pip install agentrylab
agentrylab run standup_club.yaml --objective "remote work" --max-iters 4
```

## 📋 Table of Contents

<details>
<summary>Click to expand</summary>

- [🚀 Get Started](#-get-started-in-2-minutes)
- [✨ Why AgentryLab?](#-why-agentrylab)
- [📋 Requirements](#-requirements)
- [💾 Installation](#-installation)
- [🔧 Environment Setup](#-environment-setup)
- [🎭 Built-in Presets](#-built-in-presets)
- [🖥️ CLI Commands](#️-cli-commands)
- [⚙️ Configuration](#️-configuration)
- [💰 Tool Budgets](#-tool-budgets)
- [📜💾 Persistence](#-persistence)
- [🏗️ Architecture](#️-architecture-at-a-glance)
- [🧑‍💻 Development](#-development)
- [🐍 Python API](#-python-api)
- [📦 Releasing](#-releasing)
- [📋 Event Schema](#-event-schema)
- [💾 Checkpoint Snapshot Fields](#-checkpoint-snapshot-fields)
- [🍳 Recipes](#-recipes)

</details>

## 🔗 Docs quick links

- CLI reference: `src/agentrylab/docs/CLI.md`
- Config guide: `src/agentrylab/docs/CONFIG.md`
- Providers: `src/agentrylab/docs/PROVIDERS.md`
- Tools: `src/agentrylab/docs/TOOLS.md`

## 🧠 Concepts in 30 seconds

- **Agents**: Roles that speak (pro, con, comedian, scientist, aliens — no limits!)
- **Providers**: LLM backends (OpenAI, Ollama supported)
- **Tools**: External calls wrapped as actions (DuckDuckGo, Wolfram included — contribute your own!)
- **Scheduler**: Who talks when (Round‑Robin, Every‑N — scheduling options available)
- **State**: History window, budgets, summaries, actions — continue experiments anytime

Pick preset lab setup or define your own lab (agents, tools, providers, schedules) in YAML, then run and iterate quickly from the CLI or Python. Stream outputs, save transcripts, stash checkpoints!

**10 preset lab environments - ready to have fun out of the box!** 🎭

*🎤 **Stand-Up Club** - Two comedians riff on any topic, MC closes the set*  
*🏛️ **Debates** - Pro/con arguments with evidence, moderator keeps it civil*  
*🧠 **Drifty Thoughts** - Three thinkers wander playfully through ideas*  
*🔬 **Research** - Scientists collaborate, style coach polishes the output*  
*🛋️ **Therapy Session** - Compassionate client-therapist conversations*  
*💡 **Brainstorm Buddies** - Idea generation with a scribe pulling shortlists*

Want a new preset or tool? We welcome contributions — start with a tiny PR or open an issue. See CONTRIBUTING.md. Your idea might ship in the next release.

## 🚀 Get Started in 2 Minutes

```bash
pip install agentrylab
```

### 🦙 **llama3-friendly lab presets:**
```bash
# Simple chat (works great with local Ollama!)
agentrylab run solo_chat_user.yaml --max-iters 3

# Quick web research
agentrylab run ddg_quick_summary.yaml --objective "quantum computing"
```

### 🤖 **OpenAI-friendly lab presets:**
```bash
# Formal debates with evidence
agentrylab run debates.yaml --objective "Should we colonize Mars?" --max-iters 4

# Comedy club (hybrid: llama3 + GPT-4o-mini)
agentrylab run standup_club.yaml --objective "remote work" --max-iters 6
```

## ✨ Why AgentryLab?

**Because single agents are boring.** 🤖

- 📦 **YAML‑first presets** for agents/advisors/moderator/summarizer (your config, your rules)
- 🔌 **Pluggable LLM providers** (OpenAI, Ollama) and tools (DuckDuckGo, Wolfram Alpha)
- 📡 **Streaming CLI** with resume support and transcript/DB persistence (forget nothing, replay everything)
- ⏳ **Smart budgets** for tools (per‑run/per‑iteration) with shared‑per‑tick semantics (no more runaway tool spam)
- 🧩 **Small, readable runtime**: nodes, scheduler, engine, state (batteries included, drama optional)
- 🫵 **Human‑in‑the‑loop turns**: schedule `user` nodes and poke runs from CLI/API (`agentrylab say …`)

## 📋 Requirements

- 🐍 **Python 3.11+**
- 🧰 **Virtual environment** (recommended; sanity‑preserving)
- 🖥️ **Optional: Ollama** for local models (default: `http://localhost:11434`)
- 🔑 **API keys** as needed (e.g., `OPENAI_API_KEY`, `WOLFRAM_APP_ID`) — bring your own secrets

## 💾 Installation

### Option 1: From PyPI (Recommended)
```bash
pip install agentrylab
```

### Option 2: From Source (Development)
```bash
git clone https://github.com/Alexeyisme/agentrylab.git
cd agentrylab
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .
```

## 🔧 Environment Setup

Create a `.env` file (loaded via `python-dotenv`) with any secrets you need:

```bash
# For OpenAI models (optional)
OPENAI_API_KEY=sk-...

# For Wolfram Alpha (optional)
WOLFRAM_APP_ID=...

# For Ollama (optional, defaults to localhost:11434)
OLLAMA_BASE_URL=http://localhost:11434
```

> **💡 Pro tip**: You can start with just Ollama (free, local) and add API keys later!

## 🚀 Quick Start

### CLI Quickstart
Spin up a room and let the sparks fly:

```bash
# Simple chat (works with Ollama/llama3)
agentrylab run solo_chat_user.yaml --max-iters 3

# Or with a custom topic
agentrylab run standup_club.yaml --objective "remote work" --max-iters 4

# Or a debate (needs OpenAI API key)
agentrylab run debates.yaml --max-iters 4 --thread-id demo
```

> Cleanup outputs fast when experimenting:
> ```bash
> rm -rf outputs/  # transcripts + checkpoints
> ```

### CLI Cheat‑Sheet

```
--objective TEXT   # Set topic on the fly
--thread-id ID     # Name your run (enables resume)
--max-iters N      # Number of iterations
--no-resume        # Start fresh even if checkpoint exists
--no-stream        # Print only final tail
--show-last K      # Tail size at the end
```

Set a custom objective/topic at runtime:

```bash
agentrylab run debates.yaml --thread-id debate1 --objective "Proposition: apples — good or scam?" --max-iters 4
```

Interactive mode (prompt for user message each round when a user node exists):

```bash
# Solo chat with a scheduled user turn; prompt on each iteration
agentrylab run solo_chat_user.yaml --thread-id demo --resume --max-iters 3 --interactive --user-id user
```

Check version:

```bash
agentrylab --version
```

### User Messages (User-in-the-Loop)
Let a human chime in via API or CLI, and optionally schedule a user turn in cadence.

```bash
# 1) Post a user message into a thread
agentrylab say solo_chat_user.yaml demo 'Hello from Alice!'

# 2) Run one iteration to consume it (user turn then assistant)
agentrylab run solo_chat_user.yaml --thread-id demo --resume --max-iters 1
```

Python API:
```python
from agentrylab import init

lab = init("src/agentrylab/presets/solo_chat_user.yaml", experiment_id="demo")
lab.post_user_message("Hello from Alice!", user_id="user:alice")
lab.run(rounds=1)
```

### Python API Quickstart
Orchestrate from Python with minimal fuss:

```python
from agentrylab import init, list_threads

# 1. Create lab (using solo_chat_user preset - perfect for llama3!)
lab = init("src/agentrylab/presets/solo_chat_user.yaml", 
           experiment_id="my-chat",
           prompt="Tell me about your favorite hobby!")

# 2. Run with callback
def callback(event):
    if event.get("event") == "provider_result":
        print(f"Agent responded: {event.get('content_len', 0)} chars")

status = lab.run(rounds=3, stream=True, on_event=callback)

# 3. Show conversation
for msg in lab.state.history:
    print(f"[{msg['role']}]: {msg['content']}")

# 4. Resume with new topic
lab.state.objective = "Now tell me about your dream vacation!"
lab.run(rounds=2)

# 5. List threads
threads = list_threads("src/agentrylab/presets/solo_chat_user.yaml")
```

Python examples:
- `user_in_the_loop_quick.py` — post once and run N rounds
- `user_in_the_loop_interactive.py` — type a line, run a round, repeat

> **📝 Note**: Output streams each iteration ("=== New events ===") and prints a final tail
> of the last N transcript entries. Transcripts are written to `outputs/*.jsonl`
> and checkpoints to `outputs/checkpoints.db`.

## 🖥️ CLI Commands

### Basic Commands
```bash
# Run a preset
agentrylab run <preset.yaml> [--thread-id ID] [--max-iters N] [--show-last K] [--objective TEXT]

# Inspect a thread's checkpoint
agentrylab status <preset.yaml> <thread-id>

# List all known threads
agentrylab ls <preset.yaml>
```

### Common Options
- `--max-iters N`: Run for N iterations (default: varies by preset)
- `--thread-id ID`: Use specific thread ID (enables resume)
- `--show-last K`: Show last K messages at the end
- `--stream/--no-stream`: Enable/disable real-time streaming (default: enabled)
- `--resume/--no-resume`: Resume from checkpoint or start fresh (default: resume)
- `--objective TEXT`: Override the preset `objective` (topic) just for this run

> **📚 Full docs**: See `src/agentrylab/docs/CLI.md` for complete command reference.

User-in-the-loop:
- `agentrylab say <preset.yaml> <thread-id> 'message' [--user-id USER]` appends a user message into a thread.
- Works with scheduled user nodes (role `user`) so messages are consumed on their turns.

## ⚙️ Configuration

Describe your room in YAML; everything else clicks into place.

- **Presets**: shipped with the package; the CLI accepts packaged names like `solo_chat_user.yaml` (file paths work too)
- **Providers**: OpenAI (HTTP), Ollama; add your own under `runtime/providers`
- **Tools**: DuckDuckGo search, Wolfram Alpha; add your own under `runtime/tools`
- **Scheduler**: Round‑robin and Every‑N; build your own in `runtime/scheduler`

## 🎭 Built-in Presets

Have fun out of the box — **llama3‑friendly** and non‑strict by default.

### 📊 Quick Overview

| Preset | Description | Best For | Provider | OpenAI? |
|--------|-------------|----------|----------|--------|
| [Solo Chat](#-solo-chat-user-turn-solo_chat_useryaml---perfect-for-beginners) | Single friendly agent with user turns | Testing, beginners | llama3 | ❌ |
| [Stand‑Up Club](#-stand-up-club-standup_clubyaml---comedy-gold) | Two comedians + MC | Humor, creative writing | Hybrid | ⚠️ |
| [Debates](#-debates-debatesyaml---formal-arguments) | Pro/con + moderator, evidence | Structured arguments | OpenAI | ✅ |
| [Drifty Thoughts](#-drifty-thoughts-drifty_thoughtsyaml---free-form-thinking) | Three playful thinkers | Brainstorming | OpenAI | ✅ |
| [Research](#-research-collaboration-researchyaml---academic-vibes) | Scientists + style coach | Academic, structured | OpenAI | ✅ |
| [Therapy Session](#️-therapy-session-therapy_sessionyaml---compassionate-chat) | Client–therapist chat | Supportive conversations | OpenAI | ✅ |
| [DDG Quick Summary](#-ddg-quick-summary-ddg_quick_summaryyaml---web-research) | Web search + summary | Quick research | llama3 | ❌ |
| [Small Talk](#-small-talk-small_talkyaml---casual-chat) | Two voices + host | Casual chats | llama3 | ❌ |
| [Brainstorm Buddies](#-brainstorm-buddies-brainstorm_buddiesyaml---idea-generation) | Idea gen + scribe | Creative ideation | OpenAI | ✅ |
| [Simple Argument](#-simple-argument-argueyaml---casual-debates) | Casual debate, no rules | Opinions | Hybrid | ⚠️ |

### 🎤 **Solo Chat (User Turn)** (`solo_chat_user.yaml`) - **Perfect for beginners!**
- **What**: Single friendly agent with scheduled user turns
- **Best for**: Testing, simple conversations, llama3 users, human-in-the-loop
- **Run**: `agentrylab run solo_chat_user.yaml --max-iters 3`
- **Topic**: `--objective "your topic"`

### 🎭 **Stand‑Up Club** (`standup_club.yaml`) - **Comedy gold!**
- **What**: Two comedians riff on a topic, punch‑up advisor adds tweaks, MC closes the set
- **Best for**: Entertainment, creative writing, humor
- **Run**: `agentrylab run standup_club.yaml --objective "airports" --max-iters 6`
- **Topic**: `--objective "your topic"`

### 🧠 **Drifty Thoughts** (`drifty_thoughts.yaml`) - **Free-form thinking**
- **What**: Three "thinkers" drift playfully; gentle advisor nudges; optional summarizer
- **Best for**: Creative brainstorming, philosophical discussions
- **Run**: `agentrylab run drifty_thoughts.yaml --objective "surprising ideas"`
- **Topic**: `--objective "your topic"`

### 🔬 **Research Collaboration** (`research.yaml`) - **Academic vibes**
- **What**: Two scientists brainstorm, style coach gives clarity, summarizer wraps up
- **Best for**: Research, academic discussions, structured thinking
- **Run**: `agentrylab run research.yaml --objective "curious scientific question"`
- **Topic**: `--objective "your topic"`

### 🛋️ **Therapy Session** (`therapy_session.yaml`) - **Compassionate chat**
- **What**: Reflective client and gentle therapist; summarizer offers compassionate wrap‑up
- **Best for**: Emotional discussions, self-reflection, supportive conversations
- **Run**: `agentrylab run therapy_session.yaml --objective "something on your mind"`
- **Topic**: `--objective "your topic"`

### 🔍 **DDG Quick Summary** (`ddg_quick_summary.yaml`) - **Web research**
- **What**: One agent searches DuckDuckGo and writes a 5‑bullet web summary with URLs
- **Best for**: Quick research, web summaries, fact-finding
- **Run**: `agentrylab run ddg_quick_summary.yaml --objective "your topic"`
- **Topic**: `--objective "your topic"`

### ☕ **Small Talk** (`small_talk.yaml`) - **Casual chat**
- **What**: Two friendly voices chat; host recaps every few turns
- **Best for**: Casual conversations, social interactions
- **Run**: `agentrylab run small_talk.yaml --objective "coffee rituals"`
- **Topic**: `--objective "your topic"`

### 💡 **Brainstorm Buddies** (`brainstorm_buddies.yaml`) - **Idea generation**
- **What**: Two idea buddies riff; scribe pulls a shortlist
- **Best for**: Brainstorming, creative ideation, problem-solving
- **Run**: `agentrylab run brainstorm_buddies.yaml --objective "rainy day activities"`
- **Topic**: `--objective "your topic"`

### 🏛️ **Debates** (`debates.yaml`) - **Formal arguments**
- **What**: Pro/con debaters with moderator and evidence-based arguments
- **Best for**: Formal debates, argument analysis, structured discussions
- **Run**: `agentrylab run debates.yaml --max-iters 4`
- **Note**: Requires OpenAI API key for best results

### 🗣️ **Simple Argument** (`argue.yaml`) - **Casual debates**
- **What**: Two agents having a natural debate without strict rules
- **Best for**: Casual arguments, opinion discussions
- **Run**: `agentrylab run argue.yaml --objective "Should remote work become standard?"`
- **Topic**: `--objective "your topic"`

> **💡 Pro tip**: Start with **Solo Chat (User Turn)** for testing, then try **Stand‑Up Club** for fun!  
> **📚 More tips**: See `src/agentrylab/docs/PRESET_TIPS.md` for advanced configuration.

## 💰 Tool Budgets

Control how many times tools can be called to prevent runaway costs:

- **`per_run_max`**: Total calls per tool across the entire run
- **`per_iteration_max`**: Calls per engine tick (resets each tick)
- **Scope**: Enforced per tool ID, shared across agents in the same tick
- **Minima** (`per_run_min`, `per_iteration_min`) are advisory (not enforced)

## 📜💾 Persistence

**Transcripts for storytelling; checkpoints for recovery.**

- **📜 Transcript JSONL**: `outputs/<thread-id>.jsonl` (human-readable conversation logs)
- **💾 Checkpoints (SQLite)**: `outputs/checkpoints.db` (resume from any point)
- **⏭️ Resume**: `--resume` (default) continues from last checkpoint; `--no-resume` starts fresh
- **🧠 Schemas**: See `src/agentrylab/docs/PERSISTENCE.md` for detailed field definitions
- **⏱️ Timestamps**: All recorded as Unix epoch seconds (UTC)

### Cleaning outputs (all threads)
- Remove everything (default paths): `rm -rf outputs/`
- Or per-thread: `agentrylab ls <preset.yaml>` then `agentrylab reset <preset.yaml> <thread-id> --delete-transcript`

## 🏗️ Architecture (at a glance)

**Simple, readable runtime components:**

- **Engine**: Steps the scheduler, executes nodes, applies outputs/actions
- **Nodes**: Agent, Moderator, Summarizer, Advisor (see `runtime/nodes/*`)
- **Providers**: Thin HTTP adapters (OpenAI, Ollama)
- **Tools**: Simple callables with normalized envelopes (e.g., DuckDuckGo)
- **State**: History window composition, budgets, message contracts, rollback

## 🧑‍💻 Development

**Serious tooling for serious… tinkering.**

```bash
# Install development dependencies
pip install -e .[dev]

# Lint and test
ruff check . && pytest -q

# Coverage (uses pytest-cov; default fail-under=40%)
make coverage
# or: pytest --cov=src/agentrylab --cov-branch --cov-report=term-missing
```

> **☕️ Pro tip**: Keep a coffee nearby. Agents love to riff.

## 🐍 Python API

### 🚀 Beginner API

**Essential functions for getting started quickly:**
```python
from agentrylab import init

# Initialize a lab and run for N rounds
lab = init("src/agentrylab/presets/solo_chat_user.yaml", 
           experiment_id="my-experiment", 
           prompt="Tell me about your favorite hobby!")
status = lab.run(rounds=5)
print(f"Iterations: {status.iter}, Active: {status.is_active}")

# View conversation history
for msg in lab.state.history:
    print(f"[{msg['role']}]: {msg['content']}")
```

### 🔧 Advanced API

**Power user features for complex workflows:**

#### Posting User Messages
```python
from agentrylab import init

lab = init("src/agentrylab/presets/solo_chat_user.yaml", experiment_id="chat-1")
# Append a user line into history and transcript; also enqueue for scheduled user nodes
lab.post_user_message("Please keep it concise.", user_id="user:alice")
lab.run(rounds=1)
```

#### One-shot Run with Streaming
```python
from agentrylab import run

def on_event(ev: dict):
    print(f"Iteration {ev['iter']}: {ev['agent_id']} ({ev['role']})")

lab, status = run(
    "src/agentrylab/presets/solo_chat_user.yaml",
    prompt="What makes jokes funny?",
    experiment_id="streaming-demo",
    rounds=5,
    stream=True,
    on_event=on_event,
)
```

#### Budget Management
```python
from agentrylab import init

# Set budgets in preset, then inspect counters
preset = {
    "id": "budget-demo",
    "providers": [{"id": "p1", "impl": "tests.fake_impls.TestProvider", "model": "test"}],
    "tools": [{"id": "echo", "impl": "tests.fake_impls.EchoTool"}],
    "agents": [{"id": "pro", "role": "agent", "provider": "p1", "system_prompt": "You are the agent.", "tools": ["echo"]}],
    "runtime": {
        "scheduler": {"impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler", "params": {"order": ["pro"]}},
        "budgets": {"tools": {"per_run_max": 1}},
    },
}
lab = init(preset, experiment_id="budget-demo-1", resume=False)
lab.run(rounds=1)
snap = lab.store.load_checkpoint("budget-demo-1")
print("Total tool calls:", snap.get("_tool_calls_run_total"))
```

#### Logging & Tracing
```python
# Configure runtime logging/trace in the preset
preset = {
    # ... providers/tools/agents ...
    "runtime": {
        "logs": {"level": "INFO", "format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
        "trace": {"enabled": True},
        "scheduler": {"impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler", "params": {"order": ["pro"]}},
    },
}
lab = init(preset, experiment_id="log-1")
lab.run(rounds=1)
```

## ❓ FAQ

- **Do I need OpenAI?** No. Many presets run great on llama3 via Ollama.
- **Where are outputs stored?** `outputs/*.jsonl` (transcripts), `outputs/checkpoints.db` (state).
- **How do I resume?** Use `--thread-id` and keep `--resume` (default).
- **How do I set a topic?** `--objective "..."` on the CLI or `prompt="..."` in Python.

## 🧯 Troubleshooting

- **Empty replies with llama3**: set provider timeout to 30s; add “never leave empty” lines to system prompts; for strict multi‑agent tasks, prefer `gpt-4o-mini`.
- **Moderator JSON errors**: use `debates.yaml` (OpenAI) or remove moderator; see `runtime/nodes/moderator.py` for JSON contract.

## 🗺️ Roadmap

- Tool sandboxing + more built‑in tools
- More providers and local models
- Preset sharing/marketplace
- Richer moderation contracts and guardrails

## 📚 API Reference

### Core Functions

**`init(config, *, experiment_id=None, prompt=None, user_messages=None, resume=True) -> Lab`**
- `config`: YAML path, dict, or validated Preset object
- `experiment_id`: Logical run/thread ID; enables resume
- `prompt`: Sets `cfg.objective` for the run (used in prompts when enabled)
- `user_messages`: String or list of strings; seeds initial user message(s) into context
- `resume`: Attempts to load checkpoint for `experiment_id`

**`run(config, *, prompt=None, experiment_id=None, rounds=None, resume=True, stream=False, on_event=None, timeout_s=None, stop_when=None, on_tick=None, on_round=None) -> (Lab, LabStatus)`**
- One-shot helper; see `Lab.run` for parameters

### Lab Methods

**`Lab.run(*, rounds=None, stream=False, on_event=None, timeout_s=None, stop_when=None, on_tick=None, on_round=None) -> LabStatus`**
- `rounds`: Number of iterations to run
- `stream`: When True, calls `on_event(event: Event)` for newly appended transcript entries
- `timeout_s`: Optional wall-clock timeout for streaming runs
- `stop_when`: Optional predicate `Event -> bool`; when returns True, run stops

**`Lab.stream(*, rounds=None, timeout_s=None, stop_when=None, on_tick=None, on_round=None) -> Iterator[Event]`**
- Generator that yields transcript events as they occur
- Optional callbacks: `on_tick(info)`, `on_round(info)` where `info = {"iter": int, "elapsed_s": float}`

**Other Lab Methods:**
- `Lab.status` (property) -> `LabStatus`
- `Lab.history(limit=50)` -> `list[Event]`
- `Lab.clean(thread_id=None, delete_transcript=True, delete_checkpoint=True) -> None`: Delete outputs for a thread
- `list_threads(config) -> list[tuple[str, float]]`: List (thread_id, updated_at) in persistence

## 📦 Releasing

We publish on tags via GitHub Actions (see `.github/workflows/release.yml`).

**For maintainers:**
1. Bump `version` in `pyproject.toml`
2. Update `CHANGELOG.md`
3. `git tag -a vX.Y.Z -m 'vX.Y.Z' && git push --tags`
4. CI builds sdist/wheel and uploads to PyPI using `PYPI_API_TOKEN` secret

## 📋 Event Schema

```python
from agentrylab import Event

def handle(ev: Event) -> None:
    print(ev["iter"], ev["agent_id"], ev["role"], ev.get("latency_ms"))
    # Keys: t, iter, agent_id, role, content (str|dict), metadata (dict|None), actions (dict|None), latency_ms
```

## 💾 Checkpoint Snapshot Fields

Returned by `lab.store.load_checkpoint(thread_id)` as a dict of state attributes:

- **`thread_id`**: Current experiment ID
- **`iter`**: Iteration counter
- **`stop_flag`**: Stop signal for the engine
- **`history`**: In‑memory context entries `{agent_id, role, content}` used by prompt composition
- **`running_summary`**: Summarizer running summary if set
- **`_tool_calls_run_total`, `_tool_calls_iteration`**: Global tool counters
- **`_tool_calls_run_by_id`, `_tool_calls_iter_by_id`**: Per‑tool counters
- **`cfg`, `contracts`**: Complex/opaque objects (implementation detail)

> **Note**: If a legacy/opaque pickle was saved, you'll get `{ "_pickled": ... }` instead

## 🍳 Recipes

### Programmatic Preset Construction
```python
from agentrylab import init

preset = {
    "id": "programmatic",
    "providers": [{"id": "p1", "impl": "agentrylab.runtime.providers.openai.OpenAIProvider", "model": "gpt-4o"}],
    "tools": [],
    "agents": [{"id": "pro", "role": "agent", "provider": "p1", "system_prompt": "You are the agent."}],
    "runtime": {
        "scheduler": {"impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler", "params": {"order": ["pro"]}}
    },
}
lab = init(preset, experiment_id="prog-1", user_messages=["Start topic: ..."]) 
lab.run(rounds=3)
```

### Multiple Runs in a Loop
```python
topics = ["jokes", "puns", "metaphors"]
for i, topic in enumerate(topics):
    lab = init("src/agentrylab/presets/debates.yaml", experiment_id=f"exp-{i}", prompt=f"Explore {topic}")
    lab.run(rounds=2)
```

### Inspecting Transcripts
```python
lab = init("src/agentrylab/presets/debates.yaml", experiment_id="inspect-1")
lab.run(rounds=1)
for ev in lab.history(limit=20):
    print(ev["iter"], ev["agent_id"], ev["role"], str(ev["content"])[:80])

# Or read directly from the store
rows = lab.store.read_transcript("inspect-1", limit=100)
```

### Cleaning Outputs (Transcript + Checkpoint)
```python
from agentrylab import init
lab = init("src/agentrylab/presets/debates.yaml", experiment_id="demo-clean")
lab.run(rounds=1)
# Remove persisted outputs for this experiment
lab.clean()  # or lab.clean(thread_id="some-other-id")
```

---

## 📄 License

MIT