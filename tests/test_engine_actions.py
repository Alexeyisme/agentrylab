from __future__ import annotations

from typing import Any, Dict, List

from agentrylab import init
from agentrylab.runtime.providers.base import LLMProvider, Message


class StopProvider(LLMProvider):
    """Provider that emits moderator STOP action JSON."""

    def __init__(self, *, model: str, **kwargs: Any) -> None:
        super().__init__(model=model, **kwargs)

    def _send_chat(
        self,
        messages: List[Message],
        *,
        tools: List[Dict[str, Any]] | None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        payload = {
            "summary": "Stopping here.",
            "drift": 0.0,
            "action": "STOP",
            "rollback": 0,
            "citations": [],
            "clear_summaries": False,
        }
        import json as _json
        return {"content": _json.dumps(payload)}


class StepBackProvider(StopProvider):
    def _send_chat(
        self,
        messages: List[Message],
        *,
        tools: List[Dict[str, Any]] | None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        payload = {
            "summary": "Step back by 1.",
            "drift": 0.5,
            "action": "STEP_BACK",
            "rollback": 1,
            "citations": [],
            "clear_summaries": False,
        }
        import json as _json
        return {"content": _json.dumps(payload)}


def _preset_with_moderator(impl: str) -> Dict[str, Any]:
    return {
        "id": "actions",
        "providers": [{"id": "p1", "impl": impl, "model": "test"}],
        "moderator": {
            "id": "moderator",
            "role": "moderator",
            "provider": "p1",
            "system_prompt": "You are the Moderator. Respond ONLY with JSON.",
        },
        "runtime": {
            "scheduler": {
                "impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler",
                "params": {"order": ["moderator"]},
            }
        },
    }


def test_moderator_stop_sets_stop_flag(tmp_path):
    # Provide fully qualified path to this test module classes
    impl = "tests.test_engine_actions.StopProvider"
    lab = init(_preset_with_moderator(impl), experiment_id="stop-flag", resume=False)
    lab.run(rounds=1)
    # Moderator action recorded in transcript
    events = lab.store.read_transcript("stop-flag")
    assert events and events[-1].get("actions", {}).get("type") == "STOP"


def test_moderator_step_back_rolls_history(tmp_path):
    impl = "tests.test_engine_actions.StepBackProvider"
    lab = init(_preset_with_moderator(impl), experiment_id="step-back", resume=False)
    # Seed 2 user messages so rollback of 1 has an effect in history
    lab.state.history.extend([
        {"agent_id": "user", "role": "user", "content": "msg1"},
        {"agent_id": "user", "role": "user", "content": "msg2"},
    ])
    before = len(lab.state.history)
    lab.run(rounds=1)
    after = len(lab.state.history)
    # Moderator output appended then rolled back -> history length unchanged
    assert after == before
    events = lab.store.read_transcript("step-back")
    assert events and events[-1].get("actions", {}).get("type") == "STEP_BACK"
