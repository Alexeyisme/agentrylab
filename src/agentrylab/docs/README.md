# 📚 AgentryLab Documentation

**Everything you need to master multi-agent orchestration.**

## 🚀 Quick Links

- [The Room](ROOM.md) - Web UI: android personas on a live stage, accounts, bring-your-own-key vault, REST + WebSocket API
- [CLI Reference](CLI.md) - All commands and options
- [Configuration Guide](CONFIG.md) - YAML preset format
- [Architecture](ARCHITECTURE.md) - How the system works
- [Persistence](PERSISTENCE.md) - Data storage format
- [Web UI development](../../../web/README.md) - Frontend stack, layout, animation model

## 🎯 Getting Started

1. **Install**: `pip install 'agentrylab[web]'`
2. **Watch the show**: `agentrylab serve` and open http://127.0.0.1:8000
3. **Or run a preset**: `agentrylab run standup_club.yaml --objective "AI comedy"`
4. **Read the guides**: Start with [ROOM](ROOM.md), [CLI](CLI.md) and [CONFIG](CONFIG.md)

## 🎭 What's Inside

**5 Killer Presets:**
- 🎤 **Stand-Up Club** - Comedy gold
- 🏛️ **Debates** - Real evidence-based arguments  
- 🔬 **Research** - Academic collaboration
- 🤖 **Research Assistant** - Interactive web research
- 🛒 **Marketplace Deals** - Facebook Marketplace finder

**The Room (web):**
- Zero-player stage: add/remove android personas, watch them riff, join in
- 12-persona library plus a builder with selectable faces, bodies, colours
- Accounts with a bring-your-own-key vault (OpenAI, Anthropic, DeepSeek, xAI) and private rooms

**Core Features:**
- Real tool integrations (search, marketplace, etc.)
- Human-in-the-loop conversations
- Resume anywhere persistence
- Streaming live updates
- Tool budget controls

## 🧠 Core Concepts

- **Agents**: Roles that speak and act
- **Tools**: Real-world integrations
- **Providers**: LLM backends (OpenAI, Anthropic, Ollama, and OpenAI-compatible APIs such as DeepSeek and xAI)
- **Schedulers**: Who talks when
- **Presets**: YAML configurations

## 🛠️ Architecture

**Simple & Readable:**
- Engine steps through scheduler
- Nodes execute (agents, moderators, etc.)
- Tools provide real data
- State tracks everything
- Persistence saves all

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](../../../CONTRIBUTING.md).

**Quick wins:**
- New presets
- New tools  
- New providers
- Documentation improvements

---

**Ready to orchestrate some agents? Let's go! 🚀**