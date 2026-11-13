"""Activation reports actual tool ownership, not manifest promises. Regression for #671."""

from pathlib import Path

import pytest

import hermes_yaml as yaml
from hermes_cli.plugins import PluginManager
from hermes_cli.plugins_activation import plugin_activation_summary
from tools.registry import registry


def _plugin(root, name, body, provides_tools=()):
    directory = root / name
    directory.mkdir()
    (directory / "plugin.yaml").write_text(
        yaml.safe_dump({"name": name, "version": "1.0", "provides_tools": list(provides_tools)}),
        encoding="utf-8",
    )
    (directory / "__init__.py").write_text(f"def register(ctx):\n{body}", encoding="utf-8")


def _register(tool, toolset):
    schema = {"name": tool, "description": "probe", "parameters": {"type": "object", "properties": {}}}
    return (
        f"    ctx.register_tool(name={tool!r}, toolset={toolset!r}, schema={schema!r},\n"
        "                      handler=lambda args, **kw: '{}')\n"
    )


@pytest.fixture
def plugins(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    root = home / "plugins"
    root.mkdir(parents=True)
    _plugin(root, "a-owner", _register("shared_tool", "owner_ts") + _register("undeclared_tool", "owner_ts"))
    _plugin(root, "b-claimer", _register("shared_tool", "claimer_ts"), ["shared_tool"])
    _plugin(root, "c-phantom", "    pass\n", ["phantom_tool"])
    (home / "config.yaml").write_text(
        yaml.safe_dump({"plugins": {"enabled": ["a-owner", "b-claimer", "c-phantom"]}}),
        encoding="utf-8",
    )
    bundled = tmp_path / "bundled-plugins"
    bundled.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_BUNDLED_PLUGINS", str(bundled))
    monkeypatch.chdir(tmp_path)
    manager = PluginManager()
    events = []
    manager.on_plugin_loaded(events.extend)
    try:
        manager.discover_and_load()
        for key in ("a-owner", "b-claimer", "c-phantom"):
            assert manager._plugins[key].enabled
            assert not manager._plugins[key].error
        yield manager, events
    finally:
        manager.unload()


def _tools(manager, key):
    return plugin_activation_summary(manager, key)["deferred"].get("tools", [])


def test_manifest_only_tool_is_absent_from_activation_and_loaded_event(plugins):
    manager, events = plugins
    assert manager._plugins["c-phantom"].manifest.provides_tools == ["phantom_tool"]
    assert registry.get_entry("phantom_tool", scope=manager.scope_key) is None
    assert _tools(manager, "c-phantom") == []
    summary = next(event for event in events if event["key"] == "c-phantom")
    assert "tools" not in summary["deferred"]


def test_registered_but_undeclared_tools_appear(plugins):
    manager, events = plugins
    assert manager._plugins["a-owner"].manifest.provides_tools == []
    assert _tools(manager, "a-owner") == ["shared_tool", "undeclared_tool"]
    assert registry.get_entry("undeclared_tool", scope=manager.scope_key).handler({}) == "{}"
    summary = next(event for event in events if event["key"] == "a-owner")
    assert summary["deferred"]["tools"] == ["shared_tool", "undeclared_tool"]


def test_failed_same_name_registration_does_not_claim_another_plugins_tool(plugins):
    manager, events = plugins
    assert manager._plugins["b-claimer"].tools_registered == []
    assert _tools(manager, "b-claimer") == []
    entry = registry.get_entry("shared_tool", scope=manager.scope_key)
    assert entry.toolset == "owner_ts"
    assert entry.handler({}) == "{}"
    summary = next(event for event in events if event["key"] == "b-claimer")
    assert "tools" not in summary["deferred"]


def test_unload_and_rediscovery_leave_no_phantom_ownership(plugins):
    manager, events = plugins
    assert manager.unload("b-claimer")
    assert registry.get_entry("shared_tool", scope=manager.scope_key).toolset == "owner_ts"
    assert _tools(manager, "b-claimer") == []
    assert manager.unload()
    for tool in ("shared_tool", "undeclared_tool", "phantom_tool"):
        assert registry.get_entry(tool, scope=manager.scope_key) is None
    assert not manager._ownership_ledger
    events.clear()
    manager.discover_and_load(force=True)
    assert _tools(manager, "c-phantom") == []
    assert _tools(manager, "b-claimer") == []
    assert _tools(manager, "a-owner") == ["shared_tool", "undeclared_tool"]
    assert registry.get_entry("shared_tool", scope=manager.scope_key).toolset == "owner_ts"
    assert {event["key"] for event in events} == {"a-owner", "b-claimer", "c-phantom"}
