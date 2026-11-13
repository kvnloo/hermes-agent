"""Upload metadata drives TTS packing without activating platform adapters.

Regression for kvnloo/hermes-agent#669. Adapted from the earlier fork draft
ff71cb668c6666c1c10ed52de54c6ddf7ad2112f, with baseline-compatible metadata
fixtures so the red run exercises the resolver rather than a missing keyword.
"""

from importlib import import_module

import pytest

from gateway import platform_registry as registry_module
from gateway.platform_registry import PlatformEntry, PlatformRegistry
from hermes_constants import hermes_home_key, reset_hermes_home_override, set_hermes_home_override
from tools.tts_tool_delivery import _pack_audio_files_for_delivery, _resolve_audio_delivery_profile

MIB = 1024 * 1024
GENERIC_MAX = 10 * MIB


def _forbidden(*_args, **_kwargs):
    pytest.fail("Metadata lookup must not construct adapters or probe/install dependencies")


def _entry(name, limit=0):
    entry = PlatformEntry(
        name=name, label=name, adapter_factory=_forbidden, check_fn=_forbidden,
        ensure_deps_fn=_forbidden, validate_config=_forbidden, is_connected=_forbidden)
    # Allow the same behavior tests to run against the base without the new field.
    entry.audio_upload_max_bytes = limit
    return entry


@pytest.fixture
def registry(monkeypatch):
    fresh = PlatformRegistry()
    monkeypatch.setattr(registry_module, "platform_registry", fresh)
    return fresh


def _chunk_files(tmp_path, count, size):
    paths = []
    for index in range(count):
        path = tmp_path / f"chunk{index}.ogg"
        with path.open("wb") as handle:
            handle.truncate(size)  # The packer needs sizes only, so use sparse files.
        paths.append(str(path))
    return paths


def test_platform_entry_accepts_optional_upload_default():
    assert PlatformEntry("pigeon", "Pigeon", _forbidden, _forbidden).audio_upload_max_bytes == 0
    entry = PlatformEntry(
        "pigeon", "Pigeon", _forbidden, _forbidden, audio_upload_max_bytes=30 * MIB)
    assert entry.audio_upload_max_bytes == 30 * MIB


def test_deferred_plugin_limit_drives_real_packer(registry, tmp_path):
    loaded = []
    scope = registry.current_scope_key()

    def load_pigeon():
        loaded.append("pigeon")
        registry.register(_entry("pigeon", 30 * MIB), scope=scope)

    registry.register_deferred("pigeon", load_pigeon, scope=scope)
    registry.register_deferred("unrelated", _forbidden, scope=scope)
    paths = _chunk_files(tmp_path, 3, 6 * MIB)
    profile = _resolve_audio_delivery_profile(" Pigeon ")

    # The generic cap would split these into three groups, not one.
    assert _pack_audio_files_for_delivery(paths, profile) == [paths]
    assert (profile.platform, profile.max_file_bytes, profile.safety_ratio) == ("pigeon", 30 * MIB, 0.85)
    assert loaded == ["pigeon"]


@pytest.mark.parametrize("ratio, expected", [(0.5, 0.5), (1, 1.0), (0, 0.85), (-1, 0.85),
                                            (1.5, 0.85), (True, 0.85), ("0.5", 0.85)])
def test_explicit_config_wins_and_ratio_validation_is_unchanged(registry, ratio, expected):
    registry.register(_entry("pigeon", 30 * MIB), scope=registry.current_scope_key())
    config = {"delivery_profiles": {"pigeon": {"max_file_bytes": 2 * MIB, "safety_ratio": ratio}}}
    profile = _resolve_audio_delivery_profile("pigeon", config)

    assert (profile.max_file_bytes, profile.safety_ratio) == (2 * MIB, expected)
    assert profile.target_file_bytes == int(2 * MIB * expected)


@pytest.mark.parametrize("declared", [None, 0, -1, True, False, "50MB", 2.5])
def test_invalid_metadata_uses_generic_default(registry, declared):
    registry.register(_entry("pigeon", declared), scope=registry.current_scope_key())
    profile = _resolve_audio_delivery_profile("pigeon")

    assert (profile.max_file_bytes, profile.safety_ratio) == (GENERIC_MAX, 0.85)


@pytest.mark.parametrize("override, expected", [(None, 30 * MIB), (0, GENERIC_MAX),
                                               (-1, GENERIC_MAX), (True, GENERIC_MAX),
                                               ("2MB", GENERIC_MAX)])
def test_null_override_keeps_metadata_and_invalid_override_keeps_generic_fallback(registry, override, expected):
    registry.register(_entry("pigeon", 30 * MIB), scope=registry.current_scope_key())
    config = {"delivery_profiles": {"pigeon": {"max_file_bytes": override}}}

    assert _resolve_audio_delivery_profile("pigeon", config).max_file_bytes == expected


def test_absent_metadata_and_unknown_platform_use_generic_default(registry):
    registry.register(PlatformEntry("pigeon", "Pigeon", _forbidden, _forbidden),
                      scope=registry.current_scope_key())
    for platform in ("pigeon", "nowhere", "", None):
        profile = _resolve_audio_delivery_profile(platform)
        assert (profile.max_file_bytes, profile.safety_ratio) == (GENERIC_MAX, 0.85)


def test_profiles_declare_independent_limits_without_cached_leakage(registry, tmp_path):
    limits = {"a": 20 * MIB, "b": 40 * MIB}
    for profile_name, limit in limits.items():
        registry.register(_entry("pigeon", limit), scope=hermes_home_key(tmp_path / profile_name))

    for profile_name in ("a", "b", "a"):
        token = set_hermes_home_override(tmp_path / profile_name)
        try:
            assert _resolve_audio_delivery_profile("pigeon").max_file_bytes == limits[profile_name]
        finally:
            reset_hermes_home_override(token)


class _RegisteringContext:
    """Only registration is permitted when reading a bundled platform's metadata."""

    def __init__(self, registry):
        self.registry = registry

    def register_platform(self, name, label, adapter_factory, check_fn, **fields):
        self.registry.register(
            PlatformEntry(name=name, label=label, adapter_factory=_forbidden, check_fn=_forbidden,
                          source="plugin", **{**fields, "ensure_deps_fn": _forbidden,
                                              "is_connected": _forbidden}),
            scope=self.registry.current_scope_key())


@pytest.mark.parametrize("platform, max_bytes", [("telegram", 50 * MIB), ("discord", 10 * MIB)])
def test_bundled_registrations_preserve_profiles_and_packing(registry, tmp_path, platform, max_bytes):
    import_module(f"plugins.platforms.{platform}.adapter").register(_RegisteringContext(registry))
    profile = _resolve_audio_delivery_profile(platform)
    paths = _chunk_files(tmp_path, 3, 6 * MIB)

    assert (profile.max_file_bytes, profile.safety_ratio) == (max_bytes, 0.85)
    assert profile.target_file_bytes == int(max_bytes * 0.85)
    expected = [paths] if platform == "telegram" else [[path] for path in paths]
    assert _pack_audio_files_for_delivery(paths, profile) == expected
