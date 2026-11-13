"""A background review a live turn supersedes is owed to that turn's end, never dropped."""
import types

import run_agent
from agent.background_review import with_owed_background_review


class _Run:
    def __init__(self, cancelled):
        self.cancel_requested = types.SimpleNamespace(is_set=lambda: cancelled)


def _agent(monkeypatch):
    import agent.review_idle_queue as riq
    monkeypatch.setattr(riq, "review_targets_managed_local", lambda a, cfg: False)
    return types.SimpleNamespace(_REVIEW_REQUEUE_MAX_ATTEMPTS=3)


def _finish_review(agent, cancelled):
    run_agent.AIAgent._maybe_requeue_preempted_review(
        agent, _Run(cancelled), {"task_cfg": {}, "focus": None, "review_memory": True, "review_skills": False})


def test_superseded_review_is_owed_until_a_review_spawns(monkeypatch):
    agent = _agent(monkeypatch)
    _finish_review(agent, cancelled=True)

    # The superseding turn triggered only a skill review: it also runs the owed memory one.
    assert with_owed_background_review(agent, False, True) == (True, True)
    # That turn could not review (interrupted, no reply): the next turn still owes it.
    assert with_owed_background_review(agent, False, False) == (True, False)

    spawned = []
    monkeypatch.setattr("agent.background_review.prepare_background_review_run", lambda a: object())
    monkeypatch.setattr("agent.background_review.spawn_background_review_thread",
                        lambda *a, **k: spawned.append(k) or ((lambda: None), ""))
    monkeypatch.setattr(run_agent.threading, "Thread", lambda **k: types.SimpleNamespace(start=lambda: None))
    run_agent.AIAgent._spawn_background_review_now(agent, [], review_memory=True)
    assert spawned and with_owed_background_review(agent, False, False) == (False, False)


def test_a_review_that_ran_owes_nothing(monkeypatch):
    agent = _agent(monkeypatch)
    _finish_review(agent, cancelled=False)
    assert with_owed_background_review(agent, False, False) == (False, False)


def test_only_live_turn_preemption_creates_review_debt(monkeypatch):
    """Stopping or closing a session must not schedule the stopped review on its next turn."""
    from agent.background_review import _BackgroundReviewRun, cancel_background_review_for_live_turn

    for reason, expected in (
        ("background review superseded", True),
        ("session interrupted", False),
        ("session ended", False),
    ):
        agent = _agent(monkeypatch)
        review_run = _BackgroundReviewRun()
        agent._background_review_run = review_run
        # The thread's request acknowledgement is already delivered in this isolated boundary test.
        review_run.request_done.set()
        cancel_background_review_for_live_turn(agent, tool_reason=reason)
        run_agent.AIAgent._maybe_requeue_preempted_review(
            agent, review_run,
            {"task_cfg": {}, "focus": None, "review_memory": True, "review_skills": False},
        )
        assert with_owed_background_review(agent, False, False) == (expected, False), reason
