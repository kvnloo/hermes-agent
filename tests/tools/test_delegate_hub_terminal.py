"""Durable child verdicts used by the owned hub (#568), without model calls."""
from types import SimpleNamespace

import pytest

from hermes_state import SessionDB
from tools.delegate_tool_child_run import _ChildRun


@pytest.mark.parametrize("status,reason", [("completed", "completed"), ("interrupted", "interrupted"), ("error", "failed"), ("failed", "failed")])
def test_child_persists_actual_verdict_before_generic_agent_close(tmp_path, status, reason):
    db = SessionDB(tmp_path / "state.db")
    db.create_session("child", source="subagent")
    child = SimpleNamespace(_session_db=db, session_id="child")
    run = _ChildRun(child, None, 0, "task", "sa-child", None)
    try:
        run.persist_terminal(status)
        db.end_session("child", "agent_close")
        assert db.get_session("child")["end_reason"] == reason
    finally:
        db.close()


def test_wait_timeout_does_not_claim_worker_is_terminal(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    db.create_session("child", source="subagent")
    run = _ChildRun(SimpleNamespace(_session_db=db, session_id="child"), None, 0, "task", "sa-child", None)
    try:
        run.persist_terminal("timeout")
        assert db.get_session("child")["ended_at"] is None
    finally:
        db.close()
