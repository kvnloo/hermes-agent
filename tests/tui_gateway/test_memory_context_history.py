"""Regression for NousResearch/hermes-agent#149933: malformed recall stays off history UI."""

from __future__ import annotations

import threading

import pytest

from hermes_state import SessionDB
from tui_gateway import server
from tui_gateway.session_history import _history_to_messages


@pytest.mark.parametrize(
    ("raw", "visible"),
    [
        (
            "Useful answer.\n\n<memory-context>\n[System note: internal]\nprivate recall",
            "Useful answer.\n\n",
        ),
        (
            "Useful answer.\n<memory-context>\nprivate recall\n</memory-context>\nFollow-up",
            "Useful answer.\n\nFollow-up",
        ),
        (
            "Document the literal `<memory-context>` tag inline.",
            "Document the literal `<memory-context>` tag inline.",
        ),
    ],
)
def test_history_projection_scrubs_only_assistant_memory_blocks(raw, visible):
    stored = {"role": "assistant", "active": 1, "_row_id": 23, "content": raw, "api_content": raw}
    result = _history_to_messages([stored])
    assert len(result) == 1
    assert result[0]["text"] == visible
    assert result[0]["row_id"] == 23
    assert stored["content"] == raw
    assert stored["api_content"] == raw


def test_desktop_session_history_hydration_drops_unterminated_fence(tmp_path):
    raw = "Completed answer.\n\n<memory-context>\n[System note: private]\nsecret recall"
    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session("stored-session", source="desktop")
    db.append_message("stored-session", "assistant", raw)
    previous_db = server._db
    server._db = db
    server._sessions["memory-history-repro"] = {
        "session_key": "stored-session",
        "history": [],
        "history_lock": threading.Lock(),
        "running": False,
        "agent": None,
    }
    try:
        response = server.handle_request(
            {"id": "1", "method": "session.history", "params": {"session_id": "memory-history-repro"}}
        )
    finally:
        server._sessions.pop("memory-history-repro", None)
        server._db = previous_db
        db.close()

    assert "error" not in response
    assert response["result"]["count"] == 1
    assert response["result"]["messages"][0]["role"] == "assistant"
    assert response["result"]["messages"][0]["text"] == "Completed answer.\n\n"
