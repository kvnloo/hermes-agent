"""Explicit, transport-owned dictation using Hermes's recorder and STT dispatch.

Providers remain batch STT: periodic snapshots give replaceable live hypotheses,
not invented token streaming. No worker or audio device exists before start().
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from agent.memory_provider import spawn_context_thread


def create_recorder():
    from tools.voice_mode import create_audio_recorder
    from tools.voice_mode_transcript import _voice_config
    recorder = create_audio_recorder()
    config = _voice_config()
    for key, default in (("silence_threshold", 200), ("silence_duration", 3.0), ("max_recording_seconds", 120.0)):
        value = config.get(key, default)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            setattr(recorder, "_" + key, value)
    return recorder


def transcribe(path):
    from tools.voice_mode import transcribe_recording
    return transcribe_recording(path)


@dataclass
class Capture:
    id: str
    session: dict
    transport: Any
    emit: Callable[[dict], None]
    stop: threading.Event = field(default_factory=threading.Event)
    cancelled: threading.Event = field(default_factory=threading.Event)
    recorder: Any = None
    audio_lock: Any = field(default_factory=threading.Lock)
    thread: Any = None
    final_path: str | None = None


class Dictation:
    def __init__(self, *, interval: float = 3.0):
        self.interval = interval
        self.lock = threading.RLock()
        self.active: Capture | None = None

    def start(self, capture_id, session, transport, emit):
        with self.lock:
            if self.active is not None:
                raise RuntimeError("Microphone is busy with another dictation")
            capture = Capture(capture_id, session, transport, emit)
            self.active = capture
            capture.thread = spawn_context_thread(
                self._run, name="tui-dictation", args=(capture,))
            capture.thread.start()
        return capture

    def stop(self, capture_id, session, transport, *, cancel=False):
        with self.lock:
            capture = self.active
            if capture is None:
                return
            if (capture.id != capture_id or capture.session is not session
                    or capture.transport is not transport):
                raise RuntimeError("Dictation is owned by another capture or client")
            if cancel:
                capture.cancelled.set()
            capture.stop.set()
        if cancel:
            self._close_audio(capture)
        else:
            self._finish_audio(capture)

    def release(self, *, session=None, transport=None):
        with self.lock:
            capture = self.active
            if capture is None:
                return
            if capture.session is not session and capture.transport is not transport:
                return
            capture.cancelled.set()
            capture.stop.set()
        self._close_audio(capture)

    def _close_audio(self, capture):
        with capture.audio_lock:
            if capture.recorder is not None:
                capture.recorder.shutdown()

    def _finish_audio(self, capture):
        with capture.audio_lock:
            if capture.recorder is not None and capture.final_path is None and not capture.cancelled.is_set():
                capture.final_path = capture.recorder.stop()
                capture.recorder.shutdown()

    def _publish(self, capture, state, **extra):
        with self.lock:
            if self.active is capture and not capture.cancelled.is_set():
                capture.emit({"capture_id": capture.id, "state": state, **extra})

    def _text(self, capture, path):
        if not path:
            return ""
        try:
            if capture.cancelled.is_set():
                return ""
            result = transcribe(path)
            if not result.get("success"):
                raise RuntimeError(result.get("error") or "Speech transcription failed")
            return str(result.get("transcript") or "")
        finally:
            Path(path).unlink(missing_ok=True)

    def _run(self, capture):
        try:
            self._publish(capture, "starting")
            with capture.audio_lock:
                if capture.cancelled.is_set():
                    return
                capture.recorder = create_recorder()
                capture.recorder.start(on_silence_stop=lambda: self.stop(
                    capture.id, capture.session, capture.transport))
            if capture.cancelled.is_set():
                return
            self._publish(capture, "recording")
            while not capture.stop.wait(self.interval):
                with capture.audio_lock:
                    snapshot = getattr(capture.recorder, "snapshot", None)
                    path = snapshot() if snapshot and not capture.cancelled.is_set() else None
                if path:
                    text = self._text(capture, path)
                    self._publish(capture, "recording", text=text, final=False)
            if capture.cancelled.is_set():
                return
            self._finish_audio(capture)
            self._publish(capture, "transcribing")
            text = self._text(capture, capture.final_path)
            self._publish(capture, "idle", text=text, final=True)
        except Exception as exc:
            self._close_audio(capture)
            self._publish(capture, "error", error=str(exc))
        finally:
            try:
                self._close_audio(capture)
            finally:
                if capture.final_path:
                    Path(capture.final_path).unlink(missing_ok=True)
                with self.lock:
                    if self.active is capture:
                        self.active = None


manager = Dictation()
