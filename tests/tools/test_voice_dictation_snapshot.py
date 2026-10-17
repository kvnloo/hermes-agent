"""Dictation snapshots use fake PCM, never sounddevice or a real microphone."""
from pathlib import Path
from types import SimpleNamespace
import wave

import pytest

from tools import voice_mode


class Frame:
    def __len__(self):
        return 16000

    def tobytes(self):
        return b"\x01\x00" * 16000


@pytest.fixture()
def recorder(tmp_path, monkeypatch):
    monkeypatch.setattr(voice_mode, "_TEMP_DIR", str(tmp_path / "audio"))
    monkeypatch.setattr(voice_mode, "_import_audio", lambda: (
        None, SimpleNamespace(concatenate=lambda frames, axis: frames[0])))
    rec = voice_mode.AudioRecorder()
    rec._recording = True
    rec._frames = [Frame()]
    rec._peak_rms = 400
    return rec


def test_snapshots_and_final_have_independent_audio_files(recorder):
    first = Path(recorder.snapshot())
    second = Path(recorder.snapshot())
    final = Path(recorder.stop())
    assert len({first, second, final}) == 3
    first.unlink()
    assert second.is_file() and final.is_file()
    with wave.open(str(second), "rb") as audio:
        assert audio.getnframes() == 16000
        assert audio.getframerate() == 16000
    assert not recorder.is_recording


def test_snapshots_do_not_stop_or_consume_live_audio(recorder):
    frames = list(recorder._frames)
    path = Path(recorder.snapshot())
    assert recorder.is_recording
    assert recorder._frames == frames
    path.unlink()
    recorder._peak_rms = 0
    assert recorder.snapshot() is None
    recorder.cancel()
    assert recorder.snapshot() is None
