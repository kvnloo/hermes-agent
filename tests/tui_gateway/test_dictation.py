"""Review-only native dictation (#553). All captures and STT are fake; no mic opens."""
from __future__ import annotations

import threading
from pathlib import Path

import pytest

from hermes_constants import get_hermes_home
from tui_gateway import dictation, server


@pytest.fixture()
def voice(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from tools import voice_mode
    monkeypatch.setattr(voice_mode, "_import_audio", lambda: pytest.fail("real microphone forbidden"))
    manager = dictation.Dictation(interval=0.01)
    monkeypatch.setattr(dictation, "manager", manager)
    paths, calls, events = [], [], []
    partial = threading.Event()
    session = {"profile_home": str(tmp_path), "transport": server._stdio_transport}
    monkeypatch.setitem(server._sessions, "dictation-test", session)
    monkeypatch.setattr(server, "_voice_mode_enabled", lambda: False)
    monkeypatch.setattr(server, "_wake_owner_snapshot", lambda: (None, ""))

    class Recorder:
        opened = False
        closed = False
        snapshots = 0

        def start(self, on_silence_stop=None):
            self.on_silence_stop = on_silence_stop
            self.opened = True
            calls.append("start")

        def audio(self, name):
            path = tmp_path / name
            path.write_bytes(b"fake audio; never a microphone")
            paths.append(path)
            return str(path)

        def snapshot(self):
            self.snapshots += 1
            return self.audio("partial.wav") if self.snapshots == 1 else None

        def stop(self):
            calls.append("stop")
            return self.audio("final.wav")

        def shutdown(self):
            self.closed = True
            calls.append("shutdown")

    rec = Recorder()
    monkeypatch.setattr(dictation, "create_recorder", lambda: rec)

    def transcribe(path):
        calls.append(Path(path).name)
        assert get_hermes_home() == tmp_path
        if Path(path).name == "final.wav":
            assert rec.closed, "microphone must close before final STT"
        return {"success": True, "transcript": "hello" if Path(path).name == "partial.wav" else "hello world"}

    monkeypatch.setattr(dictation, "transcribe", transcribe)

    def emit(name, sid, payload):
        assert name == "voice.dictation" and sid == "dictation-test"
        server._event_frame(name, sid, payload)  # exercise payload validation too
        events.append(payload)
        if payload.get("text") == "hello":
            partial.set()
        return True

    monkeypatch.setattr(server, "_emit", emit)
    yield manager, rec, events, calls, partial, session
    capture = manager.active
    manager.release(session=session)
    if capture:
        capture.thread.join(5)
        assert not capture.thread.is_alive()
    assert all(not path.exists() for path in paths)
    server._sessions.pop("dictation-test", None)


def rpc(method, **params):
    return server._methods["voice.dictate." + method]("req", {
        "session_id": "dictation-test", "capture_id": "capture-1", **params})


def test_explicit_start_partial_then_stop_final(voice):
    manager, rec, events, calls, partial, _ = voice
    assert not rec.opened and manager.active is None
    assert rpc("start")["result"] == {"capture_id": "capture-1"}
    capture = manager.active
    assert partial.wait(5)
    assert events[0]["state"] == "starting"
    assert events[1]["state"] == "recording"
    assert events[-1]["text"] == "hello" and not events[-1]["final"]
    assert rpc("stop")["result"] == {"capture_id": "capture-1"}
    capture.thread.join(5)
    assert not capture.thread.is_alive()
    assert events[-2]["state"] == "transcribing"
    assert events[-1] == {"capture_id": "capture-1", "state": "idle", "text": "hello world", "final": True}
    assert manager.active is None and rec.closed
    assert calls.index("shutdown") < calls.index("final.wav")


def test_recorder_silence_or_duration_limit_finishes_without_rearming(voice):
    manager, rec, events, calls, partial, _ = voice
    rpc("start")
    capture = manager.active
    assert partial.wait(5)
    rec.on_silence_stop()
    capture.thread.join(5)
    assert events[-1]["final"]
    assert calls.count("start") == 1
    assert manager.active is None and rec.closed


def test_cancel_discards_without_final_transcription(voice):
    manager, rec, events, calls, partial, _ = voice
    rpc("start")
    capture = manager.active
    assert partial.wait(5)
    before = list(events)
    rpc("stop", cancel=True)
    capture.thread.join(5)
    assert events == before
    assert "final.wav" not in calls
    assert rec.closed and manager.active is None
    assert rpc("stop", cancel=True)["result"] == {"capture_id": "capture-1"}


def test_foreign_owner_and_capture_cannot_stop_or_replace(voice, monkeypatch):
    manager, _, _, _, partial, _ = voice
    rpc("start")
    capture = manager.active
    assert partial.wait(5)
    assert "error" in rpc("start", capture_id="second")
    assert "error" in rpc("stop", capture_id="foreign")
    monkeypatch.setattr(server, "_caller_transport", lambda: object())
    assert "error" in rpc("stop", cancel=True)
    assert not capture.stop.is_set()


@pytest.mark.parametrize("operation", ["start", "transcribe"])
def test_backend_failures_are_visible_and_release_microphone(voice, monkeypatch, operation):
    manager, rec, events, _, _, _ = voice
    reached = threading.Event()

    def fail(*args, **kwargs):
        reached.set()
        raise RuntimeError("permission denied" if operation == "start" else "provider unavailable")

    monkeypatch.setattr(rec, "start", fail) if operation == "start" else monkeypatch.setattr(dictation, "transcribe", fail)
    rpc("start")
    capture = manager.active
    assert reached.wait(5)
    if capture:
        capture.thread.join(5)
    assert events[-1]["state"] == "error"
    assert rec.closed and manager.active is None


def test_cancel_during_provider_wait_closes_mic_and_suppresses_late_result(voice, monkeypatch):
    manager, rec, events, _, _, _ = voice
    entered, release = threading.Event(), threading.Event()

    def waiting(path):
        entered.set()
        assert release.wait(5)
        return {"success": True, "transcript": "late"}

    monkeypatch.setattr(dictation, "transcribe", waiting)
    rpc("start")
    capture = manager.active
    assert entered.wait(5)
    try:
        rpc("stop", cancel=True)
        assert rec.closed
    finally:
        release.set()
        capture.thread.join(5)
    assert not any(e.get("text") for e in events)


@pytest.mark.parametrize("kind", ["session", "transport"])
def test_owner_teardown_discards_audio(voice, kind):
    manager, rec, events, _, partial, session = voice
    rpc("start")
    capture = manager.active
    assert partial.wait(5)
    manager.release(**({"session": session} if kind == "session" else {"transport": server._stdio_transport}))
    capture.thread.join(5)
    assert rec.closed
    assert not any(e.get("final") for e in events)


@pytest.mark.parametrize("method,params", [
    ("voice.record", {"action": "start"}),
    ("voice.toggle", {"action": "on"}),
    ("wake.start", {}),
])
def test_other_voice_intents_cannot_open_a_second_microphone(voice, method, params):
    _, _, _, _, partial, _ = voice
    rpc("start")
    assert partial.wait(5)
    response = server._methods[method]("other-mic", params)
    assert response["error"]["code"] == 4019


def test_finish_closes_mic_even_while_a_partial_provider_is_waiting(voice, monkeypatch):
    manager, rec, events, _, _, _ = voice
    entered, release = threading.Event(), threading.Event()

    def waiting(path):
        if Path(path).name == "partial.wav":
            entered.set()
            assert release.wait(5)
        return {"success": True, "transcript": "finished"}

    monkeypatch.setattr(dictation, "transcribe", waiting)
    rpc("start")
    capture = manager.active
    assert entered.wait(5)
    try:
        rpc("stop")
        assert rec.closed
    finally:
        release.set()
        capture.thread.join(5)
    assert events[-1]["final"] and events[-1]["text"] == "finished"


def test_invalid_session_never_constructs_recorder(voice):
    manager, rec, _, _, _, _ = voice
    assert "error" in rpc("start", session_id="missing")
    assert "error" in rpc("start", capture_id=" ")
    assert manager.active is None and not rec.opened
