Preset Tips 🧩

Quick guidelines for making fun, llama3‑friendly presets that behave well.

Environment Seeding 🔑
- Seed a topic via env vars and pin it into the context as a user message:
  - YAML: `objective: ${TOPIC:Your default here}` (or `JOKE_TOPIC` for stand‑up)
  - Runtime: set `runtime.context_defaults.pin_objective: true`
  - CLI: `TOPIC="pizza" agentrylab run your.yaml ...`
  - Python: `os.environ["TOPIC"] = "pizza"`

Cadence (Schedulers) ⏱️
- Round‑Robin: fixed order each tick (simple and predictable)
  - YAML: `runtime.scheduler.impl: ...round_robin.RoundRobinScheduler`
  - `params.order: [agent1, agent2, moderator, summarizer]`
- Every‑N: flexible cadence per node (great for “advisors every 2”, “summarizer every 3”)
  - YAML: `runtime.scheduler.impl: ...every_n.EveryNScheduler`
  - `params.schedule: { agent1: 1, advisor: 2, summarizer: { every_n: 3, run_on_last: true } }`
- Tips:
  - Put summarizers on `run_on_last: true` to always get a final wrap‑up
  - Advisors are non‑blocking and can run less frequently

Prompt Patterns ✍️
- Agents (comic/storyteller/thinker)
  - Write standalone content (avoid “please type/answer”)
  - Keep it short and punchy (e.g., 2–4 lines), or set an upper bound via prompt
- Advisors (style coach, punch‑up)
  - Non‑blocking, concise: e.g., “Return 2–3 bullets, each <10–12 words”
  - Avoid meta comments or audience prompts
- Moderators (when strict JSON is required)
  - Include an explicit JSON schema and a one‑screen exemplar
  - Add “Respond ONLY with JSON. No prose, no code fences.”
- Summarizers
  - “3–5 sentences” works well; forbid bullets/requests
  - Use a `max_summary_chars` cap to keep it readable (e.g., 400–600)

Llama3 Provider Settings ⚙️
- Model: `llama3:latest` via Ollama
- Base URL: `http://localhost:11434`
- Timeout: 8s is a good starting point for local latency

Common Tweaks 🔧
- Reduce empty outputs: nudge prompts (“Response must not be empty”), or increase timeout
- Cut long turns: add summarizer cadence and `max_summary_chars`
- Encourage tool usage (if enabled): mention it in agent prompts (“Consider a quick web search for facts.”)
- Tone control: add one‑sentence style constraints (“avoid references/requests”, “use a fresh metaphor each turn”)

Examples 📦
- Stand‑Up Club: comedians every turn; punch‑up advisor every 2; MC (summarizer) every 2 & on last
- Drifty Thoughts: three thinkers every turn; gentle advisor every 2; summarizer every 3 & on last
- Research Collaboration: two scientists every turn; style coach/moderator every 2; summarizer every 2 & on last (moderator uses JSON exemplar)

