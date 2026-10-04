"""The startup timing decision must use a unit's owning systemd manager (#132565)."""
from unittest.mock import mock_open
import subprocess

import pytest

from gateway import shutdown_forensics as sf
from gateway.restart import resolve_systemd_timeout_stop_sec


@pytest.mark.parametrize("short_system_budget", [False, True], ids=["aligned", "short"])
def test_alignment_uses_loaded_system_unit(monkeypatch, short_system_budget):
    required = resolve_systemd_timeout_stop_sec(180, 30)
    actual = required - 1 if short_system_budget else required
    monkeypatch.setenv("INVOCATION_ID", "synthetic-system-service")
    monkeypatch.setattr(sf, "open", mock_open(
        read_data="0::/system.slice/hermes-gateway.service\n"), raising=False)
    calls = []

    def systemctl_output(command, **kwargs):
        calls.append(command)
        assert command[0] == "systemctl" and "show" in command
        assert "hermes-gateway.service" in command
        output = ("LoadState=not-found\nTimeoutStopUSec=90s\n" if "--user" in command
                  else f"LoadState=loaded\nTimeoutStopUSec={actual}s\n")
        return subprocess.CompletedProcess(command, 0, output, "")

    monkeypatch.setattr(sf.subprocess, "run", systemctl_output)
    decision = sf.check_systemd_timing_alignment(180, 30)
    assert decision["timeout_stop_sec"] == actual
    assert decision["expected_min"] == required
    assert decision["mismatch"] is short_system_budget
    assert len(calls) == 2
