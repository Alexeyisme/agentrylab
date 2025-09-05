from __future__ import annotations

import uuid

from agentrylab import init


def preset_dict():
    return {
        "id": "user-node-test",
        "providers": [
            {"id": "p1", "impl": "tests.fake_impls.TestProvider", "model": "test"},
        ],
        "agents": [
            {"id": "user:alice", "role": "user"},
            {
                "id": "talker",
                "role": "agent",
                "provider": "p1",
                "system_prompt": "Reply to the user",
            },
        ],
        "runtime": {
            "scheduler": {
                "impl": "agentrylab.runtime.scheduler.every_n.EveryNScheduler",
                "params": {"schedule": {"user:alice": 1, "talker": 1}},
            }
        },
    }


def test_user_node_consumes_queue_and_skips_when_empty():
    tid = f"user-node-{uuid.uuid4().hex[:6]}"
    lab = init(preset_dict(), experiment_id=tid, resume=False)
    # enqueue message for first turn only
    lab.post_user_message("hi there", user_id="user:alice", immediate=False, persist=False)
    # first iteration processes user + agent
    lab.run(rounds=1)
    first_msgs = lab.providers["p1"].last_messages
    assert any(m.get("role") == "user" for m in first_msgs)
    # second iteration: no user message queued -> skipped
    lab.run(rounds=1)
    tail = lab.store.read_transcript(tid, limit=10)
    roles = [e["role"] for e in tail]
    assert roles == ["user", "agent", "agent"]
