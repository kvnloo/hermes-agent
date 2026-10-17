"""Explicit confirmed image paths bind only this draft's attachments (#517)."""

import base64
import threading

import pytest

from hermes_state import SessionDB
from tui_gateway import server

# Real 1x1 PNG, shared with the frontend image-paste fixture.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aVmQAAAAASUVORK5CYII=")


@pytest.fixture
def session(monkeypatch, tmp_path):
    db = SessionDB(db_path=tmp_path / "state.db")
    monkeypatch.setattr(server, "_get_db", lambda: db)
    monkeypatch.setattr(server, "_schedule_agent_build", lambda _sid: None)
    monkeypatch.setattr(server, "_schedule_session_cap_enforcement", lambda: None)
    monkeypatch.setattr(server, "_register_session_cwd", lambda _session: None)
    response = server.handle_request({"id": "c", "method": "session.create", "params": {"cols": 96}})
    assert "result" in response, response
    sid = response["result"]["session_id"]
    record = server._sessions[sid]
    record["profile_home"] = str(tmp_path)
    monkeypatch.setattr(server, "_start_agent_build", lambda *args: None)
    monkeypatch.setattr(server, "_restart_completed_failed_agent_build", lambda *args: False)
    yield sid, record
    server._sessions.pop(sid, None)
    db.close()


def call(method, sid, **params):
    return server.handle_request({"id": "p", "method": method, "params": {"session_id": sid, **params}})


def attach(sid):
    response = call("image.attach_bytes", sid, content_base64=base64.b64encode(PNG).decode(), filename="image.png")
    assert response["result"]["attached"], response
    return response["result"]["path"]


def test_submit_claims_only_confirmed_selected_images_before_deferred_worker(session, monkeypatch):
    sid, record = session
    selected, later = attach(sid), attach(sid)
    captured = []
    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def wait_for_agent(*args):
        entered.set()
        assert release.wait(5)

    def run(*args, **kwargs):
        captured.append(kwargs["image_paths"])
        finished.set()

    monkeypatch.setattr(server, "_wait_agent_for_prompt", wait_for_agent)
    monkeypatch.setattr(server, "_run_prompt_submit", run)
    try:
        response = call("prompt.submit", sid, text="describe", image_paths=[selected])
        assert response["result"]["status"] == "streaming", response
        assert entered.wait(5)
        assert record["attached_images"] == [later]
        # Even an upload after the acknowledgement belongs only to the next draft.
        newest = attach(sid)
        release.set()
        assert finished.wait(5)
        assert captured == [[selected]]
        assert record["attached_images"] == [later, newest]
    finally:
        release.set()
        record.get("_run_thread").join(5)


def test_empty_selection_and_busy_queue_do_not_consume_the_next_drafts_images(session, monkeypatch):
    sid, record = session
    waiting = attach(sid)
    record["running"] = True
    monkeypatch.setattr(server, "_load_busy_input_mode", lambda: "queue")
    response = call("prompt.submit", sid, text="text only", image_paths=[], queued=True)
    assert response["result"]["status"] == "queued", response
    assert record["attached_images"] == [waiting]
    assert record["queued_prompt"]["image_paths"] == []
    dispatched = []
    monkeypatch.setattr(server, "_run_prompt_submit", lambda *args, **kwargs: dispatched.append(kwargs))
    monkeypatch.setattr(server, "_session_uses_compute_host", lambda *args: False)
    record["running"] = False
    assert server._drain_queued_prompt("drain", sid, record)
    assert dispatched[0]["image_paths"] == []
    assert record["attached_images"] == [waiting]


def test_busy_image_submit_snapshots_only_the_selected_paths(session, monkeypatch):
    sid, record = session
    selected, waiting = attach(sid), attach(sid)
    record["running"] = True
    monkeypatch.setattr(server, "_load_busy_input_mode", lambda: "queue")
    response = call("prompt.submit", sid, text="image follow-up", image_paths=[selected], queued=True)
    assert response["result"]["status"] == "queued", response
    assert record["attached_images"] == [waiting]
    assert record["queued_prompt"]["image_paths"] == [selected]


@pytest.mark.parametrize("selection", [["/unconfirmed.png"], ["/removed.png"], ["/same.png", "/same.png"], "wrong type", [12]])
def test_invalid_image_id_selection_refuses_before_turn_or_history_mutation(session, selection):
    sid, record = session
    before = list(record["history"])
    response = call("prompt.submit", sid, text="must not send", image_paths=selection)
    assert "error" in response, response
    assert record["history"] == before
    assert not record["running"]


def test_detached_confirmed_image_is_no_longer_admissible(session):
    sid, record = session
    path = attach(sid)
    assert call("image.detach", sid, path=path)["result"]["detached"]
    response = call("prompt.submit", sid, text="do not send removed image", image_paths=[path])
    assert response["error"]["code"] == 4016
    assert not record["running"]
