"""Durable-only Tern forks (#556), with no model calls or real pane launchers."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import os
import threading
from types import SimpleNamespace

import pytest

from hermes_state import SessionDB
from tui_gateway import server


@pytest.fixture()
def fork_parent(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    db = SessionDB(db_path=tmp_path / "state.db")
    monkeypatch.setattr(server, "_db", db)
    monkeypatch.setattr(server, "_make_agent", lambda *a, **kw: pytest.fail("Fork must not build an agent"))
    db.create_session("fork-parent", source="tui", model="fixture-model", cwd=str(tmp_path),
                      profile_name="default", system_prompt="exact cached system prompt",
                      model_config={"provider": "fixture", "service_tier": "normal"})
    db.append_messages_batch("fork-parent", [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": "tool-1", "type": "function", "function": {"name": "read", "arguments": "{}"}}],
         "reasoning": "thinking bytes"},
        {"role": "tool", "content": "file bytes", "tool_name": "read", "tool_call_id": "tool-1"},
        {"role": "assistant", "content": "first answer", "api_content": '{"verbatim":"wire bytes"}'},
        {"role": "user", "content": "second question"},
        {"role": "assistant", "content": "second answer"},
    ])
    db.set_session_title("fork-parent", "An original conversation")
    history = db.get_messages_as_conversation("fork-parent", include_row_ids=True)
    session = {
        "agent": None, "model_override": {"model": "fixture-model", "provider": "fixture"},
        "history": deepcopy(history), "history_lock": threading.Lock(),
        "running": False, "session_key": "fork-parent", "source": "tui", "cwd": str(tmp_path),
    }
    monkeypatch.setitem(server._sessions, "fork-live", session)
    yield db, session, history
    db.close()


def fork(**params):
    return server._methods["session.fork"]("fork-request", {"session_id": "fork-live", **params})


def session_ids(db):
    return [row[0] for row in db._conn.execute("SELECT id FROM sessions ORDER BY id").fetchall()]


def payloads(history):
    return [{k: v for k, v in message.items() if k not in {"_row_id", "_db_persisted"}} for message in history]


@pytest.mark.parametrize("target_index", [None, 0, 3, 5])
def test_fork_copies_exact_prefix_and_parent_is_unchanged(fork_parent, target_index):
    db, session, history = fork_parent
    parent_row = db.get_session("fork-parent")
    warm = deepcopy(session["history"])
    sessions_before = set(server._sessions)
    params = {} if target_index is None else {"target_message_id": history[target_index]["_row_id"]}
    result = fork(**params)["result"]
    key = result["session_id"]
    child = db.get_session(key)
    expected = history if target_index is None else history[:target_index + 1]
    assert key != "fork-parent"
    assert result["parent"] == "fork-parent"
    assert result["message_count"] == len(expected)
    assert payloads(db.get_messages_as_conversation(key, include_row_ids=True)) == payloads(expected)
    assert child["parent_session_id"] == "fork-parent"
    assert child["system_prompt"] == "exact cached system prompt"
    assert child["profile_name"] == result["profile"]
    assert child["cwd"] == parent_row["cwd"]
    assert db.get_session("fork-parent") == parent_row
    assert db.get_messages_as_conversation("fork-parent", include_row_ids=True) == history
    assert session["history"] == warm
    assert set(server._sessions) == sessions_before


def test_fork_preserves_tool_pairing_reasoning_sidecar_and_can_be_resumed(fork_parent):
    db, _session, history = fork_parent
    key = fork()["result"]["session_id"]
    model_history, display_history = db.get_resume_conversations(key)
    assert [m["role"] for m in model_history] == [m["role"] for m in history]
    assert model_history[1]["tool_calls"] == history[1]["tool_calls"]
    assert model_history[1]["reasoning"] == "thinking bytes"
    assert model_history[2]["tool_call_id"] == "tool-1"
    assert model_history[3]["api_content"] == history[3]["api_content"]
    assert len(display_history) == len(history)  # branch boundary must not prepend the parent again
    db.append_message(key, "user", "fork-only prompt")
    assert db.get_messages_as_conversation("fork-parent", include_row_ids=True) == history


@pytest.mark.parametrize("flag", ["running", "_manual_compress_active", "_compute_host_active", "resume_hydrating"])
def test_unstable_or_remote_history_refuses_without_a_child(fork_parent, flag):
    db, session, history = fork_parent
    before = session_ids(db)
    session[flag] = True
    assert fork()["error"]["code"] == 4009
    assert session_ids(db) == before
    assert db.get_messages_as_conversation("fork-parent", include_row_ids=True) == history


def test_foreign_or_missing_target_is_not_a_whole_history_fallback(fork_parent):
    db, _session, history = fork_parent
    db.create_session("foreign", source="tui")
    target = db.append_message("foreign", "user", "not in this conversation")
    before = session_ids(db)
    for row_id in (target, 999999, history[1]["_row_id"], history[2]["_row_id"]):
        assert fork(target_message_id=row_id)["error"]["code"] == 4008
    assert session_ids(db) == before
    assert db.get_messages_as_conversation("fork-parent", include_row_ids=True) == history


@pytest.mark.parametrize("invalid", [True, 0, -1, "1"])
def test_target_boundary_rejects_invalid_ids(fork_parent, invalid):
    response = server.handle_request({"id": "bad-fork", "method": "session.fork",
                                      "params": {"session_id": "fork-live", "target_message_id": invalid}})
    assert response["error"]["code"] == 4000


def test_successful_fork_reply_is_valid_on_the_gateway_dispatch_boundary(fork_parent):
    db, _session, history = fork_parent
    response = server.handle_request({"id": "wire-fork", "method": "session.fork",
                                      "params": {"session_id": "fork-live", "target_message_id": history[3]["_row_id"]}})
    result = response["result"]
    assert result["message_count"] == 4
    assert db.get_session(result["session_id"]) is not None
    assert result["parent"] == "fork-parent"


def test_copy_failure_cleans_up_only_the_child(fork_parent, monkeypatch):
    db, _session, history = fork_parent
    parent_row = db.get_session("fork-parent")
    before = session_ids(db)
    monkeypatch.setattr(db, "append_messages_batch", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("copy failed")))
    assert fork()["error"]["code"] == 5008
    assert session_ids(db) == before
    assert db.get_session("fork-parent") == parent_row
    assert db.get_messages_as_conversation("fork-parent", include_row_ids=True) == history


def test_fork_preserves_current_runtime_route_and_tool_pin(fork_parent):
    db, session, _history = fork_parent
    db.update_session_tool_names("fork-parent", ["read", "bash"])
    parent_pin = db.get_session("fork-parent")["tool_names"]
    session["agent"] = SimpleNamespace(session_id="fork-parent", model="changed-model", provider="openrouter",
                                       base_url="https://openrouter.ai/api/v1", api_mode="chat_completions")
    key = fork()["result"]["session_id"]
    child = db.get_session(key)
    assert child["model"] == "changed-model"
    assert json.loads(child["model_config"])["provider"] == "openrouter"
    assert child["tool_names"] == parent_pin


def test_secondary_profile_fork_never_writes_the_launch_database(fork_parent, tmp_path, monkeypatch):
    launch_db, _session, _history = fork_parent
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    secondary = tmp_path / ".hermes" / "profiles" / "secondary"
    secondary.mkdir(parents=True)
    db = SessionDB(db_path=secondary / "state.db")
    try:
        db.create_session("secondary-parent", source="tui", model="fixture", profile_name="secondary")
        db.append_message("secondary-parent", "user", "secondary prompt")
        session = {"agent": None, "model_override": {"model": "fixture"}, "profile_home": str(secondary),
                   "source": "tui", "running": False, "session_key": "secondary-parent",
                   "history": db.get_messages_as_conversation("secondary-parent"), "history_lock": threading.Lock()}
        monkeypatch.setitem(server._sessions, "secondary-live", session)
        before_home = os.environ["HERMES_HOME"]
        result = server._methods["session.fork"]("secondary", {"session_id": "secondary-live"})["result"]
        assert result["profile"] == "secondary"
        assert db.get_session(result["session_id"])["profile_name"] == "secondary"
        assert db.get_messages_as_conversation(result["session_id"])[0]["content"] == "secondary prompt"
        assert launch_db.get_session(result["session_id"]) is None
        assert os.environ["HERMES_HOME"] == before_home
    finally:
        db.close()
