"""Opt-in live voice (#581): fake capture/STT/TTS only, no audio devices/providers."""
from __future__ import annotations

import queue
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from hermes_constants import get_hermes_home
from tui_gateway import live_voice, server


@pytest.fixture()
def voice(tmp_path, monkeypatch):
    from tools import voice_mode
    monkeypatch.setattr(voice_mode, "_import_audio", lambda: pytest.fail("real audio forbidden"))
    manager = live_voice.LiveVoice()
    monkeypatch.setattr(live_voice, "manager", manager)
    monkeypatch.setattr(live_voice, "silence", Mock())
    monkeypatch.setattr(server, "_voice_mode_enabled", lambda: False)
    monkeypatch.setattr(server, "_wake_owner_snapshot", lambda: (None, ""))
    monkeypatch.setattr(server, "_fd_tts_pending", lambda: False)
    session = {"profile_home": str(tmp_path), "transport": server._stdio_transport, "agent": Mock(), "running": False}
    monkeypatch.setitem(server._sessions, "live-test", session)
    events = queue.Queue()
    opened = queue.Queue()
    commands = queue.Queue()
    submitted = queue.Queue()
    idle = threading.Event()
    streams = []

    def emit(event, sid, payload=None):
        if event == "voice.live":
            server._event_frame(event, sid, payload)
            events.put(payload)
            if payload["phase"] == "idle":
                idle.set()
        return True
    monkeypatch.setattr(server, "_emit", emit)

    def listen(stop, playing, trigger, on_open):
        stream = SimpleNamespace(abort=Mock(), close=Mock())
        streams.append(stream)
        on_open(stream)
        opened.put((trigger, stream))
        command = commands.get(timeout=5)
        if command is None or stop():
            return None
        trigger("playback" if playing() else "generation")
        path = tmp_path / f"utterance-{len(streams)}.wav"
        path.write_bytes(b"fake PCM")
        return str(path)
    monkeypatch.setattr(live_voice, "listen", listen)

    def transcribe(path):
        assert get_hermes_home() == tmp_path
        return "spoken request"
    monkeypatch.setattr(live_voice, "transcribe", transcribe)

    def submit(rid, params):
        submitted.put(params)
        manager.event("message.start", "live-test", None)
        return {"result": {"status": "started"}}
    monkeypatch.setitem(server._methods, "prompt.submit", submit)

    fixture = SimpleNamespace(manager=manager, session=session, events=events, opened=opened,
                              commands=commands, submitted=submitted, idle=idle, streams=streams)
    yield fixture
    manager.release(session=session)
    commands.put(None)
    if manager.active:
        assert idle.wait(5)
    assert all(not p.exists() for p in tmp_path.glob("*.wav"))


def rpc(method, **params):
    return server._methods["voice.live." + method]("request", {
        "session_id": "live-test", "live_id": "lease-1", **params})


def phase(f, expected):
    while True:
        event = f.events.get(timeout=5)
        if event["phase"] == expected:
            return event


def start(f):
    assert rpc("start", consent=True)["result"]["live_id"] == "lease-1"
    return f.opened.get(timeout=5)


def test_consent_owner_and_mutual_exclusion(voice, monkeypatch):
    f = voice
    assert "error" in rpc("start", consent=False)
    assert f.manager.active is None and not f.streams
    start(f)
    assert "error" in rpc("start", consent=True)
    assert "error" in rpc("control", action="stop", live_id="foreign")
    assert "error" in server._methods["voice.dictate.start"](1, {"session_id": "live-test", "capture_id": "other"})
    assert "error" in server._methods["voice.record"](1, {"action": "start"})
    assert "error" in server._methods["voice.tts"](1, {"text": "must not speak"})
    monkeypatch.setattr(server, "_caller_transport", lambda: object())
    assert "error" in rpc("control", action="stop")
    assert not f.manager.active.stop.is_set()


def test_spoken_turn_uses_configured_backend_and_never_sends_images_or_draft(voice):
    f = voice
    start(f)
    f.commands.put("utterance")
    params = f.submitted.get(timeout=5)
    assert params == {"session_id": "live-test", "text": "spoken request", "surface": "voice-live", "image_paths": [], "queued": True}
    assert phase(f, "thinking")["user_text"] == "spoken request"
    f.opened.get(timeout=5)


def test_mute_closes_device_unmute_explicitly_rearms_and_disconnect_releases(voice):
    f = voice
    _, stream = start(f)
    assert rpc("control", action="mute", muted=True).get("result")
    assert stream.abort.called and stream.close.called
    assert phase(f, "muted")["muted"] is True
    f.commands.put(None)
    assert rpc("control", action="mute", muted=False).get("result")
    f.opened.get(timeout=5)
    # Same hook invoked by the transport and session lifecycle chokepoints.
    f.manager.release(transport=server._stdio_transport)
    f.commands.put(None)
    assert f.idle.wait(5)
    assert f.manager.active is None


def test_barge_interrupts_only_owner_and_tts_completion(voice, monkeypatch):
    f = voice
    speech_started, speech_done = threading.Event(), threading.Event()
    def speak(text, stop, admit):
        assert text == "assistant reply" and admit()
        speech_started.set()
        assert speech_done.wait(5)
    monkeypatch.setattr(live_voice, "speak", speak)
    start(f)
    f.commands.put("utterance")
    f.submitted.get(timeout=5)
    trigger, _ = f.opened.get(timeout=5)
    f.manager.event("message.complete", "foreign", {"text": "wrong", "status": "complete"})
    assert not speech_started.is_set()
    f.manager.event("message.complete", "live-test", {"text": "assistant reply", "status": "complete"})
    assert speech_started.wait(5)
    assert phase(f, "speaking")["assistant_text"] == "assistant reply"
    f.session["running"] = True
    trigger("playback")
    f.session["agent"].interrupt.assert_called_once()
    assert phase(f, "interrupted")
    speech_done.set()


@pytest.mark.parametrize("operation", ["listen", "transcribe", "speak"])
def test_permission_provider_and_tts_failures_visible_and_release(voice, monkeypatch, operation):
    f = voice
    def fail(*args):
        raise RuntimeError("permission denied" if operation == "listen" else "configured provider failed")
    monkeypatch.setattr(live_voice, operation, fail)
    rpc("start", consent=True)
    if operation != "listen":
        f.opened.get(timeout=5)
        f.commands.put("utterance")
    if operation == "speak":
        f.submitted.get(timeout=5)
        f.opened.get(timeout=5)
        f.manager.event("message.complete", "live-test", {"text": "reply", "status": "complete"})
        f.commands.put(None)
    assert phase(f, "error")["error"]
    assert f.idle.wait(5)


def test_stop_during_stt_discards_late_result_and_closes_input(voice, monkeypatch):
    f = voice
    transcribing, finish = threading.Event(), threading.Event()
    def transcribe(path):
        transcribing.set()
        assert finish.wait(5)
        return "late result"
    monkeypatch.setattr(live_voice, "transcribe", transcribe)
    _, stream = start(f)
    f.commands.put("utterance")
    assert transcribing.wait(5)
    rpc("control", action="stop")
    assert stream.close.called
    finish.set()
    assert f.idle.wait(5)
    assert f.submitted.empty()


def test_stale_synthesis_cannot_acquire_playback(voice, monkeypatch):
    f = voice
    synthesizing, finish = threading.Event(), threading.Event()
    played = []
    def speak(text, stop, admit):
        synthesizing.set()
        assert finish.wait(5)
        if not stop.is_set() and admit():
            played.append(text)
    monkeypatch.setattr(live_voice, "speak", speak)
    start(f)
    f.commands.put("utterance"); f.submitted.get(timeout=5); f.opened.get(timeout=5)
    f.manager.event("message.complete", "live-test", {"text": "stale reply", "status": "complete"})
    assert synthesizing.wait(5)
    rpc("control", action="stop")
    f.commands.put(None); finish.set()
    assert f.idle.wait(5) and played == []


def test_normal_tts_completion_returns_to_listening(voice, monkeypatch):
    f = voice
    spoken = threading.Event()
    def speak(text, stop, admit):
        assert admit() and not stop.is_set()
        spoken.set()
    monkeypatch.setattr(live_voice, "speak", speak)
    start(f)
    f.commands.put("utterance"); f.submitted.get(timeout=5); f.opened.get(timeout=5)
    phase(f, "thinking")
    f.manager.event("message.complete", "live-test", {"text": "finished", "status": "complete"})
    assert spoken.wait(5)
    phase(f, "listening")


def test_transport_disconnect_chokepoint_releases_devices(voice, monkeypatch):
    f = voice
    _, stream = start(f)
    monkeypatch.setattr(server, "_detach_transport_from_sessions", lambda transport: [])
    assert server._close_sessions_for_transport(server._stdio_transport) == (0, 0)
    assert stream.close.called
    f.commands.put(None)
    assert f.idle.wait(5)


def test_full_duplex_endpoint_cancellation_never_writes_audio(monkeypatch):
    from tools import voice_mode
    stream = Mock()
    assert voice_mode._capture_until_quiet(stream, Mock(), 480, [], endpoint_blocks=5,
                                            max_blocks=20, should_stop=lambda: True) is None
    stream.read.assert_not_called()
