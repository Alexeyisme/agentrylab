# 🚀 AgentryLab CLI

**Minimal ceremony, maximum signal. Load presets, run agents, watch the magic.**

## 🎯 Essential Commands

```bash
# Run a preset
agentrylab run <preset.yaml> [options]

# Jump into conversations
agentrylab say <preset.yaml> <thread-id> "your message"

# Check what's happening
agentrylab status <preset.yaml> <thread-id>
agentrylab ls <preset.yaml>

# Clean up
agentrylab reset <preset.yaml> <thread-id>
```

## ⚙️ Run Options

| Option | What It Does |
|--------|-------------|
| `--max-iters N` | Run for N rounds |
| `--thread-id ID` | Name your experiment (enables resume) |
| `--objective "text"` | Set topic on the fly |
| `--no-resume` | Start fresh (ignore checkpoints) |
| `--no-stream` | Quiet mode (no live updates) |
| `--interactive` | Prompt for user messages when a `user` node exists |
| `--params '{...}'` | Provide `user_inputs` as JSON (non-interactive) |

## 🎭 Examples

```bash
# Comedy gold
agentrylab run standup_club.yaml --objective "AI taking over comedy" --max-iters 6

# Real debates with evidence
agentrylab run debates.yaml --thread-id mars-debate --objective "Mars colonization" --max-iters 4

# Interactive research
agentrylab run research_assistant.yaml --objective "quantum computing"
agentrylab say research_assistant.yaml demo "What about quantum biology?"
agentrylab run research_assistant.yaml --thread-id demo --resume --max-iters 1

# Marketplace deals (with user inputs)
agentrylab run marketplace_deals.yaml --params '{"query": "MacBook Pro M3", "location": "NYC", "min_price": 1000, "max_price": 3000}'
```

## 🔑 Environment Setup

Create `.env` file for API keys:

```bash
# Optional: OpenAI for advanced presets
OPENAI_API_KEY=sk-...

# Optional: Apify for marketplace deals
APIFY_API_TOKEN=apify_...

# Optional: Wolfram Alpha
WOLFRAM_APP_ID=...

# Optional: Ollama for local models
OLLAMA_BASE_URL=http://localhost:11434
```

## 📡 Streaming Output

**Live mode** (default): Watch agents work in real-time
```bash
agentrylab run standup_club.yaml --max-iters 4
# === New events ===
# [agent] comicA: Why did the AI go to therapy?...
```

**Quiet mode**: Just show final results
```bash
agentrylab run standup_club.yaml --max-iters 4 --no-stream
# === Last messages ===
# [agent] comicA: Why did the AI go to therapy?...
```

## 💾 Persistence

**Transcripts**: `outputs/<thread-id>.jsonl` (human-readable logs)
**Checkpoints**: `outputs/checkpoints.db` (resume anywhere)

```bash
# Clean everything
rm -rf outputs/

# Clean specific thread
agentrylab reset standup_club.yaml comedy-night --delete-transcript
```

## 🧯 Troubleshooting

**Empty responses**: 
- Try `--no-resume` for a fresh start
- Check API keys in `.env`
- Use `gpt-4o-mini` for complex multi-agent tasks

**Tool budget exceeded**:
- Reduce `--max-iters` 
- Check tool budgets in preset YAML

**Missing presets**:
- Use full paths: `src/agentrylab/presets/standup_club.yaml`
- Or install from source: `pip install -e .`

## 🎯 Pro Tips

- **Unique thread IDs**: Keep experiments separate
- **Resume anywhere**: Use `--thread-id` to continue later  
- **Live debugging**: Set `runtime.logs.level: DEBUG` in preset
- **Clean slate**: Use `--no-resume` when you need fresh state

---

**Ready to orchestrate some agents? Let's go! 🚀**