# 🧪 AgentryLab

**Multi-agent orchestration made simple. Drop in agents, watch the magic happen.**

<p align="center">
  <a href="https://github.com/Alexeyisme/agentrylab/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Alexeyisme/agentrylab/actions/workflows/ci.yml/badge.svg" /></a>
  <a href="https://pypi.org/project/agentrylab/"><img alt="PyPI" src="https://img.shields.io/pypi/v/agentrylab.svg" /></a>
  <a href="https://pypi.org/project/agentrylab/"><img alt="License" src="https://img.shields.io/pypi/l/agentrylab.svg" /></a>
  <a href="https://pypi.org/project/agentrylab/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/agentrylab.svg" /></a>
</p>

## 🚀 Quick Start

```bash
pip install agentrylab

# Comedy gold
agentrylab run standup_club.yaml --objective "remote work" --max-iters 4

# Real debates with evidence  
agentrylab run debates.yaml --objective "Should we colonize Mars?" --max-iters 4

# Facebook Marketplace deals finder
agentrylab run marketplace_deals.yaml --objective "MacBook Pro deals"
```

## 🎭 What You Get

**5 killer presets** that actually work:

| Preset | What It Does | Cool Factor |
|--------|-------------|-------------|
| 🎤 **Stand-Up Club** | Two comedians + MC | Comedy gold, pure entertainment |
| 🏛️ **Debates** | Pro/con + evidence search | Real web research, actual citations |
| 🔬 **Research** | Scientists collaborate | Academic rigor meets AI |
| 🤖 **Research Assistant** | Interactive research chat | Human-in-the-loop web research |
| 🛒 **Marketplace Deals** | Facebook Marketplace finder | Real listings, real URLs, real deals |

## 🧠 Core Concepts

- **Agents**: Roles that speak (comedian, scientist, debater — no limits!)
- **Tools**: Real integrations (DuckDuckGo search, Facebook Marketplace, Wolfram Alpha)
- **Providers**: LLM backends (OpenAI, Ollama)
- **Schedulers**: Who talks when (round-robin, every-N)

## 🛠️ Installation & Setup

```bash
# Install
pip install agentrylab

# Optional: Local models with Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3

# Optional: API keys in .env
echo "OPENAI_API_KEY=sk-..." >> .env
echo "APIFY_API_TOKEN=apify_..." >> .env
```

## 🎯 Examples

### Comedy Club
```bash
agentrylab run standup_club.yaml --objective "AI taking over the world" --max-iters 6
```

### Real Research
```bash
agentrylab run research.yaml --objective "quantum biology breakthroughs"
```

### Interactive Research
```bash
# Start conversation
agentrylab run research_assistant.yaml --objective "latest AI developments"

# Jump in anytime
agentrylab say research_assistant.yaml demo "What about quantum computing?"
agentrylab run research_assistant.yaml --thread-id demo --resume --max-iters 1
```

### Marketplace Deals
```bash
agentrylab run marketplace_deals.yaml --objective "iPhone 15 Pro deals in NYC"
```

## 🐍 Python API

```python
from agentrylab import init

# Start a comedy show
lab = init("standup_club.yaml", experiment_id="comedy-night")
lab.run(rounds=6)

# Check out the show
for msg in lab.state.history:
    print(f"[{msg['role']}]: {msg['content']}")
```

## 🔧 Advanced Features

- **Real-time streaming**: Watch agents work live
- **Resume anywhere**: Pick up where you left off
- **Tool budgets**: Prevent runaway API costs
- **Human-in-the-loop**: Jump into conversations anytime
- **Persistence**: Everything saved to SQLite + JSONL

## 📚 Documentation

- [CLI Reference](src/agentrylab/docs/CLI.md) - All commands
- [Configuration](src/agentrylab/docs/CONFIG.md) - YAML preset format
- [Architecture](src/agentrylab/docs/ARCHITECTURE.md) - How it works
- [Persistence](src/agentrylab/docs/PERSISTENCE.md) - Data storage format

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

**Quick wins:**
- New presets (comedy, debates, research, etc.)
- New tools (APIs, databases, etc.)
- New providers (Claude, Gemini, etc.)

## 📄 License

MIT - Go build something amazing!

---

**Made with ❤️ for the AI community. Because single agents are boring.** 🤖