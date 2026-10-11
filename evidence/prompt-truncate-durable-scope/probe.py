"""Post-merge #133748 B4 commit-window probe; AI authored by OpenAI Codex.

kshitijk4poor owns the safety net; JoaoMarcos44 discovered B4 and requested
read/write-window coverage. Kevin's fork459 B1-B3 and admission classifier
ownership remain separate. No production fix or rollback contract is added.
"""

from copy import deepcopy
from pathlib import Path
import socket
import threading
from types import SimpleNamespace

import pytest

from hermes_state import SessionDB
from tui_gateway import server


def _snapshot(db, key):
    rows = db._conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY id", (key,)
    ).fetchall()
    counters = db._conn.execute(
        "SELECT message_count, tool_call_count, rewind_count FROM sessions WHERE id = ?", (key,)
    ).fetchone()
    return [tuple(row) for row in rows], tuple(counters)


@pytest.fixture
def durable_session(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(Path, "home", lambda: home)

    def no_network(*_args, **_kwargs):
        raise AssertionError("Network is forbidden in this durable-scope probe")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    db = SessionDB(db_path=home / "state.db")
    sibling = SessionDB(db_path=home / "state.db")
    key, sid = "durable-scope-session", "durable-scope-runtime"
    db.create_session(key, source="tui")
    for role, content in [("user", "u0"), ("assistant", "a0"),
                          ("user", "u1"), ("assistant", "a1")]:
        db.append_message(key, role, content)
    history = db.get_messages_as_conversation(key, include_row_ids=True)
    assert [m["content"] for m in history] == ["u0", "a0", "u1", "a1"]
    assert all(isinstance(m["_row_id"], int) for m in history)
    session = {
        "agent": SimpleNamespace(), "session_key": key,
        "history": deepcopy(history), "history_lock": threading.Lock(),
        "history_version": 0, "running": False, "attached_images": [],
        "image_counter": 0, "cols": 80, "slash_worker": None,
        "show_reasoning": False, "tool_progress_mode": "all",
    }
    dispatched = []

    def record_compute(rid, runtime_id, live_session, text, *_args, **_kwargs):
        dispatched.append((rid, runtime_id, text, deepcopy(live_session["history"])))

    old_db = server._db
    monkeypatch.setattr(server, "_db", db)
    monkeypatch.setattr(server, "DEEP_TRUNCATE_ENFORCED", True)
    monkeypatch.setattr(server, "_run_after_agent_ready", record_compute)
    monkeypatch.setitem(server._sessions, sid, session)
    try:
        yield db, sibling, key, sid, session, dispatched
    finally:
        if thread := session.get("_run_thread"):
            thread.join(timeout=5)
            assert not thread.is_alive()
        server._release_active_session_slot(session)
        server._sessions.pop(sid, None)
        server._db = old_db
        sibling.close()
        db.close()


@pytest.mark.parametrize("append_in_window", [False, True], ids=["shallow-control", "commit-window"])
def test_prompt_submit_validates_durable_cut_scope(durable_session, monkeypatch, append_in_window):
    db, sibling, key, sid, session, dispatched = durable_session
    warm = deepcopy(session["history"])
    original_replace = db.replace_messages
    witness = []
    post_append_rows = []

    def append_then_replace(*args, **kwargs):
        assert args[0] == key
        assert [m["content"] for m in args[1]] == ["u0", "a0"]
        assert kwargs == {"active_only": True, "archive_dropped": True,
                          "reject_active_turn_lease": True}
        # The real depth gate has already permitted this shallow warm snapshot.
        # No append exists at RPC entry; the second handle commits only HERE.
        assert session["history"] == warm and session["history_version"] == 0
        assert [m["content"] for m in sibling.get_messages_as_conversation(key)] == ["u0", "a0", "u1", "a1"]
        if append_in_window:
            sibling.append_message(key, "user", "u2")
            sibling.append_message(key, "assistant", "a2")
        witness.append(_snapshot(sibling, key))
        post_append_rows.extend(dict(row) for row in sibling._conn.execute(
            "SELECT id, role, content, active, compacted FROM messages WHERE session_id = ? ORDER BY id", (key,)))
        # Reader on the first handle sees independently committed physical rows.
        assert _snapshot(db, key) == witness[-1]
        return original_replace(*args, **kwargs)

    monkeypatch.setattr(db, "replace_messages", append_then_replace)
    response = server.handle_request({"jsonrpc": "2.0", "id": "scope-probe", "method": "prompt.submit",
        "params": {"session_id": sid, "text": "replacement u1",
                   "truncate_before_row_id": warm[2]["_row_id"], "confirm_truncate": True}})
    if thread := session.get("_run_thread"):
        thread.join(timeout=5)
        assert not thread.is_alive()
    assert len(witness) == 1
    physical = [dict(row) for row in sibling._conn.execute(
        "SELECT id, role, content, active, compacted FROM messages WHERE session_id = ? ORDER BY id", (key,))]
    print("DURABLE_SCOPE_RECEIPT", {"append_in_window": append_in_window, "response": response,
          "post_append_rows": post_append_rows, "post_append_counters": witness[0][1], "final_counters": _snapshot(db, key)[1],
          "physical_rows": physical, "warm_history": session["history"],
          "history_version": session["history_version"], "compute_dispatches": len(dispatched)})
    if append_in_window:
        assert response.get("error", {}).get("code") == 4033
        assert dispatched == []
        assert session["history"] == warm and session["history_version"] == 0
        assert _snapshot(db, key) == witness[0]
    else:
        assert response["result"]["status"] == "streaming"
        assert len(dispatched) == 1
        assert session["history"] == warm[:2] and session["history_version"] == 1
        assert [(r["content"], r["active"]) for r in physical] == [
            ("u0", 1), ("a0", 1), ("u1", 0), ("a1", 0), ("replacement u1", 1)]
        assert _snapshot(db, key)[1] == (3, 0, 0)
