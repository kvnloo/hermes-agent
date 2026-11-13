"""Regression for #154727: dashboard-only packages need no Python entry point."""

import json

from hermes_cli.plugin_validate import validate_plugin_dir
from hermes_cli.plugins import PluginManager, PluginManifest


def test_dashboard_only_plugin_validates_and_loads_without_python_entrypoint(tmp_path):
    home = tmp_path / "home"
    plugin_dir = home / "plugins" / "fixture-dashboard"
    dashboard = plugin_dir / "dashboard"
    dashboard.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        "name: fixture-dashboard\n"
        "version: 1.0.0\n"
        "description: Dashboard tab without Python code\n"
        "kind: standalone\n",
        encoding="utf-8",
    )
    (dashboard / "manifest.json").write_text(json.dumps({
        "name": "fixture-dashboard",
        "version": "1.0.0",
        "label": "Dashboard Fixture",
        "tab": {"path": "/fixture-dashboard"},
        "entry": "dist/index.js",
    }), encoding="utf-8")

    manager = PluginManager(scope_key=str(home))
    manager._load_plugin(PluginManifest(
        name="fixture-dashboard", version="1.0.0",
        source="user", path=str(plugin_dir),
    ))
    loaded = manager._plugins["fixture-dashboard"]
    assert loaded.enabled, loaded.error
    assert loaded.error is None

    report = validate_plugin_dir(plugin_dir)
    assert report.ok, report.failures
    assert ("loadable", True, "entry: dashboard/manifest.json") in report.checks
