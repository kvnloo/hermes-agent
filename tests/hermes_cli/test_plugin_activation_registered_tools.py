"""The activation summary names the tools a plugin registered, not the ones it declared.

``plugin_activation_summary`` reads the ownership ledger, but it also unioned
``manifest.provides_tools`` into ``deferred.tools``. A plugin that declares a tool and
registers nothing (or loses a same-name registration to another plugin) then reported a
tool as arriving next session that never will.
"""

from __future__ import annotations

import hermes_yaml as yaml

from hermes_cli.plugins import PluginManager
from hermes_cli.plugins_activation import plugin_activation_summary
from tools.registry import registry

SCHEMA = "{{'name': '{0}', 'description': 'probe', 'parameters': {{'type': 'object', 'properties': {{}}}}}}"


def _plugin(plugins_dir, name, body, provides_tools=()):
    d = plugins_dir / name
    d.mkdir()
    manifest = {"name": name, "version": "1.0"}
    if provides_tools:
        manifest["provides_tools"] = list(provides_tools)
    (d / "plugin.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (d / "__init__.py").write_text(f"def register(ctx):\n{body}", encoding="utf-8")


def _register(tool, toolset):
    return (f"    ctx.register_tool(name='{tool}', toolset='{toolset}', handler=lambda args, **kw: '{{}}',\n"
            f"                      schema={SCHEMA.format(tool)})\n")


def _manager(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    plugins_dir = home / "plugins"
    plugins_dir.mkdir(parents=True)
    _plugin(plugins_dir, "a-owner", _register("shared_tool", "owner_ts") + _register("undeclared_tool", "owner_ts"))
    _plugin(plugins_dir, "b-claimer", _register("shared_tool", "claimer_ts"), provides_tools=["shared_tool"])
    _plugin(plugins_dir, "c-phantom", "    pass\n", provides_tools=["phantom_tool"])
    (home / "config.yaml").write_text(
        yaml.safe_dump({"plugins": {"enabled": ["a-owner", "b-claimer", "c-phantom"]}}), encoding="utf-8")
    bundled = tmp_path / "bundled-plugins"
    bundled.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(tmp_path / "os-home"))
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_BUNDLED_PLUGINS", str(bundled))
    manager = PluginManager()
    manager.discover_and_load()
    return manager


def _deferred_tools(manager, key):
    return plugin_activation_summary(manager, key)["deferred"].get("tools", [])


def test_activation_lists_registered_tools_and_never_manifest_promises(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    try:
        assert _deferred_tools(manager, "c-phantom") == []
        assert _deferred_tools(manager, "a-owner") == ["shared_tool", "undeclared_tool"]
        assert _deferred_tools(manager, "b-claimer") == []
        assert registry.get_entry("shared_tool", scope=manager.scope_key).toolset == "owner_ts"
    finally:
        for key in ("a-owner", "b-claimer", "c-phantom"):
            manager.unload(key)
    assert registry.get_entry("shared_tool", scope=manager.scope_key) is None


def test_rediscovery_after_unload_leaves_no_phantom_ownership(tmp_path, monkeypatch):
    first = _manager(tmp_path, monkeypatch)
    for key in ("a-owner", "b-claimer", "c-phantom"):
        first.unload(key)

    second = PluginManager()
    second.discover_and_load()
    try:
        assert _deferred_tools(second, "c-phantom") == []
        assert _deferred_tools(second, "b-claimer") == []
        assert _deferred_tools(second, "a-owner") == ["shared_tool", "undeclared_tool"]
    finally:
        for key in ("a-owner", "b-claimer", "c-phantom"):
            second.unload(key)
