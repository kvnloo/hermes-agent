"""Clarify notes and authoritative deadline/replay semantics (#586)."""
import json

import pytest

from tui_gateway import server_requests as sr
from tools.clarify_tool import clarify_tool


@pytest.fixture
def wire(monkeypatch):
    frames, events = [], []
    monkeypatch.setattr(sr, "_open", {})
    monkeypatch.setattr(sr, "_write", frames.append)
    monkeypatch.setattr(sr, "_emit", lambda *event: events.append(event))
    monkeypatch.setattr(sr, "_answerable", lambda sid: True)
    return frames, events


def params():
    return {"questions": [{"qid": "q0", "question": "First?"}, {"qid": "q1", "question": "Second?"}],
            "supports_notes": True, "supports_image_refs": True}


def test_timeout_replays_original_deadline_and_keeps_locked_notes(wire, monkeypatch):
    frames, events = wire
    note = {"text": "context", "image_paths": ["/workspace/image.png"]}
    snapshots = []

    def sent(frame):
        frames.append(frame)
        assert sr.lock_answer(frame["id"], "q0", "A", note) == ["q1"]
        snapshots.extend(sr.open_requests("s1"))

    monkeypatch.setattr(sr, "_write", sent)
    monkeypatch.setattr(sr.time, "time", lambda: 1234.5)
    result = sr.send("clarify", "s1", params(), timeout=0, qids=["q0", "q1"])
    assert frames[0]["params"]["deadline_at"] == 1234500
    assert snapshots[0]["params"]["deadline_at"] == frames[0]["params"]["deadline_at"]
    assert snapshots[0]["params"]["notes"] == {"q0": note}
    assert result == {"answers": {"q0": "A"}, "notes": {"q0": note}, "outcome": "timed_out"}
    assert len(events) == 1 and events[0][2]["reason"] == "timeout"
    assert not sr.resolve_response({"id": frames[0]["id"], "result": {"answers": {"q1": "late"}}})


def test_unlimited_cancel_retains_partial_notes_and_rejects_late_answers(wire, monkeypatch):
    frames, events = wire

    def sent(frame):
        frames.append(frame)
        assert frame["params"]["deadline_at"] is None
        sr.lock_answer(frame["id"], "q0", None, {"text": "skip reason"})
        assert sr.cancel("other") == 0
        assert sr.cancel("s1") == 1

    monkeypatch.setattr(sr, "_write", sent)
    result = sr.send("clarify", "s1", params(), timeout=None, qids=["q0", "q1"])
    assert result["outcome"] == "cancelled"
    assert result["answers"] == {"q0": None}
    assert result["notes"]["q0"]["text"] == "skip reason"
    assert sr.lock_answer(frames[0]["id"], "q1", "late") is None
    assert len(events) == 1


def test_final_response_merges_notes_and_rejects_malformed_or_foreign_qids(wire, monkeypatch):
    note = {"text": "why", "image_paths": ["/workspace/note.png"]}

    def sent(frame):
        rid = frame["id"]
        assert not sr.resolve_response({"id": rid, "result": {"answers": {"foreign": "bad"}}})
        assert not sr.resolve_response({"id": rid, "result": {"notes": {"q0": {"image_paths": [3]}}}})
        sr.lock_answer(rid, "q0", "A", note)
        assert sr.resolve_response({"id": rid, "result": {"answers": {"q1": "B"}}})

    monkeypatch.setattr(sr, "_write", sent)
    result = sr.send("clarify", "s1", params(), timeout=None, qids=["q0", "q1"])
    assert result == {"answers": {"q0": "A", "q1": "B"}, "notes": {"q0": note}, "outcome": "submitted"}


def test_legacy_request_does_not_accept_unsupported_notes(wire, monkeypatch):
    p = params()
    del p["supports_notes"]
    del p["supports_image_refs"]

    def sent(frame):
        with pytest.raises(ValueError, match="does not support"):
            sr.lock_answer(frame["id"], "q0", "A", {"text": "unsupported"})
        assert not sr.resolve_response({"id": frame["id"], "result": {"notes": {"q0": {"text": "bad"}}}})
        assert sr.resolve_response({"id": frame["id"], "result": {"answers": {"q0": "A", "q1": None}}})

    monkeypatch.setattr(sr, "_write", sent)
    assert sr.send("clarify", "s1", p, timeout=None, qids=["q0", "q1"])["outcome"] == "submitted"


def test_notes_and_image_refs_reach_actual_tool_result_without_changing_answer_shape():
    result = json.loads(clarify_tool([{"question": "Pick?", "choices": ["A", "B"]}], callback=lambda _: {
        "answers": {"q0": "A"}, "notes": {"q0": {"text": "why", "image_paths": ["/workspace/note.png"]}},
        "outcome": "submitted"}))
    assert result["responses"][0]["user_response"] == "A"
    assert result["responses"][0]["note"] == "why"
    assert result["responses"][0]["image_paths"] == ["/workspace/note.png"]
