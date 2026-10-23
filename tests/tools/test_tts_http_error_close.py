"""Streamed TTS responses must be closed when ``raise_for_status()`` fails.

``_post_json`` issues ``requests.post(..., stream=True)``, so the connection stays checked out of the
pool until the body is consumed or the response is closed. The xAI and MiniMax ``t2a_v2`` paths call
``raise_for_status()`` before handing the response to the bounded reader (which closes it), so an HTTP
error used to leak the streamed connection.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from tools import tts_tool


class _ErrorStreamingResponse:
    """A streamed response whose ``raise_for_status`` raises ``requests.HTTPError``."""

    def __init__(self, status_code: int = 500, *, close_error: bool = False):
        self.status_code = status_code
        self.close_error = close_error
        self.headers = {"Content-Type": "application/json"}
        self.close_calls = 0
        self.error = requests.HTTPError(f"{status_code} Server Error", response=self)

    def iter_content(self, chunk_size=65536):
        del chunk_size
        raise AssertionError("body must not be read after raise_for_status fails")

    def raise_for_status(self):
        raise self.error

    def close(self):
        self.close_calls += 1
        if self.close_error:
            raise OSError("simulated response-close failure")


@pytest.fixture(autouse=True)
def _clean_tts_env(monkeypatch):
    for key in ("XAI_API_KEY", "XAI_BASE_URL", "HERMES_XAI_BASE_URL", "MINIMAX_API_KEY", "MINIMAX_CN_API_KEY", "MINIMAX_GROUP_ID"):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize("close_error", [False, True])
def test_xai_tts_closes_streamed_response_on_http_error(tmp_path, monkeypatch, close_error):
    monkeypatch.setenv("XAI_API_KEY", "test-xai-key")
    response = _ErrorStreamingResponse(status_code=503, close_error=close_error)
    output_path = tmp_path / "out.mp3"

    with patch("requests.post", return_value=response) as post:
        with pytest.raises(requests.HTTPError) as excinfo:
            tts_tool._generate_xai_tts("hello", str(output_path), {})

    assert post.call_args.kwargs["stream"] is True
    assert excinfo.value is response.error
    assert response.close_calls == 1
    assert not output_path.exists()


@pytest.mark.parametrize("close_error", [False, True])
def test_minimax_t2a_v2_tts_closes_streamed_response_on_http_error(tmp_path, monkeypatch, close_error):
    monkeypatch.setenv("MINIMAX_API_KEY", "test-minimax-key")
    response = _ErrorStreamingResponse(status_code=401, close_error=close_error)
    output_path = tmp_path / "out.mp3"

    with patch("requests.post", return_value=response) as post:
        with pytest.raises(requests.HTTPError) as excinfo:
            tts_tool._generate_minimax_tts("hello", str(output_path), {})

    assert "t2a_v2" in post.call_args.args[0]
    assert post.call_args.kwargs["stream"] is True
    assert excinfo.value is response.error
    assert response.close_calls == 1
    assert not output_path.exists()


class _SuccessfulStreamingResponse:
    """Return real streamed chunks while recording status checks and cleanup."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.close_calls = 0
        self.status_checks = 0
        self.read_calls = 0

    def iter_content(self, chunk_size=65536):
        self.read_calls += 1
        yield from self.chunks

    def raise_for_status(self):
        self.status_checks += 1

    def close(self):
        self.close_calls += 1


def test_xai_tts_success_still_streams_and_writes_audio(tmp_path, monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-xai-key")
    response = _SuccessfulStreamingResponse([b"hello", b"-audio"])
    output_path = tmp_path / "out.mp3"

    with patch("requests.post", return_value=response) as post:
        result = tts_tool._generate_xai_tts("hello", str(output_path), {})

    assert result == str(output_path)
    assert output_path.read_bytes() == b"hello-audio"
    assert post.call_args.kwargs["stream"] is True
    assert response.status_checks == 1
    assert response.read_calls == 1
    assert response.close_calls == 1


def test_minimax_t2a_v2_success_still_decodes_streamed_hex_audio(tmp_path, monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "test-minimax-key")
    response = _SuccessfulStreamingResponse([
        b'{"base_resp":{"status_code":0},"data":',
        b'{"audio":"616263"}}',
    ])
    output_path = tmp_path / "out.mp3"

    with patch("requests.post", return_value=response) as post:
        result = tts_tool._generate_minimax_tts("hello", str(output_path), {})

    assert result == str(output_path)
    assert output_path.read_bytes() == b"abc"
    assert "t2a_v2" in post.call_args.args[0]
    assert post.call_args.kwargs["stream"] is True
    assert response.status_checks == 1
    assert response.read_calls == 1
    assert response.close_calls == 1
