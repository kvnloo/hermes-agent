"""Real, model-free decoding evidence for #135245 / liuhao1024's #135260.

Run explicitly in an environment containing the stt-whisper dependencies with
scripts/run_tests.sh with -m integration. Missing dependencies fail; no mocks or skip can
turn an unexecuted decoder into a pass. SultaniSaid reported the PyAV 19 failure.
"""

import io
import wave
from importlib.metadata import version

import pytest

pytestmark = pytest.mark.integration


def _wav(samples, rate):
    """Use the same stdlib PCM-WAV fixture approach as transcription tests."""
    stream = io.BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setnchannels(1 if samples.ndim == 1 else samples.shape[1])
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(samples.astype("<i2").tobytes())
    return stream.getvalue()


def _versions():
    return {name: version(name) for name in ("faster-whisper", "av", "numpy", "ctranslate2")}


def test_real_whisper_decode_mono_pcm(tmp_path):
    """Real av.open + decode must retain deterministic nonzero PCM samples."""
    import numpy as np
    from faster_whisper.audio import decode_audio

    print(_versions())
    samples = np.tile(np.array([0, 4096, 8192, 4096, 0, -4096, -8192, -4096]), 1000)
    path = tmp_path / "synthetic tone.wav"
    path.write_bytes(_wav(samples, 16000))

    decoded = decode_audio(str(path), sampling_rate=16000)

    assert decoded.dtype == np.float32
    assert decoded.shape == samples.shape
    np.testing.assert_array_equal(decoded, samples.astype(np.float32) / 32768)


def test_real_whisper_decode_stereo_resamples_stream():
    """Exercise the real decoder's channel mixing and 48kHz -> 16kHz path."""
    import numpy as np
    from faster_whisper.audio import decode_audio

    print(_versions())
    t = np.arange(24000) / 48000
    tone = (8192 * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
    stereo = np.column_stack((tone, tone))

    decoded = decode_audio(io.BytesIO(_wav(stereo, 48000)), sampling_rate=16000)

    assert decoded.dtype == np.float32
    assert decoded.shape == (8000,)
    assert np.isfinite(decoded).all()
    assert 0.1 < np.sqrt(np.mean(decoded ** 2)) < 0.4
    # No model is involved: check the generated tone survives actual resampling.
    peak = np.argmax(np.abs(np.fft.rfft(decoded)))
    assert abs(peak * 16000 / decoded.size - 440) <= 2
