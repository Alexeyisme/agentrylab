# 💾 Persistence

**How AgentryLab saves and resumes your experiments.**

## 🎯 Overview

- **📜 Transcripts**: Human-readable conversation logs (JSONL)
- **💾 Checkpoints**: Resume state (SQLite)

## 📜 Transcripts (JSONL)

**Location**: `outputs/<thread-id>.jsonl`

Each line is a JSON event:
```json
{
  "t": 1640995200,
  "iter": 0,
  "agent_id": "comedian",
  "role": "agent",
  "content": "Why did the AI go to therapy?",
  "metadata": {"citations": ["https://example.com"]},
  "latency_ms": 1234
}
```

**Event Fields**:
- `t`: Unix timestamp
- `iter`: Turn number
- `agent_id`: Who said it
- `role`: agent | moderator | summarizer | advisor
- `content`: What was said
- `metadata`: Citations, provider info, etc.
- `latency_ms`: How long it took

## 💾 Checkpoints (SQLite)

**Location**: `outputs/checkpoints.db`

**Table**: `checkpoints(thread_id, payload, updated_at)`

**Saved State**:
- `thread_id`: Experiment ID
- `iter`: Current turn
- `history`: Conversation context
- `_tool_calls_run_total`: Tool usage
- `running_summary`: Summarizer's ongoing summary

## 🔄 Resume & Clean

**Resume anywhere**:
```bash
agentrylab run standup_club.yaml --thread-id comedy-night --resume
```

**Clean up**:
```bash
# Clean everything
rm -rf outputs/

# Clean specific thread
agentrylab reset standup_club.yaml comedy-night --delete-transcript
```

---

**Everything is saved automatically. Resume from anywhere! 🚀**