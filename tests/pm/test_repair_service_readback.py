"""Reporting consumer for owner PR #133030: unreadable is not verified repaired."""

import subprocess
from pathlib import Path

import pytest


@pytest.mark.platforms("linux")
@pytest.mark.parametrize("readback_fails", [False, True], ids=["readable-control", "unreadable"])
def test_failed_service_refresh_never_claims_verified_rewrite(tmp_path, monkeypatch, capsys, readback_fails):
    from hermes_cli import gateway
    from pm import cli

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(gateway, "PROJECT_ROOT", tmp_path / "checkout")
    unit = tmp_path / "gateway.service"
    poisoned = '[Service]\nExecStart=/synthetic/installs/key/environments/gen/workspace/.hermes/bin/hermes gateway run\n'
    unit.write_text(poisoned, encoding="utf-8")
    monkeypatch.setattr(gateway, "get_systemd_unit_path",
                        lambda system=False: tmp_path / "absent-system.service" if system else unit)
    monkeypatch.setattr(gateway, "get_launchd_plist_path", lambda: tmp_path / "absent.plist")
    refreshed = []

    def refresh(system=False):
        refreshed.append(system)
        return False  # The repair attempt leaves the original definition untouched.

    monkeypatch.setattr(gateway, "refresh_systemd_unit_if_needed", refresh)
    read_text = Path.read_text

    def readback(path, *args, **kwargs):
        if path == unit and refreshed and readback_fails:
            raise PermissionError("synthetic post-refresh readback failure")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", readback)

    def no_process(*args, **kwargs):
        raise AssertionError("reporting consumer must not execute service commands")

    monkeypatch.setattr(subprocess, "run", no_process)
    cli._heal_generation_launcher_service_units()

    assert refreshed == [False]
    assert read_text(unit, encoding="utf-8") == poisoned
    captured = capsys.readouterr()
    assert "✓ Rewrote" not in captured.out
