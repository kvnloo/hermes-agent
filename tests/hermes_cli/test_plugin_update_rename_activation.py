"""Catalog re-pins can rename providers; activate the published name, not the removed one.

Regression for #153300: CLI, batch, and auto-apply must follow a renamed catalog plugin.
"""

from __future__ import annotations

from io import StringIO
from types import SimpleNamespace

from rich.console import Console


def test_catalog_rename_activates_published_name_on_each_update_surface(tmp_path, monkeypatch):
    from hermes_cli import (
        plugins_activation,
        plugins_auto_update,
        plugins_cmd,
        plugins_cmd_catalog,
        plugins_cmd_update,
        plugins_cmd_update_all,
    )

    old = tmp_path / "old-provider"
    new = tmp_path / "new-provider"
    old.mkdir()
    new.mkdir()
    (new / "plugin.yaml").write_text(
        "name: new-provider\nkind: model-provider\nversion: 2.0.0\n", encoding="utf-8"
    )
    console = Console(file=StringIO(), color_system=None)

    # Publication is external; the catalog command must retain its published name.
    monkeypatch.setattr(
        plugins_cmd_catalog,
        "repin_catalog_plugin",
        lambda *_args, **_kwargs: plugins_cmd_catalog.RepinResult(
            "b" * 40, True, "new-provider", []
        ),
    )
    updated = plugins_cmd_catalog.cmd_update_catalog(
        "old-provider", old, {"catalog_name": "demo"}, console, interactive=False
    )
    assert updated == "new-provider"

    # Exercise the real CLI, batch, and gateway auto-apply activation call sites.
    monkeypatch.setattr(plugins_cmd_update, "update_one", lambda *_args, **_kwargs: updated)
    monkeypatch.setattr(plugins_cmd, "_console", lambda: console)
    monkeypatch.setattr(plugins_cmd, "_plugins_dir", lambda: tmp_path)
    monkeypatch.setattr(plugins_cmd, "_require_installed_plugin", lambda *_args: old)
    monkeypatch.setattr(plugins_cmd, "_user_installed_plugin_dir", lambda _name: old)

    activated: list[str] = []
    monkeypatch.setattr(
        plugins_activation, "report_activation", lambda _console, name: activated.append(name)
    )
    monkeypatch.setattr(
        plugins_activation, "load_and_go_live", lambda name: activated.append(name)
    )

    plugins_cmd_update.cmd_update("old-provider", interactive=False)
    row = SimpleNamespace(name="old-provider", current="a" * 40, latest="b" * 40)
    assert plugins_cmd_update_all._update_one(row, console, interactive=False)[0] == "updated"
    plugins_auto_update.apply_unattended("old-provider")

    assert activated == ["new-provider"] * 3
