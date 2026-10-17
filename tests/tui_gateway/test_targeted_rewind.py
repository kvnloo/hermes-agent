"""Targeted renderer rewind (#522), using an isolated persistent session."""
from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from hermes_state import SessionDB
from tui_gateway import server


@pytest.fixture()
def stored_session(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    db = SessionDB(db_path=tmp_path / "state.db")
    monkeypatch.setattr(server, "_tui_model_friction", lambda *_: None)
    monkeypatch.setattr(server, "_db", db)
    db.create_session("rewind-store", source="tui")
    for i in range(4):
        db.append_message("rewind-store", "user", f"question {i + 1}")
        db.append_message("rewind-store", "assistant", f"answer {i + 1}")
    history = db.get_messages_as_conversation("rewind-store", include_row_ids=True)
    session = {
        "agent": SimpleNamespace(_session_messages=list(history), _last_flushed_db_idx=len(history),
                                 _db_flush_scan_prefix=list(history)),
        "attached_images": [], "history": list(history), "history_lock": threading.Lock(),
        "history_version": 0, "running": False, "session_key": "rewind-store",
    }
    monkeypatch.setitem(server._sessions, "rewind-live", session)
    yield db, session, history
    db.close()


def rpc(preview_only=False, **params):
    method = "session.rewind_preview" if preview_only else "session.undo"
    return server._methods[method]("rewind-request", {"session_id": "rewind-live", **params})


@pytest.mark.parametrize("k", range(4))
def test_target_leaves_exactly_the_prefix_before_message_k(stored_session, k):
    db, session, history = stored_session
    target = history[k * 2]["_row_id"]
    preview = rpc(target_message_id=target, preview_only=True)["result"]
    assert preview["removed"] == 0
    assert preview["turns_removed"] == 4 - k
    assert preview["text"] == f"question {k + 1}"
    assert db.get_messages_as_conversation("rewind-store", include_row_ids=True) == history
    response = rpc(target_message_id=target, expected_history_token=preview["history_token"])
    result = response["result"]
    assert result["text"] == f"question {k + 1}"
    assert result["turns_removed"] == 4 - k
    assert result["removed"] == len(history) - k * 2
    assert db.get_messages_as_conversation("rewind-store", include_row_ids=True) == history[:k * 2]
    assert session["history"] == history[:k * 2]
    assert session["agent"]._session_messages == history[:k * 2]
    assert [m["row_id"] for m in result["messages"]] == [m["_row_id"] for m in history[:k * 2]]


def test_no_target_keeps_last_turn_undo(stored_session):
    db, session, history = stored_session
    assert rpc()["result"] == {"removed": 2}
    assert session["history"] == history[:-2]
    assert len(db.get_messages_as_conversation("rewind-store")) == 6


@pytest.mark.parametrize("kind", ["assistant", "missing", "foreign", "media", "host", "misaligned", "merged"])
def test_unsupported_targets_do_not_fall_back_to_last_turn(stored_session, kind):
    db, session, history = stored_session
    target = history[2]["_row_id"]
    if kind == "assistant":
        target = history[3]["_row_id"]
    elif kind == "missing":
        target = 999999
    elif kind == "foreign":
        db.create_session("other-session", source="tui")
        target = db.append_message("other-session", "user", "not mine")
    elif kind == "media":
        content = [{"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}]
        db.set_user_message_content("rewind-store", target, content)
        session["history"][2]["content"] = content
    elif kind == "host":
        session["_compute_host_active"] = True
    elif kind == "misaligned":
        session["history"][2] = {"role": "user", "content": "changed"}
    elif kind == "merged":
        # A row merged into a preceding unanswered ask is not independently rewindable.
        db._conn.execute("DELETE FROM messages WHERE id = ?", (history[1]["_row_id"],))
        db._conn.commit()
    before = db.get_messages_as_conversation("rewind-store", include_row_ids=True)
    for preview in (True, False):
        assert "error" in rpc(target_message_id=target, preview_only=preview)
        assert db.get_messages_as_conversation("rewind-store", include_row_ids=True) == before


def test_changed_history_requires_a_new_confirmation(stored_session):
    db, session, history = stored_session
    target = history[2]["_row_id"]
    token = rpc(target_message_id=target, preview_only=True)["result"]["history_token"]
    db.append_message("rewind-store", "user", "a new turn")
    session["history"] = db.get_messages_as_conversation("rewind-store", include_row_ids=True)
    before = list(session["history"])
    response = rpc(target_message_id=target, expected_history_token=token)
    assert response["error"]["code"] == 4009
    assert session["history"] == before
    assert db.get_messages_as_conversation("rewind-store", include_row_ids=True) == before


def test_exact_row_identity_is_pinned_even_if_ordinal_is_reused(stored_session, monkeypatch):
    db, session, history = stored_session
    target = history[2]["_row_id"]
    original = server._rewind_active_session_history

    def race(*args, **kwargs):
        # Same turn count and same text, different durable row: must not rewind the replacement.
        db._conn.execute("DELETE FROM messages WHERE id = ?", (target,))
        db._conn.commit()
        db.append_message("rewind-store", "user", "question 2")
        session["history"] = db.get_messages_as_conversation("rewind-store", include_row_ids=True, repair_alternation=True)
        return original(*args, **kwargs)

    monkeypatch.setattr(server, "_rewind_active_session_history", race)
    assert "error" in rpc(target_message_id=target)
    assert len(db.get_messages_as_conversation("rewind-store")) == 8


def test_durable_rewind_refuses_a_different_row_at_the_selected_ordinal(stored_session):
    db, _session, history = stored_session
    with pytest.raises(ValueError, match="identity changed"):
        db.rewind_user_turn("rewind-store", 1, target_message_id=history[0]["_row_id"])
    assert db.get_messages_as_conversation("rewind-store", include_row_ids=True) == history


@pytest.mark.parametrize("invalid", [True, 0, -1, "20"])
def test_target_ids_are_validated_at_the_rpc_boundary(stored_session, invalid):
    db, _session, history = stored_session
    response = server.handle_request({
        "id": "invalid-target", "method": "session.undo",
        "params": {"session_id": "rewind-live", "target_message_id": invalid},
    })
    assert response["error"]["code"] == 4000
    assert db.get_messages_as_conversation("rewind-store", include_row_ids=True) == history


def test_running_rejects_preview_and_write(stored_session):
    db, session, history = stored_session
    session["running"] = True
    for preview in (True, False):
        assert rpc(target_message_id=history[2]["_row_id"], preview_only=preview)["error"]["code"] == 4009
    assert db.get_messages_as_conversation("rewind-store", include_row_ids=True) == history
