"""A detached --replace restart cannot occupy systemd's RestartSec gap (#73480).

When the old unit's MainPID has exited but systemd is preparing its automatic
restart, is-active is not yet "active". The watcher must not start another
gateway that will race the scheduled unit for the Telegram long-poll.
"""

import pytest

from hermes_cli import gateway


@pytest.mark.platforms("linux")
def test_manual_gateway_refused_while_systemd_restart_is_pending(monkeypatch, capsys):
    monkeypatch.setattr(gateway, "_running_under_gateway_supervisor", lambda: False)
    monkeypatch.setattr(gateway, "_is_service_installed", lambda: True)
    monkeypatch.setattr(
        gateway, "get_gateway_runtime_snapshot",
        lambda: gateway.GatewayRuntimeSnapshot(
            manager="systemd (user)", service_installed=True,
            service_running=False, service_scope="user",
        ),
    )
    scopes = []

    def pending_unit(*, system=False):
        scopes.append(system)
        return {"ActiveState": "activating", "SubState": "auto-restart"}

    monkeypatch.setattr(gateway, "_read_systemd_unit_properties", pending_unit)

    with pytest.raises(SystemExit) as exit_info:
        gateway._guard_supervised_gateway_conflict()

    assert exit_info.value.code == 1
    assert scopes == [False]
    output = capsys.readouterr()
    assert "restart is pending" in output.out + output.err
