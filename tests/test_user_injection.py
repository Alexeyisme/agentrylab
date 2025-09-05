from __future__ import annotations

from agentrylab import init


def _preset_dict():
    return {
        "id": "user-inject",
        "providers": [
            {"id": "p1", "impl": "tests.fake_impls.TestProvider", "model": "test"},
        ],
        "agents": [
            {"id": "talker", "role": "agent", "provider": "p1", "system_prompt": "You are the agent."}
        ],
        "runtime": {
            "scheduler": {
                "impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler",
                "params": {"order": ["talker"]},
            }
        },
    }


def test_post_user_message_appears_in_history_and_provider_sees_it(tmp_path):
    lab = init(_preset_dict(), experiment_id="user-inject-1", resume=False)
    # Post a user message
    lab.post_user_message("Hello agents!", user_id="user")

    # Verify it's in in-memory history before running
    assert any(e.get("role") == "user" and "Hello agents!" in str(e.get("content")) for e in lab.state.history)

    # Run one round; provider should now see the user message in messages
    lab.run(rounds=1)
    provider = lab.providers["p1"]
    msgs = getattr(provider, "last_messages", [])
    assert any(m.get("role") == "user" and "Hello agents!" in str(m.get("content")) for m in msgs)
