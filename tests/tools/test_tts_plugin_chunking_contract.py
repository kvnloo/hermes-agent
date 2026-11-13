"""Pin plugin chunk caps through text_to_speech_tool, regression contract for #675.

Adapted from fork draft 6d74cec92eb0. Registry lookup, cap resolution, splitting,
synthesis dispatch and delivery envelopes are real. Synthetic bytes and a
controlled combiner test dispatch, not codec validity or live audio quality.
"""

import json
from pathlib import Path

import pytest

from agent import tts_registry
from agent.tts_provider import TTSProvider
from tools import tts_tool
from tools.tts_tool_delivery import FALLBACK_MAX_TEXT_LENGTH

PLUGIN = "chunky-tts"
WORDS = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel")
TEXT = " ".join(
    " ".join(WORDS[(i + j) % len(WORDS)] for j in range(6)).capitalize() + "."
    for i in range(120)
)


class _RecordingProvider(TTSProvider):
    def __init__(self):
        self.texts = []

    @property
    def name(self):
        return PLUGIN

    def synthesize(self, text, output_path, **kwargs):
        self.texts.append(text)
        Path(output_path).write_bytes(b"\x00")
        return output_path


def _concat(paths, output_path, *, voice_compatible=False):
    Path(output_path).write_bytes(b"".join(Path(path).read_bytes() for path in paths))
    return output_path


@pytest.fixture
def plugin(monkeypatch):
    tts_registry._reset_for_tests()
    provider = _RecordingProvider()
    tts_registry.register_provider(provider)
    monkeypatch.setattr("tools.tts_tool_delivery._concat_audio_files", _concat)
    yield provider
    tts_registry._reset_for_tests()


def _speak(monkeypatch, tmp_path, config, text):
    monkeypatch.setattr(tts_tool, "_load_tts_config", lambda: config)
    return json.loads(tts_tool.text_to_speech_tool(
        text=text, output_path=str(tmp_path / "out.mp3")))


def _assert_delivery(result, tmp_path, chunk_count):
    output_path = str(tmp_path / "out.mp3")
    assert result["success"] is True
    assert result["provider"] == PLUGIN
    assert result["file_path"] == output_path
    assert result["file_paths"] == [output_path]
    assert result["media_tag"] == f"MEDIA:{output_path}"
    assert result["voice_compatible"] is False
    assert result["chunk_count"] == chunk_count
    assert result["delivery_file_count"] == 1
    assert result["combined_chunks"] is True
    assert Path(output_path).read_bytes() == b"\x00" * chunk_count


@pytest.mark.parametrize("text, separator", [
    pytest.param(TEXT, " ", id="sentence-boundaries"),
    pytest.param("abcdefghijklmnopqrstuvwxyz" * 180, "", id="hard-boundaries"),
])
def test_plugin_receives_ordered_chunks_under_its_configured_cap(
    plugin, monkeypatch, tmp_path, text, separator,
):
    result = _speak(monkeypatch, tmp_path, {
        "provider": PLUGIN, PLUGIN: {"max_text_length": 700},
    }, text)

    assert len(plugin.texts) > 1
    assert all(0 < len(chunk) <= 700 for chunk in plugin.texts)
    assert separator.join(plugin.texts) == text
    _assert_delivery(result, tmp_path, len(plugin.texts))


@pytest.mark.parametrize("section", [
    pytest.param(None, id="absent-section"),
    pytest.param({}, id="absent-cap"),
    pytest.param({"max_text_length": None}, id="null"),
    pytest.param({"max_text_length": 0}, id="zero"),
    pytest.param({"max_text_length": -5}, id="negative"),
    pytest.param({"max_text_length": "700"}, id="string"),
    pytest.param({"max_text_length": True}, id="boolean"),
    pytest.param({"max_text_length": 1.5}, id="float"),
])
def test_absent_or_invalid_plugin_cap_keeps_the_generic_fallback(
    plugin, monkeypatch, tmp_path, section,
):
    config = {"provider": PLUGIN}
    if section is not None:
        config[PLUGIN] = section
    text = "a" * (FALLBACK_MAX_TEXT_LENGTH + 50)

    result = _speak(monkeypatch, tmp_path, config, text)

    assert [len(chunk) for chunk in plugin.texts] == [FALLBACK_MAX_TEXT_LENGTH, 50]
    assert "".join(plugin.texts) == text
    _assert_delivery(result, tmp_path, len(plugin.texts))


def test_same_name_command_provider_still_wins_over_the_plugin(plugin, monkeypatch, tmp_path):
    commanded = []

    def fake_command(text, output_path, provider, provider_config, tts_config):
        commanded.append(text)
        Path(output_path).write_bytes(b"\x00")
        return output_path

    monkeypatch.setattr(tts_tool, "_generate_command_tts", fake_command)
    config = {
        "provider": PLUGIN,
        PLUGIN: {"max_text_length": 700},
        "providers": {PLUGIN: {"type": "command", "command": "say {input_path} {output_path}"}},
    }

    result = _speak(monkeypatch, tmp_path, config, TEXT)

    assert plugin.texts == []
    assert len(commanded) > 1
    assert all(0 < len(chunk) <= 700 for chunk in commanded)
    assert " ".join(commanded) == TEXT
    _assert_delivery(result, tmp_path, len(commanded))
