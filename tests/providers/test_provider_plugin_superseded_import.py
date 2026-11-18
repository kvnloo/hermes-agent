"""Regression for #156899: a slower old import must not undo a newer provider-plugin release."""

from __future__ import annotations

import os
import sys
import threading
import types


def test_slow_old_import_cannot_overwrite_newer_published_release(tmp_path, monkeypatch):
    import providers
    from providers import plugin_reload

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    plugin = tmp_path / "plugins" / "demo-superseded"
    plugin.mkdir(parents=True)
    gate_name = "_demo_superseded_import_gate"
    gate = types.ModuleType(gate_name)
    gate.old_started = threading.Event()
    gate.release_old = threading.Event()
    monkeypatch.setitem(sys.modules, gate_name, gate)
    layer = providers._HomeLayer()
    base_name = providers._user_module_name(plugin, str(tmp_path))

    def write_release(version: int) -> None:
        (plugin / "plugin.yaml").write_text(
            f"name: demo-superseded\nkind: model-provider\nversion: {version}.0\n"
        )
        wait = (f"import {gate_name} as gate\n"
                "gate.old_started.set()\n"
                "gate.release_old.wait()\n") if version == 1 else ""
        (plugin / "__init__.py").write_text(
            "from providers import register_provider\n"
            "from providers.base import ProviderProfile\n"
            + wait
            + f'register_provider(ProviderProfile(name="demo-superseded", '
              f'base_url="process://v{version}", auth_type="external_process"))\n'
        )
        # Ensure two actual tree fingerprints even on coarse-mtime filesystems.
        stamp = (version + 1) * 10**12
        for path in (plugin / "plugin.yaml", plugin / "__init__.py"):
            os.utime(path, ns=(stamp, stamp))

    def scan() -> None:
        token = providers._REGISTRATION_TARGET.set(layer)
        try:
            plugin_reload.import_into_layer(plugin, "user", base_name)
        finally:
            providers._REGISTRATION_TARGET.reset(token)

    write_release(1)
    older = threading.Thread(target=scan, daemon=True)
    older.start()
    try:
        assert gate.old_started.wait(10), "the old plugin never entered its import"
        write_release(2)
        scan()  # v2 finishes and publishes while v1 is still inside its import
        assert layer.registry["demo-superseded"].base_url == "process://v2"
    finally:
        gate.release_old.set()
        older.join(10)
        for name in list(sys.modules):
            if name.startswith(base_name + "_"):
                sys.modules.pop(name, None)

    assert not older.is_alive()
    # On the carrier head, v1's late _publish replaces v2; the new version must stay live.
    assert layer.registry["demo-superseded"].base_url == "process://v2"
