"""Structured tool failure is part of the completion contract; renderers must not parse result prose."""

import json

import tui_gateway.server as server


def _capture_completion(monkeypatch, result: str):
    sid = "tool-failure-contract"
    events = []
    monkeypatch.setitem(
        server._sessions,
        sid,
        {
            "agent": None,
            "edit_snapshots": {},
            "tool_started_at": {},
            "tool_progress_mode": "full",
        },
    )
    monkeypatch.setattr(server, "_tool_progress_enabled", lambda _sid: True)
    monkeypatch.setattr(server, "_tool_lifecycle_required_for_ui", lambda _name: False)
    monkeypatch.setattr(
        server,
        "_emit",
        lambda event, event_sid, payload=None: events.append((event, event_sid, payload)),
    )

    server._on_tool_complete(sid, "call-1", "terminal", {}, result)

    assert len(events) == 1
    event, event_sid, payload = events[0]
    assert event == "tool.complete"
    assert event_sid == sid
    return payload


def test_tool_complete_marks_nonzero_exit_as_failed(monkeypatch):
    payload = _capture_completion(
        monkeypatch,
        json.dumps({"output": "permission denied", "exit_code": 1, "error": None}),
    )

    assert payload["failed"] is True


def test_tool_complete_marks_success_false_as_failed(monkeypatch):
    payload = _capture_completion(monkeypatch, json.dumps({"success": False, "error": "nope"}))

    assert payload["failed"] is True


def test_tool_complete_marks_success_as_not_failed(monkeypatch):
    payload = _capture_completion(monkeypatch, json.dumps({"success": True, "output": "ok"}))

    assert payload["failed"] is False
