# ⚙️ Configuration Guide

**YAML-first presets. Define your lab, run your agents.**

## 🎯 Basic Structure

```yaml
version: "1.0.0"
id: my_lab
name: "My Awesome Lab"
description: "What this lab does"

objective: "Default topic for agents to discuss"

runtime:
  scheduler:
    impl: agentrylab.runtime.schedulers.round_robin.RoundRobinScheduler
    params:
      order: ["agent1", "agent2"]
  max_rounds: 10

providers:
  - id: openai
    impl: agentrylab.runtime.providers.openai.OpenAIProvider
    model: "gpt-4o-mini"
    api_key: ${OPENAI_API_KEY}

tools:
  - id: search
    impl: agentrylab.runtime.tools.ddg.DuckDuckGoSearchTool
    params:
      max_results: 5

agents:
  - id: agent1
    role: agent
    provider: openai
    tools: [search]
    system_prompt: "You are a helpful assistant."
```

## 🎭 Agent Roles

| Role | What It Does |
|------|-------------|
| `agent` | Regular speaking agent |
| `moderator` | Controls debate flow (JSON output) |
| `summarizer` | Wraps up conversations |
| `advisor` | Gives feedback to other agents |

## 🔄 Schedulers

**Round Robin** (default)
```yaml
scheduler:
  impl: agentrylab.runtime.schedulers.round_robin.RoundRobinScheduler
  params:
    order: ["agent1", "agent2", "agent3"]
```

**Every N**
```yaml
scheduler:
  impl: agentrylab.runtime.schedulers.every_n.EveryNScheduler
  params:
    schedule:
      agent1: 1
      agent2: 2  # runs every 2nd turn
      summarizer:
        every_n: 3
        run_on_last: true
```

## 🛠️ Tools & Budgets

**Basic Tool**
```yaml
tools:
  - id: search_ddg
    impl: agentrylab.runtime.tools.ddg.DuckDuckGoSearchTool
    params:
      max_results: 5
    budget:
      per_run_max: 10      # Total calls per run
      per_iteration_max: 2 # Calls per turn
```

**Tool Budgets**
- `per_run_max`: Total calls across entire experiment
- `per_iteration_max`: Calls per engine tick (resets each turn)
- `per_run_min` / `per_iteration_min`: Advisory minimums (not enforced)

## 📝 User Inputs (Optional)

Define dynamic parameters that users can provide:

```yaml
user_inputs:
  query:
    type: string
    description: "What are you looking for?"
    placeholder: "e.g., MacBook Pro M3"
    required: true
  location:
    type: string
    description: "Search location"
    placeholder: "e.g., Tel Aviv, Israel"
    required: true
  min_price:
    type: number
    description: "Minimum price"
    default: 0
    min: 0
  max_price:
    type: number
    description: "Maximum price"
    validate: "value >= min_price"
```

**Types**: `string`, `number`, `boolean`, `enum`
**Validation**: `min`, `max`, `choices`, `validate` (expression)
**Usage**: Reference with `${user_inputs.key}` in your config

## 🎛️ Provider Settings

**OpenAI Provider**
```yaml
providers:
  - id: openai
    impl: agentrylab.runtime.providers.openai.OpenAIProvider
    model: "gpt-4o-mini"
    api_key: ${OPENAI_API_KEY}
    extra:
      max_tokens: 300
      temperature: 0.7
      top_p: 0.9
```

**Ollama Provider**
```yaml
providers:
  - id: ollama
    impl: agentrylab.runtime.providers.ollama.OllamaProvider
    model: "llama3:latest"
    base_url: "http://localhost:11434"
    timeout: 30
```

## 🎯 Agent Configuration

```yaml
agents:
  - id: comedian
    role: agent
    provider: openai
    tools: [search]
    context:
      max_messages: 5
      pin_objective: true
      running_summary: false
    system_prompt: |
      You are a comedian. Be funny and creative.
      Always provide substantive responses - never leave empty.
```

## 🔧 Runtime Options

```yaml
runtime:
  max_rounds: 10
  stop_on_error: false  # Continue on errors (default)
  trace:
    enabled: false
  message_contract:
    require_metadata: false
  context_defaults:
    pin_objective: true
```

## 💾 Persistence

```yaml
persistence:
  checkpoints: [sqlite]
  transcript: [jsonl]

persistence_tools:
  sqlite:
    impl: LangGraphSqliteSaver
    params:
      db_path: "outputs/checkpoints.db"
  jsonl:
    impl: LangGraphJsonlSaver
    params:
      path: "outputs/transcripts"
```

## 🎨 Environment Variables

Use `${VAR_NAME}` syntax in YAML:

```yaml
providers:
  - id: openai
    api_key: ${OPENAI_API_KEY}
    model: ${MODEL_NAME:gpt-4o-mini}  # Default value
```

## 🧯 Common Patterns

**Tool Calling in Agents**
```yaml
system_prompt: |
  You have access to the search tool. Use it like this:
  ```json
  {"tool": "search_ddg", "args": {"query": "your search terms"}}
  ```
  Always use real tool results, never generate fake URLs.
```

**Human-in-the-Loop**
```yaml
agents:
  - id: user
    role: user  # Special role for human input
  - id: assistant
    role: agent
    # ... rest of config
```

**Error Handling**
```yaml
runtime:
  stop_on_error: false  # Continue on errors
  budgets:
    tools:
      per_run_max: 10   # Prevent runaway costs
```

## 🔁 Scheduling (optional)

Want to run presets on a schedule? Use external schedulers like cron, systemd timers, or cloud functions to call `agentrylab run` at your desired intervals.

---

**Ready to build your own lab? Start with a preset and customize! 🚀**