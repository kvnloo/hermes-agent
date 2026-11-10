"""Systemd's effective fatal-exit parking policy controls updater repair hints (#126362)."""

import subprocess

import pytest

from hermes_cli import update_cmd_fleet as fleet


@pytest.mark.platforms("linux")
@pytest.mark.parametrize(
    "scope,main_park,effective_park",
    [("user", False, "78"), ("system", False, "78"), ("system", True, "")],
)
def test_update_park_warning_uses_effective_systemd_policy(
    monkeypatch, tmp_path, capsys, scope, main_park, effective_park,
):
    from hermes_cli import gateway as gateway_cli

    service = "hermes-serve" if scope == "user" else "hermes-dashboard"
    unit_dir = tmp_path / scope
    unit_dir.mkdir()
    unit_file = unit_dir / f"{service}.service"
    fragment = "RestartPreventExitStatus=78\n" if main_park else ""
    unit_file.write_text(f"[Service]\nRestart=on-failure\n{fragment}", encoding="utf-8")
    dropin = unit_dir / f"{service}.service.d"
    dropin.mkdir()
    (dropin / "park.conf").write_text(
        f"[Service]\nRestartPreventExitStatus={effective_park}\n", encoding="utf-8",
    )
    monkeypatch.setattr(gateway_cli, "_SYSTEM_UNIT_DIR", unit_dir)
    monkeypatch.setattr(gateway_cli, "user_systemd_unit_dir", lambda: unit_dir)
    monkeypatch.setattr(fleet, "_needs_sudo", lambda scope: True)
    seen = []

    def show(cmd, *, timeout):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, f"RestartPreventExitStatus={effective_park}\n", "")

    monkeypatch.setattr(fleet, "_systemctl", show)
    fleet._repair_unit_without_fatal_exit_park(service, scope)

    assert ("lacks RestartPreventExitStatus=78" in capsys.readouterr().out) == (effective_park == "")
    prefix = ["systemctl"] if scope == "system" else ["systemctl", "--user"]
    assert seen == [prefix + ["show", f"{service}.service", "--property=RestartPreventExitStatus"]]
