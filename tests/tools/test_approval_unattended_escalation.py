"""``approvals.unattended_escalation: deny`` hands an escalated approval back to the agent at once
in a delegated child instead of parking it on the parent's gateway card.

A ``delegate_task`` child of a gateway/desktop parent takes the gateway branch: when the guardian
ESCALATEs, the card waits on the parent's chat for ``approvals.timeout``. Nobody watches a child's
card, so the wait usually ends as a timeout. With the key set to ``deny`` the guardian still runs
(routine commands are still approved) and only the human step becomes an instant hand-off. The
default ``wait`` and attended (non-child) sessions keep the card.
"""

import threading
import time

import pytest

import tools.approval as approval_mod
from agent.delegation_context import DELEGATED_CHILD_ENV_MARKER
from tools import approval_context

SESSION = "test-unattended-escalation"
COMMAND = "rm -rf .git"
TIMEOUT = 2  # keeps the base (parked) run short; the hand-off must beat it by far


@pytest.fixture
def gateway_turn(monkeypatch):
    approval_mod._gateway_queues.clear()
    approval_mod._gateway_notify_cbs.clear()
    approval_mod._session_approved.clear()
    for var in ("HERMES_CRON_SESSION", "HERMES_YOLO_MODE", "HERMES_INTERACTIVE",
                "HERMES_SINGLE_QUERY_SESSION", "HERMES_EXEC_ASK", DELEGATED_CHILD_ENV_MARKER):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HERMES_GATEWAY_SESSION", "1")
    monkeypatch.setenv("HERMES_SESSION_KEY", SESSION)
    monkeypatch.setattr(approval_mod, "_YOLO_MODE_FROZEN", False)
    cards = []
    approval_mod.register_gateway_notify(SESSION, lambda data: cards.append(data))
    verdict = {"value": "escalate"}
    monkeypatch.setattr(approval_mod, "_smart_verdict", lambda *a, **k: verdict["value"])

    def configure(escalation=None, verdict_value="escalate"):
        cfg = {"mode": "smart", "timeout": TIMEOUT}
        if escalation is not None:
            cfg["unattended_escalation"] = escalation
        monkeypatch.setattr(approval_context, "_get_approval_config", lambda: cfg)
        verdict["value"] = verdict_value

    yield configure, cards
    approval_mod._gateway_queues.clear()
    approval_mod._gateway_notify_cbs.clear()


def _timed_guard():
    start = time.monotonic()
    result = approval_mod.check_all_command_guards(COMMAND, "local")
    return result, time.monotonic() - start


def test_subagent_escalation_hands_off_at_once_without_a_card(gateway_turn, monkeypatch):
    configure, cards = gateway_turn
    configure("deny")
    monkeypatch.setenv(DELEGATED_CHILD_ENV_MARKER, "1")

    result, elapsed = _timed_guard()

    assert cards == [], "the escalation was parked on the parent's approval card"
    assert result["approved"] is False
    assert result.get("user_consent") is False
    assert "No human is watching this session" in result["message"]
    assert "kanban_block(kind=needs_input)" in result["message"]
    assert "Do not retry" in result["message"]
    assert elapsed < 1.0


def test_kanban_worker_escalation_never_parks_on_a_card(gateway_turn, monkeypatch):
    # A dispatched kanban worker is a single-query (-q) turn; with deny set it never waits on a card.
    configure, cards = gateway_turn
    configure("deny")
    monkeypatch.setenv("HERMES_SINGLE_QUERY_SESSION", "1")
    monkeypatch.setenv("HERMES_KANBAN_TASK", "t_example")

    result, elapsed = _timed_guard()

    assert cards == [], "the kanban worker's escalation was parked on an approval card"
    assert result["approved"] is False
    assert elapsed < 1.0


def test_subagent_guardian_still_approves_routine_work(gateway_turn, monkeypatch):
    configure, cards = gateway_turn
    configure("deny", verdict_value="approve")
    monkeypatch.setenv(DELEGATED_CHILD_ENV_MARKER, "1")

    result, _ = _timed_guard()

    assert result["approved"] is True and result.get("smart_approved") is True
    assert cards == []


def test_default_wait_keeps_the_subagent_card(gateway_turn, monkeypatch):
    configure, cards = gateway_turn
    configure()  # key unset -> shipped default "wait"
    monkeypatch.setenv(DELEGATED_CHILD_ENV_MARKER, "1")

    result, _ = _timed_guard()

    assert len(cards) == 1
    assert result["approved"] is False and result["outcome"] == "timeout"


def test_attended_gateway_turn_keeps_its_card(gateway_turn):
    # Not a delegated child: the owner's own chat/desktop turn is unchanged even with deny set.
    configure, cards = gateway_turn
    configure("deny")
    holder = {}
    worker = threading.Thread(target=lambda: holder.update(result=_timed_guard()[0]))
    worker.start()
    deadline = time.monotonic() + 5
    while not cards and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(cards) == 1, "the attended turn lost its approval card"
    approval_mod.resolve_gateway_approval(SESSION, "once")
    worker.join(timeout=10)
    assert holder["result"]["approved"] is True


@pytest.mark.parametrize("raw, expected", [
    (None, "wait"), ("wait", "wait"), ("deny", "deny"), ("DENY ", "deny"), ("approve", "wait"), (3, "wait"),
])
def test_unattended_escalation_mode_parses_fail_safe(monkeypatch, raw, expected):
    cfg = {} if raw is None else {"unattended_escalation": raw}
    monkeypatch.setattr(approval_context, "_get_approval_config", lambda: cfg)
    assert approval_context._get_unattended_escalation_mode() == expected
