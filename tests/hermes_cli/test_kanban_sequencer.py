"""Behavior contracts for the supervised kanban sequencer (issue #665)."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from hermes_cli.kanban_sequencer import SequenceResult, Step, run_sequence


def decision(action, reason="recoverable failure", signature="failure-signature"):
    return SimpleNamespace(action=action, reason=reason, signature=signature)


def test_all_done_keeps_order_and_records_one_attempt_per_card():
    spawned = []
    records = []
    steps = [Step("card-a", "Do A"), Step("card-b", "Do B")]

    def spawn(step, *, fresh, seed):
        spawned.append((step.task_id, fresh, seed))
        return {"status": "done"}

    result = run_sequence(
        steps,
        spawn=spawn,
        policy=lambda _: pytest.fail("successful tasks must not invoke policy"),
        ledger=records.append,
    )

    assert result == SequenceResult(["card-a", "card-b"], None, None, 2)
    assert spawned == [("card-a", False, None), ("card-b", False, None)]
    assert records == [
        {
            "task_id": task_id, "attempt": 1, "fresh": False,
            "status": "done", "action": "advance", "reason": None, "signature": None,
        }
        for task_id in ("card-a", "card-b")
    ]


def test_failure_retries_in_fresh_session_with_seed_and_two_ledger_records():
    calls = []
    records = []
    history_sizes = []
    replies = iter([{"status": "failed", "error": "context overflow"}, {"status": "done"}])

    def spawn(step, *, fresh, seed):
        calls.append((step.task_id, fresh, seed))
        return next(replies)

    def policy(results):
        history_sizes.append(len(results))
        return decision("fresh_session", "poisoned history", "overflow")

    result = run_sequence(
        [Step("card-a", "Implement card A")],
        spawn=spawn,
        policy=policy,
        ledger=records.append,
        sleep=lambda _: pytest.fail("fresh retry must not sleep in place"),
    )

    assert result == SequenceResult(["card-a"], None, None, 2)
    assert history_sizes == [1]
    assert calls[0] == ("card-a", False, None)
    assert calls[1][0:2] == ("card-a", True)
    assert isinstance(calls[1][2], str) and calls[1][2].strip()
    assert "Implement card A" in calls[1][2]
    assert [record["status"] for record in records] == ["failed", "done"]
    assert [record["fresh"] for record in records] == [False, True]
    assert records[0]["action"] == "fresh_session"
    assert records[0]["reason"] == "poisoned history"
    assert records[0]["signature"] == "overflow"


def test_in_place_retry_uses_first_backoff_and_preserves_session():
    calls = []
    slept = []
    records = []
    replies = iter([{"status": "failed"}, {"status": "done"}])

    def spawn(step, *, fresh, seed):
        calls.append((fresh, seed))
        return next(replies)

    result = run_sequence(
        [Step("card-a", "Do A")],
        spawn=spawn,
        policy=lambda _: decision("in_place"),
        ledger=records.append,
        sleep=slept.append,
    )

    assert result.completed == ["card-a"]
    assert slept == [15]
    assert calls == [(False, None), (False, None)]
    assert [record["action"] for record in records] == ["in_place", "advance"]


def test_blocked_stops_without_spawning_later_steps():
    spawned = []
    records = []

    def spawn(step, *, fresh, seed):
        spawned.append(step.task_id)
        return {"status": "blocked", "reason": "need human approval"} if step.task_id == "b" else {"status": "done"}

    result = run_sequence(
        [Step("a", "A"), Step("b", "B"), Step("c", "C")],
        spawn=spawn,
        policy=lambda _: pytest.fail("blocked status must not invoke policy"),
        ledger=records.append,
    )

    assert result == SequenceResult(["a"], "b", "need human approval", 2)
    assert spawned == ["a", "b"]
    assert [record["task_id"] for record in records] == ["a", "b"]
    assert records[-1]["status"] == "blocked"
    assert records[-1]["action"] == "stop"


def test_attempt_budget_is_hard_cap_with_explicit_stop_ledger():
    spawned = []
    slept = []
    records = []
    policy_sizes = []

    def spawn(step, *, fresh, seed):
        spawned.append(step.task_id)
        return {"status": "failed"}

    def policy(results):
        policy_sizes.append(len(results))
        return decision("in_place", signature="transient")

    result = run_sequence(
        [Step("a", "A", max_attempts=3), Step("b", "B")],
        spawn=spawn,
        policy=policy,
        ledger=records.append,
        sleep=slept.append,
    )

    assert spawned == ["a", "a", "a"]
    assert slept == [15, 45]
    assert policy_sizes == [1, 2, 3]
    assert result.completed == []
    assert result.stopped_at == "a"
    assert "attempt budget exhausted" in result.reason
    assert result.attempts == 3
    assert len(records) == 3
    assert records[-1]["action"] == "stop"
    assert "attempt budget exhausted" in records[-1]["reason"]
    assert records[-1]["signature"] == "transient"


def test_policy_stop_is_terminal_without_another_spawn():
    calls = []
    records = []

    def spawn(step, *, fresh, seed):
        calls.append(step.task_id)
        return {"status": "failed"}

    result = run_sequence(
        [Step("a", "A"), Step("b", "B")],
        spawn=spawn,
        policy=lambda _: decision("stop", "billing requires intervention", "billing"),
        ledger=records.append,
        sleep=lambda _: pytest.fail("stopped policy cannot back off"),
    )

    assert calls == ["a"]
    assert result == SequenceResult([], "a", "billing requires intervention", 1)
    assert records == [{
        "task_id": "a", "attempt": 1, "fresh": False, "status": "failed",
        "action": "stop", "reason": "billing requires intervention", "signature": "billing",
    }]


def test_retries_use_last_backoff_when_failures_exceed_delay_list():
    slept = []
    records = []
    calls = []

    def spawn(step, *, fresh, seed):
        calls.append(fresh)
        return {"status": "done"} if len(calls) == 5 else {"status": "failed"}

    result = run_sequence(
        [Step("a", "A", max_attempts=5)],
        spawn=spawn,
        policy=lambda _: decision("in_place"),
        ledger=records.append,
        sleep=slept.append,
    )

    assert result == SequenceResult(["a"], None, None, 5)
    assert calls == [False] * 5
    assert slept == [15, 45, 90, 90]
    assert len(records) == 5


def test_failure_history_and_attempt_numbers_reset_for_each_step():
    seen = []
    attempts = {}
    records = []

    def spawn(step, *, fresh, seed):
        attempts[step.task_id] = attempts.get(step.task_id, 0) + 1
        return {"status": "failed"} if attempts[step.task_id] == 1 else {"status": "done"}

    def policy(results):
        seen.append(len(results))
        return decision("in_place")

    result = run_sequence(
        [Step("a", "A", max_attempts=2), Step("b", "B", max_attempts=2)],
        spawn=spawn,
        policy=policy,
        ledger=records.append,
        sleep=lambda _: None,
    )

    assert result == SequenceResult(["a", "b"], None, None, 4)
    assert seen == [1, 1]
    assert [(r["task_id"], r["attempt"]) for r in records] == [
        ("a", 1), ("a", 2), ("b", 1), ("b", 2),
    ]


def test_fresh_then_in_place_resumes_new_session_without_starting_another():
    calls = []
    slept = []
    records = []
    seen = []

    def spawn(step, *, fresh, seed):
        calls.append((fresh, seed))
        return {"status": "done"} if len(calls) == 3 else {"status": "failed"}

    def policy(results):
        seen.append(len(results))
        return decision("fresh_session" if len(results) == 1 else "in_place")

    result = run_sequence(
        [Step("a", "A", max_attempts=3)],
        spawn=spawn,
        policy=policy,
        ledger=records.append,
        sleep=slept.append,
    )

    assert result == SequenceResult(["a"], None, None, 3)
    assert seen == [1, 2]
    assert [fresh for fresh, _ in calls] == [False, True, False]
    assert calls[1][1]
    assert calls[2][1] is None
    assert slept == [45]
    assert [record["action"] for record in records] == ["fresh_session", "in_place", "advance"]


def test_uses_sibling_seed_builder_when_available(monkeypatch):
    sibling = ModuleType("agent.kanban_session_poison")
    received = []
    records = []

    def seed_builder(body, prior, *, max_chars=4000):
        received.append((body, [r["status"] for r in prior], max_chars))
        return "seed from sibling"

    sibling.fresh_session_seed = seed_builder
    monkeypatch.setitem(sys.modules, "agent.kanban_session_poison", sibling)
    calls = []

    def spawn(step, *, fresh, seed):
        calls.append((fresh, seed))
        return {"status": "failed"} if len(calls) == 1 else {"status": "done"}

    result = run_sequence(
        [Step("a", "A")],
        spawn=spawn,
        policy=lambda _: decision("fresh_session"),
        ledger=records.append,
    )

    assert result.completed == ["a"]
    assert received == [("A", ["failed"], 4000)]
    assert calls == [(False, None), (True, "seed from sibling")]


def test_one_attempt_is_not_retried_even_when_policy_wants_fresh():
    records = []
    result = run_sequence(
        [Step("a", "A", max_attempts=1)],
        spawn=lambda step, *, fresh, seed: {"status": "failed"},
        policy=lambda _: decision("fresh_session"),
        ledger=records.append,
    )

    assert result.stopped_at == "a"
    assert result.attempts == 1
    assert "attempt budget exhausted" in result.reason
    assert records[0]["action"] == "stop"


def test_rejects_invalid_budgets_and_unknown_status():
    with pytest.raises(ValueError, match="max_attempts"):
        Step("a", "A", max_attempts=0)
    with pytest.raises(ValueError, match="task_id"):
        Step("", "A")

    records = []
    with pytest.raises(ValueError, match="invalid settled status"):
        run_sequence(
            [Step("a", "A")],
            spawn=lambda step, *, fresh, seed: {"status": "running"},
            policy=lambda _: decision("stop"),
            ledger=records.append,
        )
    assert records == []


def test_empty_sequence_has_no_attempts():
    records = []
    result = run_sequence(
        [],
        spawn=lambda step, *, fresh, seed: pytest.fail("no steps should spawn"),
        policy=lambda _: pytest.fail("no steps should invoke policy"),
        ledger=records.append,
    )
    assert result == SequenceResult([], None, None, 0)
    assert records == []
