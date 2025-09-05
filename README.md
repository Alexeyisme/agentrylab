<p align="center">
  <a href="https://github.com/Alexeyisme/agentrylab/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Alexeyisme/agentrylab/actions/workflows/ci.yml/badge.svg" /></a>
  <a href="https://pypi.org/project/agentrylab/"><img alt="PyPI" src="https://img.shields.io/pypi/v/agentrylab.svg" /></a>
  <a href="https://codecov.io/gh/Alexeyisme/agentrylab"><img alt="Coverage" src="https://codecov.io/gh/Alexeyisme/agentrylab/branch/main/graph/badge.svg" /></a>
  <a href="https://pypi.org/project/agentrylab/"><img alt="License" src="https://img.shields.io/pypi/l/agentrylab.svg" /></a>
</p>

Agentry Lab — Multi‑Agent Orchestration for Experiments
Serious tooling, delightfully unserious outcomes. 😏

A lightweight, hackable lab for building and evaluating multi‑agent workflows.
Define your lab room (agents, tools, providers, schedules) in YAML, then run and
iterate quickly from the CLI or Python. Stream outputs, save transcripts, stash
checkpoints — because sometimes you want agents to argue… on purpose.

Highlights ✨
Because single agents are boring.
- 📦 YAML‑first presets for agents/advisors/moderator/summarizer (your config, your rules)
- 🔌 Pluggable LLM providers (OpenAI, Ollama) and tools (ddgs, Wolfram Alpha)
- 📡 Streaming CLI with resume support and transcript/DB persistence (forget nothing, replay everything)
- ⏳ Budgets for tools (per‑run/per‑iteration) with shared‑per‑tick semantics (no more runaway tool spam)
- 🧩 Small, readable runtime: nodes, scheduler, engine, state (batteries included, drama optional)

Requirements
- 🐍 Python 3.11+
- 🧰 A virtualenv (recommended; sanity‑preserving)
- 🖥️ Optional: Ollama for local models (default base URL `http://localhost:11434`)
- 🔑 API keys as needed (e.g., `OPENAI_API_KEY`, `WOLFRAM_APP_ID`) — bring your own secrets

Install (editable)
```
python -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e .
```

Environment (.env)
Create a `.env` file (loaded via `python-dotenv`) with any secrets:
```
OPENAI_API_KEY=sk-...
WOLFRAM_APP_ID=...
OLLAMA_BASE_URL=http://localhost:11434
```

Quickstart (CLI) 🚀
Spin up a room and let the sparks fly.
```
.venv/bin/agentrylab run src/agentrylab/presets/debates.yaml \
  --max-iters 4 --thread-id demo --show-last 10
```

Quickstart (Python API) 🐍
Orchestrate from Python with minimal fuss.
```python
from agentrylab import init
from agentrylab.presets import path as preset_path

lab = init(preset_path("debates.yaml"), experiment_id="demo")
lab.run(rounds=2)
```
See the “Python API” section below for full details and streaming options (callbacks, timeouts, early‑stops).
Output streams each iteration ("=== New events ===") and prints a final tail
of the last N transcript entries. Transcripts are written to `outputs/*.jsonl`
and checkpoints to `outputs/checkpoints.db`.

CLI
- Run a preset
  - `agentrylab run <preset.yaml> [--thread-id ID] [--max-iters N] [--stream/--no-stream] [--resume/--no-resume] [--show-last K]`
- Inspect a thread’s checkpoint
  - `agentrylab status <preset.yaml> <thread-id>`
 - List all known threads
   - `agentrylab ls <preset.yaml>`

See `src/agentrylab/docs/CLI.md` for full command docs.

Configuration ⚙️
Describe your room in YAML; everything else clicks into place.
- Presets live under `src/agentrylab/presets/` (see `debates.yaml`).
- Providers: OpenAI (HTTP), Ollama; add your own under `runtime/providers`.
- Tools: `ddgs` search, Wolfram Alpha; add your own under `runtime/tools`.
- Scheduler: Round‑robin and Every‑N; build your own in `runtime/scheduler`.

Presets 🎭
Have fun out of the box — llama3‑friendly and non‑strict by default.

- Stand‑Up Club (`standup_club.yaml`): two comedians riff on a topic, a punch‑up advisor adds tweaks, and the MC closes the set.
  - Seed a topic: `JOKE_TOPIC="airports"`
  - Cadence (Every‑N): `comicA`/`comicB` every turn, `punch_up` every 2, `mc` every 2 (run on last)
  - Run: `agentrylab run src/agentrylab/presets/standup_club.yaml --max-iters 6 --thread-id standup-1 --show-last 20`

- Drifty Thoughts (`drifty_thoughts.yaml`): three “thinkers” drift playfully; a gentle advisor nudges; optional summarizer digests.
  - Seed a topic: `TOPIC="surprising ideas"`
  - Cadence (Every‑N): thinkers every turn, advisor every 2, summarizer every 3 (run on last)
  - Tip: prompts avoid asking for user input; outputs are standalone prose

- Research Collaboration (`research.yaml`): two scientists brainstorm, a style coach gives clarity bullets, moderator emits JSON actions, summarizer keeps things readable.
  - Seed a topic: `TOPIC="curious scientific question"`
  - Cadence (Every‑N): scientists every turn; style_coach/moderator every 2; summarizer every 2 (run on last)
  - Tip: moderator includes a JSON exemplar to improve compliance; style coach gives ultra‑short bullets

- Therapy Session (`therapy_session.yaml`): a reflective client and gentle therapist; summarizer offers a compassionate wrap‑up.
  - Seed a topic: `TOPIC="something on your mind"`
  - Cadence (Every‑N): client/therapist every turn; summarizer every 2 (run on last)
  - Tip: therapist responds in 3–5 sentences and ends with one open question

- DDG Quick Summary (`ddg_quick_summary.yaml`): one agent searches DuckDuckGo and writes a 5‑bullet web summary with URLs.
  - Seed a topic: `SUMMARY_TOPIC="your topic"`
  - Cadence: single agent speaks once (tool call + summary)
  - Tip: good “starter” preset to test tools with llama3

- Small Talk (`small_talk.yaml`): two friendly voices chat; a host recaps every few turns.
  - Seed a topic: `SMALL_TALK_TOPIC="coffee rituals"`
  - Cadence (Every‑N): `pal`/`friend` every turn; `host` every 3 (run on last)
  - Tip: configured for `gpt‑4o‑mini` by default; swap provider to llama3 if you prefer local

- Brainstorm Buddies (`brainstorm_buddies.yaml`): two idea buddies riff; a scribe pulls a shortlist.
  - Seed a topic: `BRAINSTORM_TOPIC="rainy day activities"`
  - Cadence (Every‑N): `buddyA`/`buddyB` every turn; `scribe` every 3 (run on last)
  - Tip: buddies write short lines; scribe outputs a clean shortlist (no bullets)

- Follow‑Up Q&A (`follow_up.yaml`): explainer → interviewer → explainer → interviewer → summarizer.
  - Seed a topic: `FOLLOWUP_TOPIC="solar panels at home"`
  - Cadence (Round‑Robin, exact order): explainer → interviewer → explainer → interviewer → summarizer
  - Tip: simple 5‑turn Q&A flow with a tidy wrap‑up

See more tips: `src/agentrylab/docs/PRESET_TIPS.md`

Budgets (Tools)
- `per_run_max`: total calls per tool id across the run
- `per_iteration_max`: calls per engine tick (counters reset each tick)
- Scope: enforced per tool id, shared across agents that act in the same tick
- Minima (`per_run_min`, `per_iteration_min`) are advisory (not enforced);
  useful for prompting and analysis

Persistence 📜💾
Transcripts for storytelling; checkpoints for recovery.
- 📜 Transcript JSONL: default `outputs/<thread-id>.jsonl`
- 💾 Checkpoints (SQLite): default `outputs/checkpoints.db`
- ⏭️ Resume: `run --resume` (default) merges the saved snapshot into state before
  running; `--no-resume` starts fresh for that thread id.
- 🧠 Schemas and field definitions: see `src/agentrylab/docs/PERSISTENCE.md`
- ⏱️ Timekeeping: all timestamps are recorded as Unix epoch seconds (UTC)

Architecture (at a glance)
- Engine: steps the scheduler, executes nodes, applies outputs/actions
- Nodes: Agent, Moderator, Summarizer, Advisor (see `runtime/nodes/*`)
- Providers: thin HTTP adapters (OpenAI, Ollama)
- Tools: simple callables with normalized envelopes (e.g., ddgs)
- State: history window composition, budgets, message contracts, rollback

Development 🧑‍💻
Serious tooling for serious… tinkering.
```
pip install -e .[dev]

# lint and tests
ruff check . && pytest -q

# coverage (uses pytest-cov; default fail-under=40%)
make coverage            # or: pytest --cov=src/agentrylab --cov-branch --cov-report=term-missing
```
☕️ Pro tip: keep a coffee nearby. Agents love to riff.

Python API
- Initialize a lab and run for N rounds
  ```python
  from agentrylab import init, Event

  # When installed from PyPI, use the packaged preset path helper:
  # from agentrylab.presets import path as preset_path
  # lab = init(preset_path("debates.yaml"), experiment_id="unique_id_1234", prompt="What makes jokes funny?")
  # When working from a checkout, you can also reference the file under src/
  lab = init("src/agentrylab/presets/debates.yaml", experiment_id="unique_id_1234", prompt="What makes jokes funny?")
  status = lab.run(rounds=5)
  print(status.iter, status.is_active)
  print(lab.history(limit=10))
  ```
- One-shot run with optional streaming callback
  ```python
  from agentrylab import run

  def on_event(ev: dict):
      print(ev["iter"], ev["agent_id"], ev["role"])  # transcript events

  lab, status = run(
      "src/agentrylab/presets/debates.yaml",
      prompt="What makes jokes funny?",
      experiment_id="unique_id_1234",
      rounds=5,
      stream=True,
      on_event=on_event,
  )
  ```

Budgets (Python)
- Set global/per-tool budgets in the preset, then inspect counters via the checkpoint snapshot.
  ```python
  from agentrylab import init

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
  print("total tool calls:", snap.get("_tool_calls_run_total"))
  ```

Logging/Tracing from Python
- Configure runtime logging/trace in the preset and call via Python.
  ```python
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

API reference (Python)
- `init(config, *, experiment_id=None, prompt=None, user_messages=None, resume=True) -> Lab`
  - `config`: YAML path, dict, or a validated Preset object
  - `experiment_id`: logical run/thread id; enables resume
  - `prompt`: sets `cfg.objective` for the run (used in prompts when enabled)
  - `user_messages`: str or list[str]; seeds initial user message(s) into context
  - `resume`: attempts to load checkpoint for `experiment_id`

- `run(config, *, prompt=None, experiment_id=None, rounds=None, resume=True, stream=False, on_event=None, timeout_s=None, stop_when=None, on_tick=None, on_round=None) -> (Lab, LabStatus)`
  - One-shot helper; see `Lab.run` for params

- `Lab.run(*, rounds=None, stream=False, on_event=None, timeout_s=None, stop_when=None, on_tick=None, on_round=None) -> LabStatus`
  - `rounds`: number of iterations to run
  - `stream`: when True, calls `on_event(event: Event)` for newly appended transcript entries
  - `timeout_s`: optional wall-clock timeout for streaming runs
  - `stop_when`: optional predicate `Event -> bool`; when returns True, run stops

- `Lab.stream(*, rounds=None, timeout_s=None, stop_when=None, on_tick=None, on_round=None) -> Iterator[Event]`
  - Generator that yields transcript events as they occur
  - Optional callbacks: `on_tick(info)`, `on_round(info)` where `info = {"iter": int, "elapsed_s": float}`

- `Lab.status` (property) -> `LabStatus`
- `Lab.history(limit=50)` -> `list[Event]`
 - `Lab.clean(thread_id=None, delete_transcript=True, delete_checkpoint=True) -> None`: delete outputs for a thread
 - `list_threads(config) -> list[tuple[str, float]]`: list (thread_id, updated_at) in persistence

Releasing 📦
- We publish on tags via GitHub Actions (see `.github/workflows/release.yml`).
- Maintainers: bump `version` in `pyproject.toml`, update `CHANGELOG.md`, then:
  - `git tag -a vX.Y.Z -m 'vX.Y.Z' && git push --tags`
- CI builds sdist/wheel and uploads to PyPI using `PYPI_API_TOKEN` secret.

Event schema
```python
from agentrylab import Event

def handle(ev: Event) -> None:
    print(ev["iter"], ev["agent_id"], ev["role"], ev.get("latency_ms"))
    # keys: t, iter, agent_id, role, content (str|dict), metadata (dict|None), actions (dict|None), latency_ms
```

Checkpoint snapshot fields
- Returned by `lab.store.load_checkpoint(thread_id)` as a dict of state attributes (when available):
  - `thread_id`: current experiment id
  - `iter`: iteration counter
  - `stop_flag`: stop signal for the engine
  - `history`: in‑memory context entries `{agent_id, role, content}` used by prompt composition
  - `running_summary`: summarizer running summary if set
  - `_tool_calls_run_total`, `_tool_calls_iteration`: global tool counters
  - `_tool_calls_run_by_id`, `_tool_calls_iter_by_id`: per‑tool counters
  - `cfg`, `contracts`: complex/opaque objects (implementation detail)
  - If a legacy/opaque pickle was saved, you’ll get `{ "_pickled": ... }` instead

Recipes
- Programmatic preset construction
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

- Multiple runs in a loop
  ```python
  topics = ["jokes", "puns", "metaphors"]
  for i, topic in enumerate(topics):
      lab = init("src/agentrylab/presets/debates.yaml", experiment_id=f"exp-{i}", prompt=f"Explore {topic}")
      lab.run(rounds=2)
  ```

- Inspecting transcripts
  ```python
  lab = init("src/agentrylab/presets/debates.yaml", experiment_id="inspect-1")
  lab.run(rounds=1)
  for ev in lab.history(limit=20):
      print(ev["iter"], ev["agent_id"], ev["role"], str(ev["content"])[:80])
  # Or read directly from the store
  rows = lab.store.read_transcript("inspect-1", limit=100)
  ```

- Cleaning outputs (transcript + checkpoint)
  ```python
  from agentrylab import init
  lab = init("src/agentrylab/presets/debates.yaml", experiment_id="demo-clean")
  lab.run(rounds=1)
  # Remove persisted outputs for this experiment
  lab.clean()  # or lab.clean(thread_id="some-other-id")
  ```

License
MIT
