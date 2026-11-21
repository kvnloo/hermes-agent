"""A finite turn (kanban worker, ``chat -q`` over the daemon) under ``approvals.mode: smart`` takes
the same tiered gate as an interactive session when its session registered an approval notifier:
the guardian approves routine flagged commands, and an escalation parks in the session (paging the
owner through ``pre_approval_request``) instead of the instant single-query refusal. Without a
notifier nobody can answer, so the deterministic ``approvals.single_query_mode`` path stays."""

import pytest

import tools.approval as approval_mod
from gateway.session_finite import finite_turn_scope
from tools import approval_context, approval_smart

SESSION = "test-single-query-tiered"
GATED = "ssh groot systemctl --user disable --now hermes-upstream.timer"


@pytest.fixture
def finite_turn(monkeypatch):
    monkeypatch.setattr(approval_mod, "_YOLO_MODE_FROZEN", False)
    for var in ("HERMES_CRON_SESSION", "HERMES_SESSION_PLATFORM", "HERMES_INTERACTIVE",
                "HERMES_SINGLE_QUERY_SESSION", "HERMES_YOLO_MODE"):
        monkeypatch.delenv(var, raising=False)
    # What a gateway-owned managed worker runs with.
    monkeypatch.setenv("HERMES_GATEWAY_SESSION", "1")
    monkeypatch.setenv("HERMES_EXEC_ASK", "1")
    monkeypatch.setenv("HERMES_SESSION_KEY", SESSION)
    monkeypatch.setattr(approval_context, "_get_approval_mode", lambda: "smart")
    monkeypatch.setattr(approval_context, "_get_single_query_approval_mode", lambda: "deny")
    hooks = []
    monkeypatch.setattr(approval_context, "_fire_approval_hook",
                        lambda name, **kw: hooks.append((name, kw.get("surface"), kw.get("choice"))))
    approval_mod.clear_session(SESSION)
    with finite_turn_scope(True):
        yield hooks
    approval_mod.unregister_gateway_notify(SESSION)
    approval_mod.clear_session(SESSION)


def _guardian(monkeypatch, verdict):
    monkeypatch.setattr(approval_smart, "_smart_approve", lambda *_: verdict)


def test_routine_flagged_command_runs_without_a_prompt(finite_turn, monkeypatch):
    _guardian(monkeypatch, "approve")
    approval_mod.register_gateway_notify(SESSION, lambda data: pytest.fail("routine work prompted the owner"))
    result = approval_mod.check_all_command_guards("rm -rf ./build", "local")
    assert result["approved"] is True


def test_gated_command_pages_the_owner_and_runs_once_approved(finite_turn, monkeypatch):
    _guardian(monkeypatch, "escalate")
    cards = []

    def notify(data):
        cards.append(data["command"])
        approval_mod.resolve_gateway_approval(SESSION, "once")

    approval_mod.register_gateway_notify(SESSION, notify)
    result = approval_mod.check_all_command_guards(GATED, "local")
    assert cards == [GATED]
    assert ("pre_approval_request", "gateway", None) in finite_turn
    assert result["approved"] is True and result.get("user_approved") is True


def test_gated_command_denied_by_owner_stays_blocked(finite_turn, monkeypatch):
    _guardian(monkeypatch, "escalate")
    approval_mod.register_gateway_notify(SESSION, lambda data: approval_mod.resolve_gateway_approval(SESSION, "deny"))
    result = approval_mod.check_all_command_guards(GATED, "local")
    assert result["approved"] is False and "denied by user" in result["message"]


def test_without_a_notifier_the_single_query_refusal_stays(finite_turn, monkeypatch):
    _guardian(monkeypatch, "approve")
    result = approval_mod.check_all_command_guards(GATED, "local")
    assert result["approved"] is False and "approvals.single_query_mode" in result["message"]


def test_manual_mode_keeps_the_single_query_refusal(finite_turn, monkeypatch):
    monkeypatch.setattr(approval_context, "_get_approval_mode", lambda: "manual")
    approval_mod.register_gateway_notify(SESSION, lambda data: pytest.fail("manual-mode -q prompted"))
    result = approval_mod.check_all_command_guards(GATED, "local")
    assert result["approved"] is False and "approvals.single_query_mode" in result["message"]
