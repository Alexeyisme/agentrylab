# Persistence 📜💾

On‑disk formats used by Agentry Lab for transcripts and checkpoints. Minimal ceremony, maximum signal.

Overview ✨
- 📜 Transcripts: append‑only JSONL files per thread (experiment id).
- 💾 Checkpoints: a SQLite table storing a snapshot of runtime state per thread.

Transcript (JSONL) 🧾
- Location: `outputs/transcripts/<safe_thread_id>.jsonl` (by default)
- File per thread id; each line is a JSON object (an event).
- Event schema (keys):
  - `t` (float): Unix timestamp in seconds (UTC) when the event was recorded.
  - `iter` (int): 0‑based iteration index at the time of the node’s execution.
  - `agent_id` (str): Node id that produced the output (e.g., `pro`, `moderator`).
  - `role` (str): Logical role — one of `agent | moderator | summarizer | advisor`.
  - `content` (str | dict): Normalized node output.
    - Agents/Summarizer: usually a string.
    - Moderator: a dict matching the moderator schema (summary/drift/action/... ).
  - `metadata` (dict | null): Optional metadata attached by providers/tools (e.g., `citations`, `provider`, `model`).
  - `actions` (dict | null): Optional control actions (primarily from Moderator):
    - Keys: `type` (CONTINUE|STOP|STEP_BACK), `rollback` (int), `clear_summaries` (bool).
  - `latency_ms` (float, optional): Time to produce the node output.

Notes 📝
- The transcript is the canonical “what happened” log — append‑only, easy to read/stream.
- Event order is the order of execution. Use `iter` to group events produced in the same turn.

Checkpoint (SQLite) 🗄️
- Location: `outputs/checkpoints.db` (by default)
- Table: `checkpoints(thread_id TEXT PRIMARY KEY, payload BLOB, updated_at REAL)`
- Content: a serialized snapshot of `state.__dict__` when saved by the engine.
- Typical snapshot keys:
  - `thread_id` (str): The thread/experiment id.
  - `cfg` (object): The loaded preset/config object (opaque/complex).
  - `iter` (int): Current iteration counter.
  - `stop_flag` (bool): Stop signal seen by the engine.
  - `contracts` (object): Internal validators (opaque).
  - `history` (list[dict]): In‑memory context history `{agent_id, role, content}` used for prompt composition.
  - `running_summary` (str | null): Optional summarizer running summary (set only in specific paths).
  - `_tool_calls_run_total` (int): Total tool calls across the run.
  - `_tool_calls_iteration` (int): Tool calls in the current iteration.
  - `_tool_calls_run_by_id` (dict[str,int]): Per‑tool totals across the run.
  - `_tool_calls_iter_by_id` (dict[str,int]): Per‑tool counts in the current iteration.

Serialization details 📦
- Preferred snapshot is a shallow dict of state attributes. If that fails, the store falls back to pickling; in that case `load_checkpoint()` returns `{ "_pickled": <opaque> }`.
- The checkpoint is intended for operational state (counters/flags/quick status), not long‑term analytics. Prefer transcripts for auditing and reporting.

Cleaning 🧹
- Use `lab.clean(thread_id=None, delete_transcript=True, delete_checkpoint=True)` to remove persisted artifacts for a thread. When `thread_id` is omitted, the lab’s current thread id is used.
