"""A frozen narrow ``async def`` hook keeps working through real plugin discovery.

Narrowing and coroutine resolution have unit coverage on hand-built hook state
(#12449); this pins the path a published plugin takes: discovery under an isolated
home, then both ``invoke_hook`` and ``ainvoke_hook`` with an additive payload field.
"""

import asyncio
import shutil
from pathlib import Path

import hermes_yaml as yaml

from hermes_cli.plugins import PluginManager

FIXTURE = Path(__file__).parent / "fixtures" / "plugin_compat_async_legacy"
NAME = "async-legacy-contract-fixture"
PAYLOAD = {"session_id": "async-session", "resumed": True, "future_additive_field": {"nested": "value"}}


def test_async_narrow_hook_runs_once_per_invocation_on_both_paths(tmp_path, monkeypatch):
    hermes_home = tmp_path / "hermes-home"
    plugins_dir = hermes_home / "plugins"
    plugins_dir.mkdir(parents=True)
    shutil.copytree(FIXTURE, plugins_dir / NAME)
    (hermes_home / "config.yaml").write_text(
        yaml.safe_dump({"plugins": {"enabled": [NAME]}}), encoding="utf-8")
    empty_bundled = tmp_path / "bundled-plugins"
    empty_bundled.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path / "os-home"))
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("HERMES_BUNDLED_PLUGINS", str(empty_bundled))

    manager = PluginManager()
    manager.discover_and_load()
    loaded = manager._plugins[NAME]
    try:
        assert loaded.enabled is True
        assert loaded.error is None
        assert "on_session_start" in loaded.hooks_registered

        sync_results = manager.invoke_hook("on_session_start", **PAYLOAD)
        async_results = asyncio.run(manager.ainvoke_hook("on_session_start", **PAYLOAD))

        for results in (sync_results, async_results):
            assert results[0] == {"async_legacy_session_id": "async-session"}
            assert set(PAYLOAD) <= set(results[1]["observed_fields"])
            assert len(results) == 2
        assert loaded.module.received_sessions == ["async-session", "async-session"]
    finally:
        assert manager.unload(NAME)

    assert manager.invoke_hook("on_session_start", **PAYLOAD) == []
