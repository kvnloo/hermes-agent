"""Plugin TTS providers chunk at their configured cap through ``text_to_speech_tool``.

The plugin dispatch tests call ``_dispatch_to_plugin_provider`` directly and the
max-text-length tests drive built-in engines only, so nothing pinned the composed
contract: a registered ``TTSProvider`` named in ``tts.provider`` receives ordered
chunks no longer than ``tts.<name>.max_text_length``, and ordinary config rules
(invalid overrides fall back, a same-name command provider wins) still apply.
Audio bytes are a placeholder; only the combiner is replaced.
"""

from __future__ import annotations

import json

import pytest

from agent import tts_registry
from agent.tts_provider import TTSProvider
from tools.tts_tool import text_to_speech_tool
from tools.tts_tool_delivery import FALLBACK_MAX_TEXT_LENGTH

PLUGIN = "chunky-tts"
WORDS = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel")
TEXT = " ".join(
    " ".join(WORDS[(i + j) % len(WORDS)] for j in range(6)).capitalize() + "."
    for i in range(120)
)


class _RecordingProvider(TTSProvider):
    def __init__(self) -> None:
        self.texts: list[str] = []

    @property
    def name(self) -> str:
        return PLUGIN

    def synthesize(self, text, output_path, **kwargs):
        self.texts.append(text)
        with open(output_path, "wb") as handle:
            handle.write(b"\x00")
        return output_path


def _concat(paths, output_path, *, voice_compatible=False):
    with open(output_path, "wb") as destination:
        for path in paths:
            with open(path, "rb") as source:
                destination.write(source.read())
    return output_path


@pytest.fixture
def plugin(monkeypatch):
    tts_registry._reset_for_tests()
    provider = _RecordingProvider()
    tts_registry.register_provider(provider)
    monkeypatch.setattr("tools.tts_tool_delivery._concat_audio_files", _concat)
    yield provider
    tts_registry._reset_for_tests()


def _speak(monkeypatch, tmp_path, config, text=TEXT):
    monkeypatch.setattr("tools.tts_tool._load_tts_config", lambda: config)
    return json.loads(text_to_speech_tool(text=text, output_path=str(tmp_path / "out.mp3")))


def test_plugin_receives_ordered_chunks_under_its_configured_cap(plugin, monkeypatch, tmp_path):
    result = _speak(monkeypatch, tmp_path, {"provider": PLUGIN, PLUGIN: {"max_text_length": 700}})

    assert result["success"] is True
    assert result["provider"] == PLUGIN
    assert result["media_tag"]
    assert result["chunk_count"] == len(plugin.texts) > 1
    assert max(len(chunk) for chunk in plugin.texts) <= 700
    assert " ".join(plugin.texts) == TEXT


@pytest.mark.parametrize("override", [None, 0, -5, "700", True, 1.5])
def test_absent_or_invalid_plugin_cap_keeps_the_generic_fallback(plugin, monkeypatch, tmp_path, override):
    section = {} if override is None else {"max_text_length": override}
    text = "a" * (FALLBACK_MAX_TEXT_LENGTH + 50)

    result = _speak(monkeypatch, tmp_path, {"provider": PLUGIN, PLUGIN: section}, text=text)

    assert result["success"] is True
    assert [len(chunk) for chunk in plugin.texts] == [FALLBACK_MAX_TEXT_LENGTH, 50]


def test_same_name_command_provider_still_wins_over_the_plugin(plugin, monkeypatch, tmp_path):
    commanded: list[str] = []

    def fake_command(text, output_path, provider, provider_config, tts_config):
        commanded.append(text)
        with open(output_path, "wb") as handle:
            handle.write(b"\x00")
        return output_path

    monkeypatch.setattr("tools.tts_tool._generate_command_tts", fake_command)
    config = {
        "provider": PLUGIN,
        PLUGIN: {"max_text_length": 700},
        "providers": {PLUGIN: {"type": "command", "command": "say {input_path} {output_path}"}},
    }

    result = _speak(monkeypatch, tmp_path, config)

    assert result["success"] is True
    assert plugin.texts == []
    assert len(commanded) == result["chunk_count"] > 1
    assert max(len(chunk) for chunk in commanded) <= 700
    assert " ".join(commanded) == TEXT
