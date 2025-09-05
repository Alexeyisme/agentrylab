from agentrylab.runtime.scheduler.round_robin import RoundRobinScheduler
from agentrylab.runtime.scheduler.every_n import EveryNScheduler


def test_round_robin_sequence():
    rr = RoundRobinScheduler(order=["pro", "con", "moderator"]) 
    rr.configure(agents=["pro", "con", "moderator"])  # filter to active
    # turn 0 -> pro, 1 -> con, 2 -> moderator, 3 -> pro
    assert rr.next(0, ["pro", "con", "moderator"]) == ["pro"]
    assert rr.next(1, ["pro", "con", "moderator"]) == ["con"]
    assert rr.next(2, ["pro", "con", "moderator"]) == ["moderator"]
    assert rr.next(3, ["pro", "con", "moderator"]) == ["pro"]


def test_every_n_sequence():
    # pro every turn; moderator every 2nd; summarizer every 3rd
    sched = EveryNScheduler(schedule={"pro": 1, "moderator": 2, "summarizer": 3})
    sched.configure(agents=["pro", "moderator", "summarizer"], schedule=None)
    # turn indices are 0-based; selection uses (turn+1) % n == 0
    assert sched.next(0, ["pro", "moderator", "summarizer"]) == ["pro"]  # pro every turn
    assert sched.next(1, ["pro", "moderator", "summarizer"]) == ["pro", "moderator"]
    assert sched.next(2, ["pro", "moderator", "summarizer"]) == ["pro", "summarizer"]
    assert sched.next(3, ["pro", "moderator", "summarizer"]) == ["pro", "moderator"]
