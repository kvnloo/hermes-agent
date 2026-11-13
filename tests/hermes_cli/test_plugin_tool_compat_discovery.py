"""Pin the frozen args-only tool ABI through real plugin discovery for #674."""

import json
import shutil
from pathlib import Path

import hermes_yaml as yaml

from hermes_cli.plugins import PluginManager
from hermes_constants import hermes_home_key
from tools.registry import registry


FIXTURE = Path(__file__).parent / "fixtures" / "plugin_compat_tool_legacy"
NAME = "legacy-tool-fixture"
CONTEXT = {
    "session_id": "legacy-session",
    "task_id": "legacy-task",
    "future_context_field": {"nested": 1},
}


def test_args_only_plugin_tool_survives_discovery_and_scoped_dispatch(
    tmp_path, monkeypatch
):
    hermes_home = tmp_path / "hermes-home"
    plugins_dir = hermes_home / "plugins"
    plugins_dir.mkdir(parents=True)
    shutil.copytree(FIXTURE, plugins_dir / NAME)
    (hermes_home / "config.yaml").write_text(
        yaml.safe_dump({"plugins": {"enabled": [NAME]}}), encoding="utf-8"
    )
    empty_bundled = tmp_path / "bundled-plugins"
    empty_bundled.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path / "os-home"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "os-home")
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("HERMES_BUNDLED_PLUGINS", str(empty_bundled))

    manager = PluginManager()
    try:
        manager.discover_and_load()
        loaded = manager._plugins[NAME]
        assert loaded.enabled is True
        assert loaded.error is None
        assert loaded.module is not None
        scope = manager.scope_key
        assert scope == hermes_home_key(hermes_home)

        probed = registry.dispatch("legacy_context_probe", {}, scope=scope, **CONTEXT)
        assert json.loads(probed) == {"kwargs": sorted(CONTEXT)}

        echoed = registry.dispatch("legacy_echo", {"text": "hi"}, scope=scope, **CONTEXT)
        assert json.loads(echoed) == {"echo": "hi"}
        assert loaded.module.calls == [{"text": "hi"}]

        other = hermes_home_key(tmp_path / "other-home")
        assert other != scope
        for tool in ("legacy_echo", "legacy_context_probe"):
            refused = registry.dispatch(tool, {"text": "no"}, scope=other, **CONTEXT)
            assert "Unknown tool" in json.loads(refused)["error"]
        assert loaded.module.calls == [{"text": "hi"}]
    finally:
        assert manager.unload(NAME)

    for tool in ("legacy_echo", "legacy_context_probe"):
        gone = registry.dispatch(tool, {"text": "late"}, scope=scope, **CONTEXT)
        assert "Unknown tool" in json.loads(gone)["error"]
        assert registry.get_entry(tool, scope=scope) is None
    assert loaded.module.calls == [{"text": "hi"}]
