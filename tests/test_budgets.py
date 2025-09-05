from __future__ import annotations

from typing import Any, Dict

from agentrylab import init
from agentrylab.runtime.providers.base import LLMProvider, Message


class AlwaysToolProvider(LLMProvider):
    def __init__(self, *, model: str, **kwargs: Any) -> None:
        super().__init__(model=model, **kwargs)

    def _send_chat(
        self,
        messages: list[Message],
        *,
        tools: list[Dict[str, Any]] | None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        # Always ask for echo tool on each call
        return {"content": '{"tool":"echo","args":{}}'}


def _base_preset() -> Dict[str, Any]:
    return {
        "id": "budget-test",
        "providers": [{"id": "p1", "impl": "tests.test_budgets.AlwaysToolProvider", "model": "test"}],
        "tools": [{"id": "echo", "impl": "tests.fake_impls.EchoTool"}],
        "agents": [
            {"id": "pro", "role": "agent", "provider": "p1", "system_prompt": "You are the agent.", "tools": ["echo"]},
        ],
        "runtime": {
            "scheduler": {
                "impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler",
                "params": {"order": ["pro"]},
            },
            # allow extra fields like budgets
            "budgets": {"tools": {}},
        },
    }


def test_per_iteration_max_zero_denies_tool_and_sets_error(tmp_path):
    preset = _base_preset()
    # Deny any tool per iteration via per-tool overlay
    preset["tools"][0]["budget"] = {"per_iteration_max": 0}
    lab = init(preset, experiment_id="budget-iter-0", resume=False)
    lab.run(rounds=1)
    # Agent should emit a failure message due to tool error (budget denial)
    events = lab.store.read_transcript("budget-iter-0")
    # Find agent event
    agent_events = [e for e in events if e.get("role") == "agent"]
    assert agent_events, events
    assert "tool calls failed" in str(agent_events[-1].get("content", ""))
    snap = lab.store.load_checkpoint("budget-iter-0")
    assert snap.get("_tool_calls_run_total", 0) == 0


def test_per_run_max_one_across_agents_denies_second_call(tmp_path):
    # Two agents both try to call echo on their first turn
    preset: Dict[str, Any] = _base_preset()
    preset["agents"].append({"id": "con", "role": "agent", "provider": "p1", "system_prompt": "You are the agent.", "tools": ["echo"]})
    preset["runtime"]["scheduler"]["params"]["order"] = ["pro", "con"]
    # Per-tool budget per run: 1
    preset["tools"][0]["budget"] = {"per_run_max": 1}
    lab = init(preset, experiment_id="budget-run-1", resume=False)
    lab.run(rounds=1)
    events = lab.store.read_transcript("budget-run-1")
    # At least one agent should have failed due to budget denial
    failed = [e for e in events if e.get("role") == "agent" and "tool calls failed" in str(e.get("content", ""))]
    assert failed, events
    snap = lab.store.load_checkpoint("budget-run-1")
    # Exactly one tool call succeeded
    assert snap.get("_tool_calls_run_total") == 1
