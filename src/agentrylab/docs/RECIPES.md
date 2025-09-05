Agentry Lab — Recipes 🍳

Basic non‑streaming run 🧪
```
from agentrylab import init

lab = init("src/agentrylab/presets/debates.yaml", experiment_id="demo-1", prompt="What makes jokes funny?")
status = lab.run(rounds=2)
print(status)
print(lab.history(limit=10))
```

Streaming with callback 📡
```
from agentrylab import run

def on_event(ev: dict):
    print(ev["iter"], ev["agent_id"], ev["role"])  # transcript events

lab, status = run(
    "src/agentrylab/presets/debates.yaml",
    experiment_id="demo-2",
    rounds=2,
    stream=True,
    on_event=on_event,
)
```

Streaming via generator 🔁
```
from agentrylab import init

lab = init("src/agentrylab/presets/debates.yaml", experiment_id="gen-1")
for ev in lab.stream(rounds=2):
    print("gen:", ev["iter"], ev["agent_id"], ev["role"])
print("final:", lab.status)
```

Stop conditions and timeout ⏱️
```
from agentrylab import init

lab = init("src/agentrylab/presets/debates.yaml", experiment_id="stop-1")
# Stop on first event
lab.run(rounds=10, stream=True, on_event=lambda e: None, stop_when=lambda e: True)

lab2 = init("src/agentrylab/presets/debates.yaml", experiment_id="stop-2")
# Stop after 1 second
lab2.run(rounds=100, stream=True, on_event=lambda e: None, timeout_s=1.0)
```

Progress callbacks (on_tick / on_round) 📈
```
from agentrylab import init

lab = init("src/agentrylab/presets/debates.yaml", experiment_id="progress-1")

def on_tick(info: dict):
    print("tick", info["iter"], f"elapsed={info['elapsed_s']:.3f}s")

def on_round(info: dict):
    print("round", info["iter"])  # identical cadence in current engine

lab.run(rounds=2, stream=True, on_event=lambda e: None, on_tick=on_tick, on_round=on_round)
```

Seed initial user message(s) 📨
```
from agentrylab import init

lab = init(
    "src/agentrylab/presets/debates.yaml",
    experiment_id="seed-1",
    user_messages=["Hello, start with irony in humor"],
)
lab.run(rounds=1)
```

Resume the same experiment id 🔁
```
from agentrylab import init

lab = init("src/agentrylab/presets/debates.yaml", experiment_id="resume-1")
lab.run(rounds=1)

# Later (same machine / persistence):
lab2 = init("src/agentrylab/presets/debates.yaml", experiment_id="resume-1")
lab2.run(rounds=1)  # continues from previous checkpoint
```

Programmatic preset construction 🧩
```
from agentrylab import init

preset = {
    "id": "programmatic",
    "providers": [{"id": "p1", "impl": "agentrylab.runtime.providers.openai.OpenAIProvider", "model": "gpt-4o"}],
    "agents": [{"id": "pro", "role": "agent", "provider": "p1", "system_prompt": "You are the agent."}],
    "runtime": {"scheduler": {"impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler", "params": {"order": ["pro"]}}},
}
lab = init(preset, experiment_id="prog-1", user_messages=["Start topic: ..."])
lab.run(rounds=3)
```

Multiple runs in a loop 🔄
```
from agentrylab import init

topics = ["jokes", "puns", "metaphors"]
for i, topic in enumerate(topics):
    lab = init("src/agentrylab/presets/debates.yaml", experiment_id=f"exp-{i}", prompt=f"Explore {topic}")
    lab.run(rounds=2)
```

Inspecting transcripts 🧾
```
from agentrylab import init

lab = init("src/agentrylab/presets/debates.yaml", experiment_id="inspect-1")
lab.run(rounds=1)
for ev in lab.history(limit=20):
    print(ev["iter"], ev["agent_id"], ev["role"], str(ev["content"])[:80])
# Or read directly from the store
rows = lab.store.read_transcript("inspect-1", limit=100)
```
