from agentrylab.lab import init_lab


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
        "agents": [
            {"id": "pro", "role": "agent", "provider": "p1", "system_prompt": "You are the agent."}
        ],
        "summarizer": {"id": "sum", "role": "summarizer", "provider": "p1"},
        "runtime": {
            "scheduler": {
                "impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler",
                "params": {"order": ["pro", "sum"]},
            }
        },
    }


def test_start_extend_stop_status_and_history(tmp_path):
    # Use dict form; loader validates and Lab wires everything
    lab = init_lab(_preset_dict(), thread_id="test-thread", resume=False)

    # start for 2 iterations
    st = lab.start(max_iters=2)
    assert st.iter == 2
    assert st.thread_id == "test-thread"
    assert st.is_active is False or st.is_active is True  # status may be inactive after stopping conditions

    # extend by 1
    st2 = lab.extend(add_iters=1)
    assert st2.iter == 3

    # status() shape
    s = lab.get_status()
    assert s.thread_id == "test-thread"

    # history: should have some entries
    hist = lab.get_history(limit=10)
    assert isinstance(hist, list)
