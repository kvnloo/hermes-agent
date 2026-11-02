"""TTS upload-byte limits come from the destination platform's own registration.

A platform plugin declares ``PlatformEntry.audio_upload_max_bytes``; the provider-neutral packer
reads it (explicit ``tts.delivery_profiles`` config still wins, and an absent or invalid value
keeps the generic 10 MiB default). The lookup must not construct an adapter, probe or install
dependencies, or import any platform other than the destination.
"""

import pytest

from gateway import platform_registry as registry_module
from gateway.platform_registry import PlatformEntry, PlatformRegistry
from hermes_constants import hermes_home_key, reset_hermes_home_override, set_hermes_home_override
from tools.tts_tool_delivery import _pack_audio_files_for_delivery, _resolve_audio_delivery_profile

MIB = 1024 * 1024
GENERIC_MAX = 10 * MIB


def _forbidden(*_args, **_kwargs):
    raise AssertionError("an upload-limit lookup must not build adapters or probe/install deps")


def _entry(name, **fields):
    return PlatformEntry(
        name=name, label=name, adapter_factory=_forbidden, check_fn=_forbidden,
        ensure_deps_fn=_forbidden, validate_config=_forbidden, is_connected=_forbidden, **fields)


@pytest.fixture
def registry(monkeypatch):
    fresh = PlatformRegistry()
    monkeypatch.setattr(registry_module, "platform_registry", fresh)
    return fresh


def _chunk_files(tmp_path, count, size):
    paths = []
    for index in range(count):
        path = tmp_path / f"chunk{index}.ogg"
        with open(path, "wb") as handle:
            handle.truncate(size)  # sparse: the packer reads st_size only
        paths.append(str(path))
    return paths


def test_deferred_plugin_limit_drives_the_real_packer(registry, tmp_path):
    loaded = []
    scope = registry.current_scope_key()

    def load_pigeon():
        loaded.append("pigeon")
        registry.register(_entry("pigeon", audio_upload_max_bytes=30 * MIB), scope=scope)

    registry.register_deferred("pigeon", load_pigeon, scope=scope)
    registry.register_deferred("unrelated", lambda: loaded.append("unrelated"), scope=scope)

    profile = _resolve_audio_delivery_profile("Pigeon")

    assert (profile.max_file_bytes, profile.safety_ratio) == (30 * MIB, 0.85)
    # Three 6 MiB chunks fit one 30 MiB upload; the generic 10 MiB limit would need three.
    assert len(_pack_audio_files_for_delivery(_chunk_files(tmp_path, 3, 6 * MIB), profile)) == 1
    assert loaded == ["pigeon"]


def test_explicit_config_wins_over_registered_limit(registry):
    registry.register(_entry("pigeon", audio_upload_max_bytes=30 * MIB), scope=registry.current_scope_key())
    config = {"delivery_profiles": {"pigeon": {"max_file_bytes": 2 * MIB, "safety_ratio": 1.5}}}

    profile = _resolve_audio_delivery_profile("pigeon", config)

    assert (profile.max_file_bytes, profile.safety_ratio) == (2 * MIB, 0.85)


@pytest.mark.parametrize("declared", [0, -1, True, "50MB", 2.5])
def test_invalid_registered_limit_uses_generic_default(registry, declared):
    registry.register(_entry("pigeon", audio_upload_max_bytes=declared), scope=registry.current_scope_key())

    assert _resolve_audio_delivery_profile("pigeon").max_file_bytes == GENERIC_MAX


def test_unregistered_or_absent_platform_uses_generic_default(registry):
    registry.register(_entry("pigeon"), scope=registry.current_scope_key())

    for platform in ("pigeon", "nowhere", "", None):
        profile = _resolve_audio_delivery_profile(platform)
        assert (profile.max_file_bytes, profile.safety_ratio) == (GENERIC_MAX, 0.85)


def test_profiles_may_declare_different_limits(registry, tmp_path):
    limits = {"a": 20 * MIB, "b": 40 * MIB}
    for profile_name, limit in limits.items():
        registry.register(_entry("pigeon", audio_upload_max_bytes=limit),
                          scope=hermes_home_key(tmp_path / profile_name))

    for profile_name, limit in limits.items():
        token = set_hermes_home_override(tmp_path / profile_name)
        try:
            assert _resolve_audio_delivery_profile("pigeon").max_file_bytes == limit
        finally:
            reset_hermes_home_override(token)


class _RegisteringContext:
    """The slice of ``PluginContext`` a platform plugin's ``register()`` uses."""

    def __init__(self, registry):
        self._registry = registry

    def register_platform(self, name, label, adapter_factory, check_fn, **fields):
        entry = PlatformEntry(name=name, label=label, adapter_factory=adapter_factory,
                              check_fn=check_fn, source="plugin", **fields)
        self._registry.register(entry, scope=self._registry.current_scope_key())


@pytest.mark.parametrize("platform, max_bytes", [("telegram", 50 * MIB), ("discord", 10 * MIB)])
def test_bundled_registrations_keep_their_upload_limits(registry, platform, max_bytes):
    from importlib import import_module

    import_module(f"plugins.platforms.{platform}.adapter").register(_RegisteringContext(registry))

    profile = _resolve_audio_delivery_profile(platform)

    assert (profile.max_file_bytes, profile.safety_ratio) == (max_bytes, 0.85)
    assert profile.target_file_bytes == int(max_bytes * 0.85)
