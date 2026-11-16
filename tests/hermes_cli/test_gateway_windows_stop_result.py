"""Windows stop --all must count real stops, not successful service calls (#156589)."""

from contextlib import nullcontext
from types import SimpleNamespace

from hermes_cli import gateway, gateway_windows


def test_stop_all_windows_counts_only_a_running_scheduled_task(monkeypatch, capsys):
    # Keep the production Windows stop and CLI dispatch; stub only host/OS boundaries.
    monkeypatch.setattr(gateway_windows, "_assert_windows", lambda: None)
    monkeypatch.setattr(gateway_windows, "_clear_start_attestation", lambda: None)
    monkeypatch.setattr("gateway.status.get_running_pid", lambda: None)
    monkeypatch.setattr(gateway_windows, "_collect_gateway_stop_pids", lambda pid=None: [])
    monkeypatch.setattr(gateway_windows, "_gateway_pid_identities", lambda pids: {})
    monkeypatch.setattr(gateway_windows, "_force_terminate_known_gateway_pids", lambda ids: 0)
    monkeypatch.setattr(gateway_windows, "is_task_registered", lambda: True)
    monkeypatch.setattr(gateway_windows, "get_task_name", lambda: "HermesGateway")

    monkeypatch.setattr(gateway, "_refuse_from_inside_gateway", lambda *a, **k: None)
    monkeypatch.setattr("hermes_cli.gateway_profile_lifecycle.profile_lifecycle",
                        lambda verb, args: False)
    monkeypatch.setattr("hermes_cli.gateway_profile_lifecycle.host_scope_for_all_verb",
                        lambda owner: nullcontext())
    monkeypatch.setattr("hermes_cli.gateway_lifecycle_guards.refuse_while_sessions_live",
                        lambda *a, **k: None)
    monkeypatch.setattr(gateway, "_dispatch_all_via_service_manager_if_s6", lambda action: False)
    monkeypatch.setattr(gateway, "_host_multiplexer_for_all_verb", lambda: None)
    monkeypatch.setattr(gateway, "_installed_service_kind", lambda: "windows")
    monkeypatch.setattr(gateway, "_gw_windows", lambda: gateway_windows)
    monkeypatch.setattr(gateway, "kill_gateway_processes", lambda **kw: 0)

    # A successful /End counts one; an installed but idle task counts zero.
    # On base the second case incorrectly reports "Stopped 1".
    for code, expected in (
        (0, "✓ Stopped 1 gateway process(es) across all profiles"),
        (1, "✗ No gateway processes found"),
    ):
        def schtasks(args):
            assert args == ["/End", "/TN", "HermesGateway"]
            return code, "", "ERROR: The task is not running." if code else ""

        monkeypatch.setattr(gateway_windows, "_exec_schtasks", schtasks)
        gateway._cmd_stop(SimpleNamespace(all=True, system=False))
        output = capsys.readouterr().out
        assert expected in output
        if code:
            assert "✗ No gateway was running" in output
            assert "Stopped 1 gateway process(es)" not in output
