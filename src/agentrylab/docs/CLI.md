# Agentry Lab CLI 🚀

The CLI is a thin wrapper over the runtime: load a preset, spin up providers/tools/nodes,
and run the engine for a specified number of ticks. Minimal ceremony, maximum signal.

Commands 🧭
- run: start or continue a thread
  - Usage: `agentrylab run <preset.yaml> [options]`
- status: inspect a thread’s latest checkpoint
  - Usage: `agentrylab status <preset.yaml> <thread-id>`
- validate: lint a preset file and print advisory warnings
  - Usage: `agentrylab validate <preset.yaml>`
- say: append a user message into a thread (user-in-the-loop)
  - Usage: `agentrylab say <preset.yaml> <thread-id> "message" [--user-id USER]`
  - Example: `agentrylab say src/agentrylab/presets/user_in_the_loop.yaml demo "Hello agents!"`
 - ls: list known threads (from the checkpoint store)
   - Usage: `agentrylab ls <preset.yaml>`
 - reset: delete checkpoint (and optionally transcript) for a thread
   - Usage: `agentrylab reset <preset.yaml> <thread-id> [--delete-transcript]`

Run options ⚙️
- --max-iters INT: Number of engine ticks to execute (default: 8)
- --thread-id TEXT: Logical thread/run id (used for transcript and checkpoints)
- --show-last INT: Print the last N transcript events at the end (default: 10)
- --stream / --no-stream: Print new events after each iteration (default: --stream)
- --resume / --no-resume: Load saved state for the thread before running (default: --resume)
- --objective TEXT: Override the preset objective/topic just for this run

Examples 💡
- First run with a new thread id
  - `agentrylab run src/agentrylab/presets/debates.yaml --max-iters 4 --thread-id demo --show-last 10`
- Override objective/topic at runtime
  - `agentrylab run src/agentrylab/presets/debates.yaml --thread-id apples --objective "Proposition: apples — good or scam?" --max-iters 4`
- Continue (resume) the same thread
  - `agentrylab run src/agentrylab/presets/debates.yaml --max-iters 2 --thread-id demo`
- Run without resuming (fresh state) even if a checkpoint exists
  - `agentrylab run src/agentrylab/presets/debates.yaml --max-iters 1 --thread-id demo --no-resume`
- Inspect checkpoint status
  - `agentrylab status src/agentrylab/presets/debates.yaml demo`
- Post a user message and run one tick
  - `agentrylab say src/agentrylab/presets/user_in_the_loop.yaml demo "Hi team!"`
  - `agentrylab run src/agentrylab/presets/user_in_the_loop.yaml --thread-id demo --resume --max-iters 1`

Environment and .env 🔑
- The CLI loads environment variables from `.env` (if present) via `python-dotenv`
  without overriding existing process variables.
- Common variables used by presets:
  - `OPENAI_API_KEY`: for OpenAI providers
  - `WOLFRAM_APP_ID`: for the Wolfram Alpha tool
  - `OLLAMA_BASE_URL`: for Ollama (default is `http://localhost:11434`)

Streaming output 📡
- With `--stream` (default), the CLI prints a “=== New events ===” block after
  each iteration and shows the role, agent id, and either content or error for
  each event.
- At the end, it prints a “=== Last messages ===” tail of the last N transcript
  entries (successes and errors).

Persistence 📜💾
- Transcript: newline-delimited JSON written to `outputs/<thread-id>.jsonl`
  (path is configurable via the preset; default is `outputs/`).
- Checkpoints: per-thread state snapshots stored in `outputs/checkpoints.db`
  (SQLite).
  - The engine saves a snapshot after each tick.
  - With `--resume` (default), the CLI merges any saved snapshot into the
    in-memory state before running (best-effort; only dict snapshots are merged).

Clean all outputs 🧹
- Quick way: delete the outputs root (default location):
  - `rm -rf outputs/`  (this removes all transcripts and the checkpoints DB)
- Per-thread loop (safer): reset each listed thread and delete transcripts:
  - `for tid in $(agentrylab ls src/agentrylab/presets/solo_chat.yaml | awk '{print $1}'); do agentrylab reset src/agentrylab/presets/solo_chat.yaml "$tid" --delete-transcript; done`
  - Replace the preset path with the one you’re using; `ls` reads from the checkpoint DB to enumerate threads.

What to expect in transcript JSONL 🧾
- Each line is a JSON object with fields like:
  - `t`: timestamp (seconds since epoch)
  - `iter`: engine iteration index (0-based)
  - `agent_id`: node id (pro, con, moderator, summarizer, etc.)
  - `role`: agent | advisor | moderator | summarizer
  - `content`: text (agents/summarizer) or JSON (moderator) when successful
  - `metadata`: may include `citations` (URLs), etc.
  - `actions`: control signals (primarily from Moderator)
  - `error`: present when a node raised an error (e.g., non-JSON moderator output)
  - `latency_ms`: execution time for the node call

Budgets (tools) ⏳
- Per-run vs per-iteration:
  - `per_run_max` caps the total calls to a tool id across the entire thread.
  - `per_iteration_max` caps calls per engine tick; counters reset automatically
    at the start of each tick.
- Scope: Limits are enforced per tool id and shared across all agents that
  execute within the same tick.
- Minima: `per_run_min` and `per_iteration_min` are advisory (not enforced at
  call time) and can be used for prompting or analysis.

Exit codes / errors 🧯
- If provider calls fail (e.g., missing API key), the CLI continues and records
  the error into the transcript. The process still exits with success unless an
  internal error occurs during CLI setup.

Tips ☕️
- Use unique `--thread-id` per run to keep transcripts and checkpoints separate.
- Prefer `--no-resume` if you need a clean slate for a thread id that already
  exists in the DB.
- For deep debugging, set the log level in the preset:
  - `runtime.logs.level: DEBUG`
  This enables additional logs such as provider result sizes and budget checks.
Preset lint 🧹
- The CLI lints presets on `run` and via `agentrylab validate`, surfacing:
  - Unknown/missing roles under `agents: [ ... ]`
  - Duplicated `moderator`/`summarizer` defined both top‑level and under `agents`
  - Presence of top‑level `message_contract` (ignored by the runtime) when
    `runtime.message_contract` is missing
- Loader normalization logs these messages at INFO by default; you can set a
  stricter mode by adding `runtime.lint_strict: true` in your preset to elevate
  them to WARNING.
