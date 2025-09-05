Providers

This document describes the built‑in provider adapters and how to configure
them via presets, environment variables, and per‑call options.

OpenAI
- Adapter: `agentrylab.runtime.providers.openai.OpenAIProvider`
- Base URL:
  - Default: `https://api.openai.com/v1`
  - Override via env: `OPENAI_BASE_URL`
  - Or set `providers[].base_url` in the preset
- API key:
  - Provide `providers[].api_key` (recommended) or set the `Authorization`
    header via `providers[].headers`
- Common params:
  - `model` (required by OpenAI)
  - `temperature` (float)
  - Optional passthrough keys supported via `providers[].extra` (or per‑call kwargs):
    - `response_format`
    - `max_tokens`
    - `top_p`
    - `frequency_penalty`
    - `presence_penalty`
    - `stop` (string or array of strings)
  - Example preset snippet:
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

Per-call overrides (advanced)
- The OpenAI adapter accepts these keys per call as well. In code, you can
  override defaults by passing kwargs to `provider.chat(...)`:
```
provider.chat(messages, max_tokens=500, top_p=0.8, stop=["\n\n"]) 
```
- Nodes can forward such keys through their `llm_params` method. By default,
  nodes pass `temperature` only; extend `llm_params` in a custom node if you
  need per-node/turn overrides for other keys.

Ollama
- Adapter: `agentrylab.runtime.providers.ollama.OllamaProvider`
- Base URL:
  - Default: `http://localhost:11434`
  - Override via env: `OLLAMA_BASE_URL`
  - Or set `providers[].base_url` in the preset
- Common params:
  - `model` (e.g., `llama3:latest`)
  - `temperature`, `options` (e.g., `{num_ctx, top_p, seed}`)
- Streaming:
  - `stream_chat()` yields token deltas and a final content join; non‑streaming
    `chat()` returns the full content.

Messages and roles
- The provider base expects a list of `{role, content}` messages.
- When a tool result is appended, the ‘tool’ role is coerced to a plain user
  line in the OpenAI adapter (e.g., `TOOL: …`) since the minimal HTTP adapter
  does not implement the full function‑calling protocol.

Timeouts and retries
- All providers inherit defaults from the base: `timeout=60s`, `retries=1`,
  `backoff=0.2` (exponential). You can override in the preset or per call.

Notes
- The runtime normalizes provider responses to a simple dict with `content` and
  optional `metadata`. The original raw payload is also stored for debugging.
