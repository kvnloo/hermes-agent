"""Owned hub and canonical child transcript contracts (#568)."""
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def hub(tmp_path, monkeypatch):
    from hermes_state import SessionDB
    from tui_gateway import server
    from tools import delegate_tool_registry as registry

    db = SessionDB(tmp_path / "state.db")
    db.create_session("root", source="tui")
    db.create_session("child-session", source="subagent", parent_session_id="root",
                      model_config={"_delegate_from": "root", "_subagent_id": "child", "_delegate_goal": "Owned task"})
    db.create_session("nested", source="subagent", parent_session_id="child-session")
    db.create_session("other", source="tui")
    db.create_session("foreign", source="subagent", parent_session_id="other")
    db.create_session("branch", source="tui", parent_session_id="root",
                      model_config={"_branched_from": "root"})
    transport = SimpleNamespace(write=lambda frame: True)
    owner = {"session_key": "root", "history": [], "transport": transport, "profile_home": tmp_path}
    child = SimpleNamespace(session_id="child-session", steer=Mock(return_value=True), interrupt=Mock(), _delegate_role="leaf")
    record = {"subagent_id": "child", "owner_session_id": "ui", "owner_session_record": owner,
              "owner_transport": transport, "agent": child, "status": "running", "accepting_steer": True, "goal": "Owned task"}
    monkeypatch.setattr(server, "_sessions", {"ui": owner})
    monkeypatch.setattr(server, "_get_db", lambda: db)
    monkeypatch.setattr(registry, "_active_subagents", {"child": record})
    monkeypatch.setattr(registry, "_active_subagents_lock", threading.Lock())

    def call(method, *, via=transport, **params):
        token = server.bind_transport(via)
        try:
            return server.handle_request({"id": 1, "method": method, "params": {"session_id": "ui", **params}})
        finally:
            server.reset_transport(token)

    yield call, db, child, record, owner, registry, server
    db.close()


def test_roster_has_explicit_capabilities_nested_lineage_and_no_foreign_or_branch(hub):
    call, _, _, record, _, registry, _ = hub
    rows = {row["id"]: row for row in call("subagent.hub")["result"]["agents"]}
    assert set(rows) == {"child-session", "nested"}
    assert rows["child-session"]["actions"] == {"send": True, "stop": True, "transcript": True}
    assert rows["nested"]["parent_id"] == "child-session"
    assert rows["nested"]["status"] == "unknown"
    assert rows["nested"]["actions"] == {"send": False, "stop": False, "transcript": True}
    record["status"] = "idle"
    assert call("subagent.hub")["result"]["agents"][0]["actions"]["send"]
    registry._active_subagents.clear()
    rows = call("subagent.hub")["result"]["agents"]
    assert not any(row["actions"]["send"] or row["actions"]["stop"] for row in rows)
    assert "retry" not in str(rows)


def test_full_paged_transcript_equals_running_and_stored_with_tools_and_large_text(hub):
    call, db, _, _, _, registry, _ = hub
    db.append_message("child-session", "user", "goal")
    db.append_message("child-session", "assistant", "x" * 22000,
                      tool_calls=[{"id": "read-1", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}])
    db.append_message("child-session", "tool", "full tool result", tool_call_id="read-1", tool_name="read_file")
    first = call("subagent.transcript", child_session_id="child-session", limit=2)["result"]
    assert len(first["messages"]) == 2 and first["next_offset"] == 2
    assert first["messages"][1]["content"] == "x" * 22000
    assert first["messages"][1]["tool_calls"][0]["function"]["name"] == "read_file"
    second = call("subagent.transcript", child_session_id="child-session", limit=2, offset=2)["result"]
    assert second["messages"][0]["content"] == "full tool result" and second["next_offset"] is None
    registry._active_subagents.clear()
    db.end_session("child-session", "completed")
    assert call("subagent.transcript", child_session_id="child-session", limit=2)["result"] == first
    rows = call("subagent.hub")["result"]["agents"]
    assert next(row for row in rows if row["id"] == "child-session")["status"] == "completed"


@pytest.mark.parametrize("target", ["foreign", "root", "branch", "task-0", "missing"])
def test_stale_foreign_and_task_index_ids_cannot_read_transcripts(hub, target):
    call, *_ = hub
    assert "error" in call("subagent.transcript", child_session_id=target)


def test_controls_require_exact_transport_generation_child_and_supported_action(hub):
    call, _, child, record, owner, registry, server = hub
    params = {"subagent_id": "child", "child_session_id": "child-session", "text": "change course"}
    assert call("subagent.message", **params)["result"] == {"status": "queued"}
    child.steer.assert_called_once_with("change course")
    child.steer.reset_mock()
    assert "error" in call("subagent.message", via=SimpleNamespace(write=lambda frame: True), **params)
    assert call("subagent.message", **{**params, "child_session_id": "other"})["result"]["status"] == "rejected"
    server._sessions["ui"] = {**owner}
    assert call("subagent.message", **params)["result"]["status"] == "rejected"
    server._sessions["ui"] = owner
    for role, status, accepting in [("advisor", "running", True), ("leaf", "aborted", True),
                                     ("leaf", "completed", True), ("leaf", "unknown", True), ("leaf", "running", False)]:
        child._delegate_role, record["status"], record["accepting_steer"] = role, status, accepting
        assert call("subagent.message", **params)["result"]["status"] == "rejected"
    registry._active_subagents.clear()
    assert call("subagent.message", **params)["result"]["status"] == "rejected"
    child.steer.assert_not_called()


def test_cooperative_stop_is_cancel_requested_not_terminal(hub):
    call, _, child, record, *_ = hub
    result = call("subagent.stop", subagent_id="child", child_session_id="child-session")
    assert result["result"] == {"status": "cancel_requested"}
    child.interrupt.assert_called_once()
    row = next(row for row in call("subagent.hub")["result"]["agents"] if row["id"] == "child-session")
    assert row["status"] == "cancel_requested"
    assert not row["actions"]["send"] and not row["actions"]["stop"]
    record["cancel_requested"] = False
    record["status"] = "cancelled"
    assert call("subagent.stop", subagent_id="child", child_session_id="child-session")["result"]["status"] == "rejected"


@pytest.mark.parametrize("extra", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": True}, {"limit": "2"}])
def test_boundary_validation_runs_through_dispatch(hub, extra):
    call, *_ = hub
    assert "error" in call("subagent.transcript", child_session_id="child-session", **extra)


def test_message_uses_real_agent_steering_queue_and_final_boundary_drain(hub):
    from run_agent import AIAgent
    from tools.delegate_tool_registry import _close_subagent_steering

    call, _, _, record, *_ = hub
    child = object.__new__(AIAgent)
    child.session_id = "child-session"
    child._pending_steer = None
    child._pending_steer_lock = threading.Lock()
    record["agent"] = child
    assert call("subagent.message", subagent_id="child", child_session_id="child-session", text="actual queued text")["result"]["status"] == "queued"
    assert _close_subagent_steering("child", child) == "actual queued text"
    assert call("subagent.message", subagent_id="child", child_session_id="child-session", text="too late")["result"]["status"] == "rejected"


def test_read_only_lineage_visibility_does_not_grant_control(hub):
    call, _, _, record, owner, *_ = hub
    owner["agent"] = SimpleNamespace(session_id="root")
    record["owner_agent_session_id"] = "root"
    record["owner_session_record"] = {"transport": object()}
    row = next(row for row in call("subagent.hub")["result"]["agents"] if row["id"] == "child-session")
    assert row["actions"] == {"send": False, "stop": False, "transcript": True}
    assert call("subagent.message", subagent_id="child", child_session_id="child-session", text="not authorized")["result"]["status"] == "rejected"


def test_bad_message_types_and_blank_are_rejected_without_delivery(hub):
    call, _, child, *_ = hub
    for text in (42, "", "   ", "x" * 32001):
        assert "error" in call("subagent.message", subagent_id="child", child_session_id="child-session", text=text)
    child.steer.assert_not_called()
