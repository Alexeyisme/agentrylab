# Config

Budgets
- Per-run vs per-iteration: `per_run_*` limits apply across the entire thread/run; `per_iteration_*` limits apply per engine tick.
- Reset semantics: Per-iteration counters reset automatically at the start of every tick.
- Scope: Per-iteration limits are enforced per tool id and shared across all agents that run in the same tick. If multiple agents execute in a single tick, they share that tick's budget bucket for that tool id.
- Minima: `per_run_min` and `per_iteration_min` are advisory (not enforced at call time). Maxima are enforced before a tool call.

Engine behavior
- `runtime.stop_on_error: bool` (default: false)
  - When true, the engine stops the run after recording the first node error in a tick.
  - When false (default), errors are recorded in the transcript and the run continues.

Provider extras and per-call overrides (OpenAI)
- Set adapter defaults in the provider block using `extra:`.
- Example:
```
providers:
  - id: openai_gpt4o_mini
    impl: agentrylab.runtime.providers.openai.OpenAIProvider
    model: gpt-4o-mini
    api_key: ${OPENAI_API_KEY}
    extra:
      max_tokens: 300
      top_p: 0.9
      frequency_penalty: 0.0
      presence_penalty: 0.0
      stop: ["\n\n"]
```
- Per-call overrides (advanced):
  - The OpenAI adapter accepts these keys per call as well. Nodes can forward
    them via their `llm_params(...)` method. By default, nodes only pass
    `temperature`. If you need to override other keys per node/turn, extend the
    node’s `llm_params` to include the desired keys (e.g., `max_tokens`,
    `top_p`).
  - See `src/agentrylab/runtime/nodes/*` for examples.
