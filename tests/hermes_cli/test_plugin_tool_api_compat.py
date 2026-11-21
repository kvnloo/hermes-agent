"""A frozen args-only plugin tool keeps working through real discovery and dispatch.

``ToolRegistry.dispatch`` filters injected context kwargs by signature (#68318), and
direct registry tests pin that. This pins the composed path a real plugin takes:
discovery under an isolated home, ``ctx.register_tool`` into the profile scope, and
dispatch with today's context fields plus a future one.
"""

import json
import shutil
from pathlib import Path

import hermes_yaml as yaml

from hermes_cli.plugins import PluginManager
from hermes_constants import hermes_home_key
from tools.registry import registry

FIXTURE = Path(__file__).parent / "fixtures" / "plugin_compat_tool_legacy"
NAME = "legacy-tool-fixture"
CONTEXT = {"session_id": "legacy-session", "task_id": "legacy-task", "future_context_field": {"nested": 1}}


def _home(tmp_path, monkeypatch, label):
    hermes_home = tmp_path / label
    plugins_dir = hermes_home / "plugins"
    plugins_dir.mkdir(parents=True)
    shutil.copytree(FIXTURE, plugins_dir / NAME)
    (hermes_home / "config.yaml").write_text(
        yaml.safe_dump({"plugins": {"enabled": [NAME]}}), encoding="utf-8")
    empty_bundled = tmp_path / "bundled-plugins"
    empty_bundled.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(tmp_path / "os-home"))
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("HERMES_BUNDLED_PLUGINS", str(empty_bundled))
    return hermes_home


def test_args_only_plugin_tool_survives_discovery_and_scoped_dispatch(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch, "hermes-home")
    manager = PluginManager()
    manager.discover_and_load()
    loaded = manager._plugins[NAME]
    try:
        assert loaded.enabled is True
        assert loaded.error is None
        scope = manager.scope_key

        echoed = registry.dispatch("legacy_echo", {"text": "hi"}, scope=scope, **CONTEXT)
        assert json.loads(echoed) == {"echo": "hi"}
        assert loaded.module.calls == [{"text": "hi"}]

        probed = json.loads(registry.dispatch("legacy_context_probe", {}, scope=scope, **CONTEXT))
        assert set(CONTEXT) <= set(probed["kwargs"])

        other = hermes_home_key(tmp_path / "other-home")
        assert other != scope
        refused = json.loads(registry.dispatch("legacy_echo", {"text": "no"}, scope=other, **CONTEXT))
        assert "Unknown tool" in refused["error"]
        assert loaded.module.calls == [{"text": "hi"}]
    finally:
        assert manager.unload(NAME)

    gone = json.loads(registry.dispatch("legacy_echo", {"text": "late"}, scope=scope, **CONTEXT))
    assert "Unknown tool" in gone["error"]
    assert loaded.module.calls == [{"text": "hi"}]
