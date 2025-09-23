# 🏗️ AgentryLab Architecture

**Simple, readable runtime that orchestrates agents, tools, and conversations.**

## 🎯 Overview

**YAML → Runtime → Magic**

```
Preset (YAML) → Loader → Runtime → Engine → State → Persistence
     ↓              ↓        ↓        ↓       ↓        ↓
   Agents        Validate  Build   Execute  Track   Save
   Tools         Normalize  Nodes   Scheduler Memory Results
   Providers     Env Vars   Tools   Actions  Budgets
```

## 🧩 Core Components

### 📋 **Preset (YAML)**
Declarative configuration for your lab:
- **Agents**: Roles that speak (comedian, scientist, debater)
- **Tools**: Real integrations (search, marketplace, APIs)
- **Providers**: LLM backends (OpenAI, Ollama)
- **Scheduler**: Who talks when
- **Runtime**: Budgets, persistence, behavior

### ⚙️ **Loader**
Validates and normalizes YAML into runtime models:
- **Environment interpolation**: `${OPENAI_API_KEY}`
- **Pydantic validation**: Catches errors early
- **Normalization**: Consistent structure

### 🏃 **Runtime**
The execution engine:

**Providers** - LLM adapters
```python
OpenAIProvider(model="gpt-4o-mini", api_key="...")
OllamaProvider(model="llama3", base_url="localhost:11434")
```

**Tools** - Real-world integrations
```python
DuckDuckGoSearchTool(max_results=5)
ApifyMarketplaceTool(actor_id="facebook-marketplace-scraper")
```

**Nodes** - Agent types
- `Agent`: Regular speaking agents (can use tools)
- `Moderator`: Controls debate flow (JSON output)
- `Summarizer`: Wraps up conversations
- `Advisor`: Gives feedback (non-blocking)

**Scheduler** - Who talks when
```python
RoundRobinScheduler(order=["agent1", "agent2"])
EveryNScheduler(schedule={"agent1": 1, "summarizer": {"every_n": 3}})
```

**Engine** - Execution loop
1. Call scheduler to get next nodes
2. Execute nodes (agents, tools, providers)
3. Apply actions and update state
4. Persist transcript and checkpoints

**State** - Memory and tracking
- **History**: Conversation context
- **Budgets**: Tool call limits
- **Counters**: Usage tracking
- **Contracts**: Message validation

## 💾 Persistence

**Transcripts** (JSONL) - Human-readable logs
```json
{"t": 1640995200, "iter": 0, "agent_id": "comedian", "role": "agent", "content": "Why did the AI..."}
```

**Checkpoints** (SQLite) - Resume state
```sql
CREATE TABLE checkpoints(thread_id TEXT PRIMARY KEY, payload BLOB, updated_at REAL);
```

## 🔄 Execution Flow

1. **Load**: YAML → Validated Preset
2. **Build**: Preset → Runtime Components
3. **Run**: Engine loop:
   - Scheduler picks next nodes
   - Execute nodes (call providers/tools)
   - Update state and history
   - Persist transcript/checkpoint
4. **Resume**: Load checkpoint → Continue

## 🧠 Key Concepts

**Tool Calling Protocol**
```json
{"tool": "search_ddg", "args": {"query": "your search terms"}}
```

**Budget Management**
- `per_run_max`: Total calls per experiment
- `per_iteration_max`: Calls per turn (resets each turn)

**State Management**
- **History window**: Rolling conversation context
- **Running summary**: Summarizer's ongoing summary
- **Tool counters**: Track usage per tool

## 🔧 Extension Points

**Add New Providers**
```python
class MyProvider(Provider):
    def call(self, messages, **kwargs):
        # Your LLM integration
        return response
```

**Add New Tools**
```python
class MyTool(Tool):
    def run(self, **kwargs):
        # Your integration
        return ToolResult(ok=True, data=result)
```

**Add New Schedulers**
```python
class MyScheduler(Scheduler):
    def next(self, state):
        # Your scheduling logic
        return nodes_to_run
```

## 🎯 Design Principles

- **Simple**: Readable code, clear abstractions
- **Extensible**: Easy to add providers, tools, schedulers
- **Resumable**: Checkpoints enable pause/resume
- **Observable**: Transcripts show everything
- **Budgeted**: Prevent runaway costs

---

**The architecture is designed to be simple enough to understand, powerful enough to build amazing multi-agent experiences.** 🚀