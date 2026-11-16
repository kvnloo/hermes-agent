"""Regression for NousResearch/hermes-agent#156677: every active unattended policy applies."""

import tools.approval as approval
from gateway.session_context import clear_session_vars, set_session_vars
from tools import approval_context


def test_cron_deny_survives_single_query_approve(monkeypatch):
    monkeypatch.setattr(approval, "_YOLO_MODE_FROZEN", False)
    monkeypatch.setattr(approval_context, "_get_approval_mode", lambda: "manual")
    monkeypatch.setattr(approval_context, "_get_single_query_approval_mode", lambda: "approve")
    monkeypatch.setattr(approval_context, "_get_cron_approval_mode", lambda: "deny")
    monkeypatch.setenv("HERMES_SINGLE_QUERY_SESSION", "1")

    tokens = set_session_vars(cron_session="1")
    try:
        result = approval.check_execute_code_guard("print('ok')", "local")
    finally:
        clear_session_vars(tokens)

    assert result["approved"] is False
    assert result["outcome"] == "blocked"
    assert "approvals.cron_mode" in result["message"]
