"""Regression for NousResearch/hermes-agent#152202: headless plugin update consent."""

from argparse import ArgumentParser
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from hermes_cli import plugins_cmd, plugins_cmd_catalog
from hermes_cli.plugins_transaction import _refresh_declared_dependencies
from hermes_cli.subcommands.plugins import build_plugins_parser


def test_named_update_yes_deps_reaches_command(monkeypatch):
    parser = ArgumentParser()
    build_plugins_parser(parser.add_subparsers(dest="command"), cmd_plugins=lambda _: None)
    args = parser.parse_args(["plugins", "update", "homeassistant", "--yes-deps"])
    calls = []
    monkeypatch.setattr(plugins_cmd, "cmd_update", lambda name, **kw: calls.append((name, kw)))

    plugins_cmd.plugins_command(args)

    assert calls == [("homeassistant", {"force": False, "yes_deps": True})]


def test_update_new_python_deps_headless_flag(tmp_path, monkeypatch):
    target = tmp_path / "homeassistant"
    staged = tmp_path / "staged"
    target.mkdir()
    staged.mkdir()
    (target / "pyproject.toml").write_text(
        '[project]\nname = "homeassistant"\nversion = "0.1.0"\ndependencies = []\n', encoding="utf-8"
    )
    (staged / "pyproject.toml").write_text(
        '[project]\nname = "homeassistant"\nversion = "0.1.1"\ndependencies = ["tzdata>=2025.3"]\n',
        encoding="utf-8",
    )
    from pm import workspace

    monkeypatch.setattr(workspace, "enabled_plugin_dirs", lambda **kw: [target.resolve()])
    monkeypatch.setattr(plugins_cmd, "_consent_python_deps", lambda *a, **kw: pytest.fail("TTY prompt"))
    with pytest.raises(plugins_cmd.PluginOperationError, match="run .*plugins update"):
        _refresh_declared_dependencies(target, staged, {"name": "homeassistant"}, interactive=False)

    _refresh_declared_dependencies(target, staged, {"name": "homeassistant"},
                                   interactive=False, assume_deps_consent=True)


def test_catalog_yes_deps_does_not_approve_other_surfaces(monkeypatch):
    approvals = []

    def fake_repin(_target, _sidecar, *, consent_cb, assume_deps_consent, **kwargs):
        assert assume_deps_consent is True
        approvals.append(consent_cb({"python_dependencies": ["tzdata>=2025.3"]}))
        approvals.append(consent_cb({"python_dependencies": ["tzdata>=2025.3"], "tools": ["new_tool"]}))
        return plugins_cmd_catalog.RepinResult("f" * 40, False, "homeassistant", [])

    monkeypatch.setattr(plugins_cmd_catalog, "repin_catalog_plugin", fake_repin)
    monkeypatch.setattr(plugins_cmd, "_is_tty", lambda: False)
    console = Console(file=StringIO(), force_terminal=False)
    plugins_cmd_catalog.cmd_update_catalog("homeassistant", Path("homeassistant"), {}, console,
                                          interactive=False, assume_deps_consent=True)
    assert approvals == [True, False]
