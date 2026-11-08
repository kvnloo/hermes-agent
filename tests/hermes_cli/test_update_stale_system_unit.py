"""Regression for #151375: update must not restart an unrefreshed system unit."""

import subprocess

import pytest

from hermes_cli import gateway
from hermes_cli import update_cmd_fleet as fleet


@pytest.mark.platforms("linux")
def test_nonroot_update_does_not_restart_stale_system_unit(tmp_path, monkeypatch, capsys):
    legacy = (
        "[Service]\n"
        "ExecStart=/srv/hermes/venv/bin/python -m hermes_cli.main gateway run --replace\n"
    )
    expected = "[Service]\nExecStart=/srv/hermes/.hermes/bin/hermes gateway run\n"
    unit = tmp_path / "hermes-gateway.service"
    unit.write_text(legacy, encoding="utf-8")

    monkeypatch.setattr(gateway, "get_service_name", lambda: "hermes-gateway")
    monkeypatch.setattr(gateway, "get_systemd_unit_path", lambda system=False: unit)
    monkeypatch.setattr(gateway, "_sync_hermes_home_from_systemd_unit", lambda system=False: None)
    monkeypatch.setattr(gateway, "_read_systemd_user_from_unit", lambda path: "serviceuser")
    monkeypatch.setattr(gateway, "generate_systemd_unit", lambda system=False, run_as_user=None: expected)
    monkeypatch.setattr(fleet, "_systemd_unit_owned_by_update", lambda *args: True)
    monkeypatch.setattr(fleet, "_repair_unit_without_fatal_exit_park", lambda *args: None)
    monkeypatch.setattr(fleet, "_needs_sudo", lambda scope: True)
    monkeypatch.setattr(fleet, "_resolve_manage_cmd", lambda *args: ["sudo", "-n", "systemctl"])
    monkeypatch.setattr(fleet, "_wait_for_service_active", lambda *args, **kwargs: True)
    calls = []

    def systemctl(cmd, *, timeout):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "active", "")

    monkeypatch.setattr(fleet, "_systemctl", systemctl)
    assert gateway.systemd_unit_is_current(system=True) is False

    restarted, failed = [], []
    fleet._restart_one_systemd_gateway_unit(
        "hermes-gateway", scope="system", scope_cmd=["systemctl"], drain_budget=5,
        _manage_cmd_cache={}, restarted_services=restarted, failed_or_stale_units=failed,
    )

    assert restarted == []
    assert failed == ["hermes-gateway"]
    assert calls == [["systemctl", "is-active", "hermes-gateway"]]
    assert unit.read_text(encoding="utf-8") == legacy
    output = capsys.readouterr().out
    assert "restart skipped" in output
    assert "gateway restart --system" in output
