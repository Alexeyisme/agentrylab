from __future__ import annotations

from agentrylab import init, run
from agentrylab import list_threads as list_threads_api


def _preset_dict():
    return {
        "id": "lab-test",
        "providers": [
            {
                "id": "p1",
                "impl": "tests.fake_impls.TestProvider",
                "model": "test",
            }
        ],
        "tools": [
            {"id": "echo", "impl": "tests.fake_impls.EchoTool", "params": {}},
        ],
        "agents": [
            {"id": "pro", "role": "agent", "provider": "p1", "system_prompt": "You are the agent.", "tools": ["echo"]}
        ],
        "runtime": {
            "scheduler": {
                "impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler",
                "params": {"order": ["pro"]},
            },
            "message_contract": {"require_metadata": True, "min_citations": 1},
        },
    }


def test_init_and_run_non_streaming(tmp_path):
    lab = init(_preset_dict(), experiment_id="api-1", prompt="Test objective", user_messages=["Hello world"], resume=False)
    status = lab.run(rounds=1)
    assert status.iter >= 1
    # provider captured last messages, should include our user message
    provider = lab.providers["p1"]
    msgs = getattr(provider, "last_messages", [])
    assert any(m.get("role") == "user" and "Hello world" in str(m.get("content")) for m in msgs)


def test_top_level_run_streaming(tmp_path):
    events = []

    def on_ev(e):
        events.append(e)

    lab, status = run(_preset_dict(), experiment_id="api-2", rounds=1, stream=True, on_event=on_ev, resume=False)
    assert status.iter >= 1
    assert len(events) >= 1


def test_stream_stop_conditions_and_timeout(tmp_path):
    # stop after first event using stop_when
    lab = init(_preset_dict(), experiment_id="api-3", resume=False)
    st = lab.run(rounds=10, stream=True, on_event=lambda e: None, stop_when=lambda e: True)
    assert st.iter == 1

    # timeout before any tick
    lab2 = init(_preset_dict(), experiment_id="api-4", resume=False)
    st2 = lab2.run(rounds=10, stream=True, on_event=lambda e: None, timeout_s=0)
    assert st2.iter == 0


def test_time_based_callbacks_called(tmp_path):
    lab = init(_preset_dict(), experiment_id="api-5", resume=False)
    ticks = {"count": 0, "last": None}

    def on_tick(info):
        ticks["count"] += 1
        ticks["last"] = info

    rounds = {"count": 0}

    def on_round(info):
        rounds["count"] += 1

    st = lab.run(rounds=2, stream=True, on_event=lambda e: None, on_tick=on_tick, on_round=on_round)
    assert st.iter == 2
    assert ticks["count"] >= 2
    assert rounds["count"] >= 2
    assert isinstance(ticks["last"].get("elapsed_s"), float)


def test_clean_outputs_removes_transcript_and_checkpoint(tmp_path):
    lab = init(_preset_dict(), experiment_id="clean-1", resume=False)
    # Run to create outputs
    lab.run(rounds=1)
    # Pre-checks: transcript has content; checkpoint row exists
    assert len(lab.store.read_transcript("clean-1", limit=None)) >= 1
    threads = [tid for (tid, _) in lab.store.list_threads()]
    assert "clean-1" in threads

    # Clean both transcript and checkpoint
    lab.clean()

    # Transcript removed
    assert lab.store.read_transcript("clean-1", limit=None) == []
    # Checkpoint removed
    threads_after = [tid for (tid, _) in lab.store.list_threads()]
    assert "clean-1" not in threads_after


def test_list_threads_top_level_api(tmp_path):
    # create a run so a thread appears in persistence
    lab = init(_preset_dict(), experiment_id="lt-1", resume=False)
    lab.run(rounds=1)
    rows = list_threads_api(_preset_dict())
    tids = [tid for tid, _ in rows]
    assert "lt-1" in tids
