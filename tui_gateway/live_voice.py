"""Opt-in, session/transport-owned conversation using the configured Hermes audio backends.

No global voice flags: dictation stays insert-only and other sessions never gain a mic.
The existing full-duplex detector handles speaker bleed and utterance endpointing.
"""
from __future__ import annotations

import json
import logging
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from agent.memory_provider import spawn_context_thread


def listen(stop, playing, trigger, opened):
    from tools.voice_mode import full_duplex_listen
    from tools.voice_mode_transcript import _voice_config
    cfg = _voice_config()
    return full_duplex_listen(stop, is_playing=playing, on_trigger=trigger,
                              on_stream=opened, strict=True,
                              multiplier=cfg.get("barge_in_threshold_multiplier") or None)


def transcribe(path):
    from tools.voice_mode import transcribe_recording
    result = transcribe_recording(path)
    if not result.get("success"):
        raise RuntimeError(result.get("error") or "Speech transcription failed")
    return str(result.get("transcript") or "").strip()


def silence():
    from tools.voice_mode import stop_playback
    stop_playback()


def speak(text, stop, admit):
    """Use the configured TTS dispatcher, with no alternate provider on failure."""
    from tools.tts_tool import text_to_speech_tool
    from tools.voice_mode import play_audio_file
    with tempfile.TemporaryDirectory(prefix="hermes-live-voice-") as directory:
        output = str(Path(directory) / "reply.wav")
        result = text_to_speech_tool(text=text, output_path=output)
        result = json.loads(result) if isinstance(result, str) else result
        if not result.get("success"):
            raise RuntimeError(result.get("error") or "Speech synthesis failed")
        paths = result.get("file_paths") or [result.get("file_path") or output]
        try:
            for path in paths:
                # admit serializes speaker acquisition with stop/mute/barge-in.
                if stop.is_set() or not admit():
                    return
                if not play_audio_file(path, stop_event=stop) and not stop.is_set():
                    raise RuntimeError("Audio playback failed; check speaker permissions and output device")
        finally:
            for path in paths:
                Path(path).unlink(missing_ok=True)


@dataclass
class Lease:
    id: str
    sid: str
    session: dict
    transport: Any
    emit: Callable[[dict], None]
    submit: Callable[[str], dict]
    stop: threading.Event = field(default_factory=threading.Event)
    wake: threading.Event = field(default_factory=threading.Event)
    speech_stop: threading.Event = field(default_factory=threading.Event)
    muted: bool = False
    stream: Any = None
    workers: int = 0
    generation: int = 0
    waiting: bool = False
    pending_start: bool = False
    input_epoch: int = 0


class LiveVoice:
    def __init__(self):
        self.lock = threading.RLock()
        self.active: Lease | None = None

    def _publish(self, lease, phase, **extra):
        with self.lock:
            if self.active is lease:
                lease.emit({"live_id": lease.id, "phase": phase, "muted": lease.muted, **extra})

    def _spawn(self, lease, target, *args):
        lease.workers += 1
        def run():
            try:
                target(lease, *args)
            except Exception as exc:
                logging.getLogger(__name__).exception("Live voice worker failed")
                if not lease.stop.is_set():
                    self._publish(lease, "error", error=str(exc))
                    self._halt(lease)
            finally:
                with self.lock:
                    lease.workers -= 1
                    if lease.workers == 0 and self.active is lease:
                        self._publish(lease, "idle")
                        self.active = None
        thread = spawn_context_thread(run, name="tui-live-voice")
        thread.start()

    def start(self, live_id, sid, session, transport, emit, submit):
        with self.lock:
            if self.active is not None:
                raise RuntimeError("Live voice is already owned; stop it first")
            lease = Lease(live_id, sid, session, transport, emit, submit)
            self.active = lease
            self._publish(lease, "starting")
            self._spawn(lease, self._listen)
            return lease

    def owned(self, live_id, session, transport):
        lease = self.active
        if lease is None:
            return None
        if lease.id != live_id or lease.session is not session or lease.transport is not transport:
            raise RuntimeError("Live voice is owned by another session or client")
        return lease

    def _close_input(self, lease):
        stream, lease.stream = lease.stream, None
        if stream is not None:
            stream.abort(ignore_errors=True)
            stream.close(ignore_errors=True)

    def _cut(self, lease):
        lease.generation += 1
        lease.waiting = False
        lease.pending_start = False
        lease.speech_stop.set()
        silence()

    def _halt(self, lease):
        with self.lock:
            lease.stop.set()
            lease.wake.set()
            self._cut(lease)
            self._close_input(lease)

    def release(self, *, session=None, transport=None):
        with self.lock:
            lease = self.active
            if lease and (lease.session is session or lease.transport is transport):
                self._publish(lease, "stopping")
                self._halt(lease)

    def control(self, live_id, session, transport, action, muted=False):
        with self.lock:
            lease = self.owned(live_id, session, transport)
            if lease is None:
                return
            if action == "stop":
                self.release(session=session)
            elif action == "mute":
                lease.muted = muted
                lease.input_epoch += 1
                self._cut(lease)
                self._close_input(lease)
                self._publish(lease, "muted" if muted else "starting")
                lease.wake.set()
            elif action == "interrupt":
                self._interrupt(lease)

    def _interrupt(self, lease):
        with self.lock:
            if lease.stop.is_set() or lease.muted:
                return
            self._cut(lease)
            agent = lease.session.get("agent")
            if lease.session.get("running") and agent is not None:
                agent.interrupt()
            self._publish(lease, "interrupted")

    def _opened(self, lease, stream, epoch):
        with self.lock:
            if lease.stop.is_set() or lease.muted or epoch != lease.input_epoch:
                stream.abort(ignore_errors=True)
                stream.close(ignore_errors=True)
                return
            lease.stream = stream
            if not lease.waiting and not lease.pending_start and lease.workers == 1:
                self._publish(lease, "listening")

    def _listen(self, lease):
        from tools.voice_mode import is_audio_output_active
        from tools.voice_mode_transcript import is_voice_stop_phrase, is_whisper_hallucination
        while not lease.stop.is_set():
            with self.lock:
                paused = lease.muted
                epoch = lease.input_epoch
                lease.wake.clear()
            if paused:
                lease.wake.wait()
                continue
            path = None
            try:
                path = listen(lambda: lease.stop.is_set() or lease.muted or epoch != lease.input_epoch,
                              is_audio_output_active, lambda _phase: self._interrupt(lease),
                              lambda stream: self._opened(lease, stream, epoch))
                if lease.stop.is_set() or lease.muted or epoch != lease.input_epoch:
                    continue
                if not path:
                    raise RuntimeError("Microphone capture ended; check audio dependencies and device permissions")
                self._publish(lease, "transcribing")
                text = transcribe(path)
                with self.lock:
                    if lease.stop.is_set() or lease.muted or epoch != lease.input_epoch:
                        continue
                    if is_voice_stop_phrase(text):
                        self.release(session=lease.session)
                        continue
                    if text and not is_whisper_hallucination(text):
                        lease.pending_start = True
                        self._publish(lease, "thinking", user_text=text)
                        result = lease.submit(text)
                        if result.get("error"):
                            raise RuntimeError(result["error"]["message"])
            except Exception:
                if not (lease.muted or lease.stop.is_set() or epoch != lease.input_epoch):
                    raise
            finally:
                with self.lock:
                    self._close_input(lease)
                if path:
                    Path(path).unlink(missing_ok=True)

    def event(self, event, sid, payload):
        if event not in {"message.start", "message.complete", "error"}:
            return
        with self.lock:
            lease = self.active
            if not lease or lease.sid != sid or lease.stop.is_set() or lease.muted:
                return
            if event == "message.start":
                if lease.pending_start:
                    lease.waiting, lease.pending_start = True, False
                return
            if event == "error" and (lease.pending_start or lease.waiting):
                self._publish(lease, "error", error=str((payload or {}).get("message") or "Assistant failed"))
                self._halt(lease)
                return
            if event != "message.complete" or not lease.waiting:
                return
            lease.waiting = False
            text = str((payload or {}).get("text") or "")
            status = (payload or {}).get("status", "complete")
            if status == "error":
                self._publish(lease, "error", error=text or "Assistant turn failed")
                self._halt(lease)
            elif status == "complete" and text:
                lease.speech_stop = threading.Event()
                self._publish(lease, "speaking", assistant_text=text)
                # Completion can arrive on a compute-host reader, not the profile-bound turn.
                from tui_gateway import server
                with server._session_profile_runtime_scope(lease.session):
                    self._spawn(lease, self._speak, text, lease.generation, lease.speech_stop)
            else:
                self._publish(lease, "listening")

    def _speak(self, lease, text, generation, stop):
        def admit():
            with self.lock:
                return self.active is lease and not lease.stop.is_set() and not lease.muted and generation == lease.generation
        try:
            speak(text, stop, admit)
        except Exception:
            if admit():
                raise
        if admit():
            self._publish(lease, "listening")


manager = LiveVoice()
