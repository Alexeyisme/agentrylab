from __future__ import annotations

from agentrylab import init


def _preset_with_user_and_agent():
    return {
        "id": "user-node-demo",
        "providers": [
            {"id": "p1", "impl": "tests.fake_impls.TestProvider", "model": "test"},
        ],
        "tools": [
            {"id": "echo", "impl": "tests.fake_impls.EchoTool"},
        ],
        "agents": [
            {"id": "user:alice", "role": "user", "provider": "p1"},
            {"id": "talker", "role": "agent", "provider": "p1", "system_prompt": "You are the agent."},
        ],
        "runtime": {
            "scheduler": {
                "impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler",
                "params": {"order": ["user:alice", "talker"]},
            }
        },
    }


def _preset_with_user_only():
    return {
        "id": "user-only",
        "providers": [
            {"id": "p1", "impl": "tests.fake_impls.TestProvider", "model": "test"},
        ],
        "agents": [
            {"id": "user:alice", "role": "user", "provider": "p1"},
        ],
        "runtime": {
            "scheduler": {
                "impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler",
                "params": {"order": ["user:alice"]},
            }
        },
    }


def test_user_node_consumes_enqueued_and_precedes_agent(tmp_path):
    # Arrange: user turn then agent; enqueue a message for the user node
    lab = init(_preset_with_user_and_agent(), experiment_id="user-node-1", resume=False)
    lab.state.enqueue_user_message("user:alice", "Hello from Alice!")

    # Act: run one tick (user then agent)
    lab.run(rounds=2)

    # Assert: transcript order is user then agent, and agent saw the user line
    rows = lab.store.read_transcript("user-node-1")
    assert len(rows) >= 2
    user_ev, agent_ev = rows[-2], rows[-1]
    assert user_ev.get("role") == "user"
    assert user_ev.get("agent_id") == "user:alice"
    assert "Hello from Alice!" in str(user_ev.get("content"))
    assert agent_ev.get("role") == "agent"
    # Provider should have seen the user message in composed messages
    provider = lab.providers["p1"]
    msgs = getattr(provider, "last_messages", [])
    assert any(m.get("role") == "user" and "Hello from Alice!" in str(m.get("content")) for m in msgs)


def test_empty_user_turn_is_skipped_in_transcript(tmp_path):
    # Arrange: only a user node is scheduled; no messages queued
    lab = init(_preset_with_user_only(), experiment_id="user-node-2", resume=False)

    # Act: run one tick; nothing should be appended for the empty user turn
    lab.run(rounds=3)

    # Assert: transcript has no events (engine skipped empty user output)
    rows = lab.store.read_transcript("user-node-2")
    assert rows == [] or all(r.get("role") != "user" for r in rows)


def test_user_node_never_calls_provider(tmp_path):
    # Arrange: only a user node and one queued message
    lab = init(_preset_with_user_only(), experiment_id="user-node-3", resume=False)
    lab.state.enqueue_user_message("user:alice", "Ping!")

    # Act: run one tick (only user node executes)
    lab.run(rounds=3)

    # Assert: user event exists, but provider was not called by the user node
    rows = lab.store.read_transcript("user-node-3")
    assert any(r.get("role") == "user" and "Ping!" in str(r.get("content")) for r in rows)
    provider = lab.providers["p1"]
    assert not hasattr(provider, "last_messages"), "UserNode should not call provider.chat()"


def test_multi_user_targets_and_order(tmp_path):
    preset = {
        "id": "multi-user",
        "providers": [
            {"id": "p1", "impl": "tests.fake_impls.TestProvider", "model": "test"},
        ],
        "agents": [
            {"id": "user:alice", "role": "user", "provider": "p1"},
            {"id": "user:bob", "role": "user", "provider": "p1"},
            {"id": "talker", "role": "agent", "provider": "p1", "system_prompt": "You are the agent."},
        ],
        "runtime": {
            "scheduler": {
                "impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler",
                "params": {"order": ["user:alice", "user:bob", "talker"]},
            }
        },
    }

    lab = init(preset, experiment_id="multi-user-1", resume=False)
    # Enqueue distinct messages for each user node
    lab.state.enqueue_user_message("user:alice", "Hi from Alice")
    lab.state.enqueue_user_message("user:bob", "Hey from Bob")

    lab.run(rounds=3)

    rows = lab.store.read_transcript("multi-user-1")
    assert len(rows) >= 3
    u1, u2, agent_ev = rows[-3], rows[-2], rows[-1]
    assert u1.get("agent_id") == "user:alice" and "Hi from Alice" in str(u1.get("content"))
    assert u2.get("agent_id") == "user:bob" and "Hey from Bob" in str(u2.get("content"))
    assert agent_ev.get("agent_id") == "talker" and agent_ev.get("role") == "agent"

    # Agent provider should see both user lines in its composed messages
    provider = lab.providers["p1"]
    msgs = getattr(provider, "last_messages", [])
    got_alice = any(m.get("role") == "user" and "Hi from Alice" in str(m.get("content")) for m in msgs)
    got_bob = any(m.get("role") == "user" and "Hey from Bob" in str(m.get("content")) for m in msgs)
    assert got_alice and got_bob
