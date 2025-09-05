from __future__ import annotations

from typing import Any, Dict

from agentrylab import init


def _preset() -> Dict[str, Any]:
    # Minimal preset using test doubles, ensures a tool call occurs
    return {
        "id": "shape-test",
        "providers": [
            {"id": "p1", "impl": "tests.fake_impls.TestProvider", "model": "test"},
        ],
        "tools": [
            {"id": "echo", "impl": "tests.fake_impls.EchoTool"},
        ],
        "agents": [
            {
                "id": "pro",
                "role": "agent",
                "provider": "p1",
                "system_prompt": "You are the agent.",
                "tools": ["echo"],
            }
        ],
        "runtime": {
            "scheduler": {
                "impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler",
                "params": {"order": ["pro"]},
            }
        },
    }


def test_transcript_event_shape_and_types(tmp_path):
    lab = init(_preset(), experiment_id="shape-transcript", resume=False)
    lab.run(rounds=1)
    events = lab.store.read_transcript("shape-transcript")
    assert isinstance(events, list) and events
    ev = events[-1]
    # Required keys exist
    for key in ("t", "iter", "agent_id", "role", "content", "metadata", "actions"):
        assert key in ev
    # Types
    assert isinstance(ev["t"], (int, float))
    assert isinstance(ev["iter"], int)
    assert isinstance(ev["agent_id"], str)
    assert isinstance(ev["role"], str)
    # content may be str or dict depending on role/provider
    assert isinstance(ev.get("latency_ms"), (int, float))
    md = ev.get("metadata")
    assert md is None or isinstance(md, dict)
    actions = ev.get("actions")
    assert actions is None or isinstance(actions, dict)
    # If metadata exists, citations list (from EchoTool/TestProvider) should be present
    if isinstance(md, dict) and "citations" in md:
        cites = md.get("citations")
        assert isinstance(cites, list)


def test_checkpoint_snapshot_shape_and_counters(tmp_path):
    lab = init(_preset(), experiment_id="shape-checkpoint", resume=False)
    lab.run(rounds=1)
    snap = lab.store.load_checkpoint("shape-checkpoint")
    assert isinstance(snap, dict)

    # Expected keys present (opaque ones tolerated)
    for key in (
        "thread_id",
        "iter",
        "stop_flag",
        "history",
        "running_summary",
        "_tool_calls_run_total",
        "_tool_calls_iteration",
        "_tool_calls_run_by_id",
        "_tool_calls_iter_by_id",
    ):
        assert key in snap

    assert snap["thread_id"] == "shape-checkpoint"
    assert isinstance(snap["iter"], int) and snap["iter"] >= 1
    assert isinstance(snap["stop_flag"], bool)
    assert isinstance(snap["history"], list)
    # history entries are dicts with minimal keys
    if snap["history"]:
        ent = snap["history"][-1]
        assert isinstance(ent, dict)
        for k in ("agent_id", "role", "content"):
            assert k in ent

    # Tool counters should reflect at least one echo call
    assert isinstance(snap["_tool_calls_run_total"], int) and snap["_tool_calls_run_total"] >= 1
    assert isinstance(snap["_tool_calls_iteration"], int) and snap["_tool_calls_iteration"] >= 1
    by_id = snap["_tool_calls_run_by_id"]
    assert isinstance(by_id, dict) and by_id.get("echo", 0) >= 1
    iter_by_id = snap["_tool_calls_iter_by_id"]
    assert isinstance(iter_by_id, dict) and iter_by_id.get("echo", 0) >= 1

