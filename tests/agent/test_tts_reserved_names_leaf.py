"""Import isolation and shared ownership of built-in TTS reserved names."""

import logging
import subprocess
import sys
from pathlib import Path

import pytest

from agent import tts_registry
from agent.tts_provider import TTSProvider


@pytest.fixture(autouse=True)
def _reset_registry():
    tts_registry._reset_for_tests()
    yield
    tts_registry._reset_for_tests()


def test_reserved_names_and_registry_import_without_application_dependencies():
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            """
import sys
sys.path.insert(0, sys.argv[1])
import agent.tts_reserved_names
import agent.tts_registry

forbidden = (
    "tools.tts_tool", "tools.tts_command_provider", "gateway", "hermes_cli.config",
    "openai", "elevenlabs", "edge_tts", "google.genai", "mistralai",
    "neutts", "kittentts", "piper",
)
loaded = sorted(
    name for name in sys.modules
    if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)
)
assert not loaded, loaded
""",
            str(Path(__file__).resolve().parents[2]),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_registry_and_command_provider_share_reserved_names_object():
    from agent.tts_reserved_names import BUILTIN_TTS_PROVIDERS
    from tools import tts_command_provider

    assert tts_registry._BUILTIN_NAMES is BUILTIN_TTS_PROVIDERS
    assert tts_registry._BUILTIN_NAMES is tts_command_provider.BUILTIN_TTS_PROVIDERS


def test_reserved_collision_warns_and_arbitrary_plugin_registers(caplog):
    class PluginProvider(TTSProvider):
        def __init__(self, name):
            self._name = name

        @property
        def name(self):
            return self._name

        def synthesize(self, text, output_path, **kwargs):
            return output_path

    with caplog.at_level(logging.WARNING, logger="agent.tts_registry"):
        tts_registry.register_provider(PluginProvider("openai"))

    assert tts_registry.get_provider("openai") is None
    assert "TTS provider 'openai' shadows a built-in name; registration ignored." in caplog.text

    plugin = PluginProvider("custom-leaf-test")
    tts_registry.register_provider(plugin)
    assert tts_registry.get_provider(plugin.name) is plugin
    assert plugin in tts_registry.list_providers()
