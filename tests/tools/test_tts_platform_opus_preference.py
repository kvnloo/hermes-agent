"""Platform voice-output declarations drive both TTS paths. Regression for fork #668."""

import builtins
import importlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from gateway import platform_registry as registry_module
from gateway.config import Platform
from gateway.platform_registry import PlatformEntry, PlatformRegistry
from gateway.platforms.base import build_auto_tts_output_path, should_send_media_as_audio
from gateway.session_context import _SESSION_PLATFORM
from hermes_constants import (
    hermes_home_key,
    reset_hermes_home_override,
    set_hermes_home_override,
)
from tools import tts_tool


@pytest.fixture
def registry(monkeypatch, tmp_path):
    registry = PlatformRegistry()
    monkeypatch.setattr(registry_module, "platform_registry", registry)
    monkeypatch.setattr(tts_tool, "_default_output_dir", lambda: str(tmp_path))
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    return registry


def _entry(name, preference=None):
    entry = PlatformEntry(
        name=name,
        label=name,
        adapter_factory=Mock(side_effect=AssertionError("adapter constructed")),
        check_fn=Mock(side_effect=AssertionError("dependency probe called")),
        ensure_deps_fn=Mock(side_effect=AssertionError("dependencies installed")),
        validate_config=Mock(side_effect=AssertionError("config validated")),
    )
    # Assign after construction so the unfixed base reaches the routing assertion.
    if preference is not None:
        entry.voice_output_opus = preference
    return entry


def _output_path(route, name):
    if route == "gateway":
        return Path(build_auto_tts_output_path(name))
    token = _SESSION_PLATFORM.set(getattr(name, "value", name) or "")
    try:
        platform, want_opus = tts_tool._session_platform()
        assert platform == (getattr(name, "value", name) or "").lower()
        path, error = tts_tool._resolve_output_base(None, "openai", None, want_opus)
        assert error is None
        return path
    finally:
        _SESSION_PLATFORM.reset(token)


def test_declaration_is_optional_and_default_false():
    entry = _entry("plain-speech")
    assert entry.voice_output_opus is False
    assert PlatformEntry(
        "native-speech", "Native speech", Mock(), Mock(), voice_output_opus=True,
    ).voice_output_opus is True


@pytest.mark.parametrize("route", ["tool", "gateway"])
@pytest.mark.parametrize("preference, extension", [(True, ".ogg"), (False, ".mp3"), (None, ".mp3")])
def test_arbitrary_registered_plugin(registry, route, preference, extension):
    entry = _entry("aurora-voice-link", preference)
    registry.register(entry)
    assert _output_path(route, entry.name).suffix == extension
    for callback in (entry.adapter_factory, entry.check_fn, entry.ensure_deps_fn, entry.validate_config):
        callback.assert_not_called()


@pytest.mark.parametrize("route", ["tool", "gateway"])
@pytest.mark.parametrize("name", ["unknown-voice-link", "", None])
def test_unregistered_platform_uses_mp3(registry, route, name):
    assert _output_path(route, name).suffix == ".mp3"


@pytest.mark.parametrize("route", ["tool", "gateway"])
@pytest.mark.parametrize("name", ["telegram", "matrix", "feishu", "whatsapp", "signal", "discord", "slack"])
def test_current_platforms_keep_their_encoding_without_sdk_imports(registry, monkeypatch, route, name):
    original_import = builtins.__import__

    def guarded_import(module, *args, **kwargs):
        assert not module.startswith("plugins.platforms."), module
        assert module.split(".")[0] not in {"telegram", "discord", "mautrix", "lark_oapi", "slack_sdk"}, module
        return original_import(module, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    expected = ".mp3" if name in {"discord", "slack"} else ".ogg"
    assert _output_path(route, Platform(name)).suffix == expected


@pytest.mark.parametrize("route", ["tool", "gateway"])
def test_profile_scopes_do_not_leak(registry, tmp_path, route):
    name = "same-voice-link"
    for profile, preference in (("alpha", True), ("beta", False)):
        home = tmp_path / profile
        registry.register(_entry(name, preference), scope=hermes_home_key(home))
    for profile, extension in (("alpha", ".ogg"), ("beta", ".mp3"), ("alpha", ".ogg"), ("other", ".mp3")):
        token = set_hermes_home_override(tmp_path / profile)
        try:
            assert _output_path(route, name).suffix == extension
        finally:
            reset_hermes_home_override(token)


@pytest.mark.parametrize("route", ["tool", "gateway"])
def test_registered_opt_out_overrides_bundled_default(registry, route):
    registry.register(_entry("telegram", False))
    assert _output_path(route, "telegram").suffix == ".mp3"


@pytest.mark.parametrize("route", ["tool", "gateway"])
def test_lookup_loads_only_requested_registration(registry, route):
    entry = _entry("deferred-voice-link", True)
    wanted = Mock(side_effect=lambda: registry.register(entry))
    unrelated = Mock(side_effect=AssertionError("unrelated adapter imported"))
    registry.register_deferred(entry.name, wanted)
    registry.register_deferred("unrelated-voice-link", unrelated)
    assert _output_path(route, entry.name).suffix == ".ogg"
    assert _output_path(route, entry.name).suffix == ".ogg"
    wanted.assert_called_once_with()
    unrelated.assert_not_called()
    for callback in (entry.adapter_factory, entry.check_fn, entry.ensure_deps_fn, entry.validate_config):
        callback.assert_not_called()


@pytest.mark.parametrize("name", ["telegram", "matrix", "feishu", "whatsapp", "signal"])
def test_bundled_registration_declares_opus(registry, name):
    from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest

    context = PluginContext(
        PluginManifest(name=name, key=name, source="bundled"),
        PluginManager(scope_key=registry.current_scope_key()),
    )
    module = importlib.import_module(f"plugins.platforms.{name}")
    module.register(context)
    assert registry.get(name).voice_output_opus is True
    assert _output_path("tool", name).suffix == ".ogg"
    assert _output_path("gateway", name).suffix == ".ogg"


@pytest.mark.parametrize("preference, extension", [(True, ".ogg"), (False, ".mp3")])
def test_registered_plugin_through_tool_dispatch(registry, monkeypatch, preference, extension):
    from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest
    from tools.registry import registry as tool_registry

    name = "aurora-dispatch-link"
    entry = _entry(name)
    context = PluginContext(
        PluginManifest(name=name, key=name, source="user"),
        PluginManager(scope_key=registry.current_scope_key()),
    )
    context.register_platform(
        name=name, label=name, adapter_factory=entry.adapter_factory,
        check_fn=entry.check_fn, ensure_deps_fn=entry.ensure_deps_fn,
        voice_output_opus=preference,
    )
    monkeypatch.setattr(tts_tool, "_load_tts_config", lambda: {"provider": "openai"})
    monkeypatch.setattr(tts_tool, "_select_builtin_engine", lambda provider: (provider, None))

    def synthesize(provider, text, path, config, instructions):
        Path(path).write_bytes(b"OggS" if Path(path).suffix == ".ogg" else b"ID3")

    monkeypatch.setattr(tts_tool, "_synthesize_builtin", synthesize)
    token = _SESSION_PLATFORM.set(name)
    try:
        result = json.loads(tool_registry.dispatch("text_to_speech", {"text": "Hello from a plugin"}))
    finally:
        _SESSION_PLATFORM.reset(token)
    assert result["success"] is True, result
    assert Path(result["file_path"]).suffix == extension
    assert Path(result["file_path"]).read_bytes() == (b"OggS" if preference else b"ID3")
    assert result["voice_compatible"] is preference
    assert ("[[audio_as_voice]]" in result["media_tag"]) is preference
    entry.adapter_factory.assert_not_called()
    entry.check_fn.assert_not_called()
    entry.ensure_deps_fn.assert_not_called()


@pytest.mark.parametrize("extension, is_voice, expected", [
    (".ogg", False, False), (".opus", False, False),
    (".mp3", False, True), (".ogg", True, True),
])
def test_explicit_attachment_semantics_stay_unchanged(registry, extension, is_voice, expected):
    registry.register(_entry("telegram", True))
    assert should_send_media_as_audio(Platform.TELEGRAM, extension, is_voice) is expected
