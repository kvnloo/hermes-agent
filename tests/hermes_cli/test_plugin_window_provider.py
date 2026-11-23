"""A plugin registers the cron decision-window provider through ``ctx``.

``ctx.register_window_provider(provider)`` mirrors ``register_context_engine``: one slot per
profile's plugin manager, leased so unload restores what was there. The cron tick resolves it
through ``cron.scheduler_window_gate.resolve_window_provider``. Design:
NousResearch/hermes-agent#158538. The plugin below is a synthetic fixture loaded through real
discovery with a temp ``HERMES_HOME``.
"""
from datetime import UTC, datetime

import hermes_yaml as yaml
import pytest

from cron.decision_window import ALWAYS_ANYTIME, WindowClass

PLUGIN = (
    "class FixedWindow:\n"
    "    def current(self, now):\n"
    "        return 'wind_down'\n\n"
    "def register(ctx):\n"
    "    ctx.register_window_provider(FixedWindow())\n"
)


@pytest.fixture
def plugin_home(tmp_path, monkeypatch):
    import hermes_cli.plugins as plugins_mod

    home = tmp_path / "hermes_test"
    plugin_dir = home / "plugins" / "window-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        yaml.safe_dump({"name": "window-plugin", "version": "0.1.0", "description": "synthetic"}))
    (plugin_dir / "__init__.py").write_text(PLUGIN)
    (home / "config.yaml").write_text(yaml.safe_dump({"plugins": {"enabled": ["window-plugin"]}}))
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(plugins_mod, "_plugin_manager", None)
    plugins_mod._reset_plugin_managers_for_tests()
    yield home
    plugins_mod._reset_plugin_managers_for_tests()


def test_a_plugin_registers_the_window_provider_the_tick_uses(plugin_home):
    from cron.scheduler_window_gate import resolve_window_provider

    provider = resolve_window_provider()
    assert provider is not ALWAYS_ANYTIME
    now = datetime(2026, 1, 5, 21, 0, tzinfo=UTC)
    assert provider.current(now) == WindowClass.WIND_DOWN.value


def test_without_a_plugin_every_window_is_open(tmp_path, monkeypatch):
    import hermes_cli.plugins as plugins_mod
    from cron.scheduler_window_gate import resolve_window_provider

    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "empty"))
    monkeypatch.setattr(plugins_mod, "_plugin_manager", None)
    plugins_mod._reset_plugin_managers_for_tests()
    try:
        assert resolve_window_provider() is ALWAYS_ANYTIME
    finally:
        plugins_mod._reset_plugin_managers_for_tests()


def test_a_second_provider_is_refused(plugin_home):
    import hermes_cli.plugins as plugins_mod

    manager = plugins_mod.get_plugin_manager()
    manager.discover_and_load()
    first = plugins_mod.get_plugin_window_provider()
    ctx = plugins_mod.PluginContext(
        plugins_mod.PluginManifest(name="second", source="user"), manager)

    class Other:
        def current(self, now):
            return "peak"

    assert ctx.register_window_provider(Other()) is None
    assert plugins_mod.get_plugin_window_provider() is first


def test_unloading_the_plugin_frees_the_slot(plugin_home):
    import hermes_cli.plugins as plugins_mod

    manager = plugins_mod.get_plugin_manager()
    manager.discover_and_load()
    assert manager._window_provider is not None
    manager.unload("window-plugin")
    assert manager._window_provider is None


def test_an_object_without_current_is_refused(plugin_home):
    import hermes_cli.plugins as plugins_mod

    manager = plugins_mod.get_plugin_manager()
    ctx = plugins_mod.PluginContext(plugins_mod.PluginManifest(name="bad", source="user"), manager)
    with pytest.raises(TypeError, match="current"):
        ctx.register_window_provider(object())
