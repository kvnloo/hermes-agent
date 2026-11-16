"""Windows SCM enumeration failure regressions for NousResearch/hermes-agent#148204."""

from types import SimpleNamespace

import pytest

from hermes_cli import gateway


@pytest.mark.parametrize("error_kind", ["winerror5", "psutil"], ids=["openscmanager", "psutil"])
@pytest.mark.parametrize("stage", ["call", "before_first", "after_first"])
def test_denied_scm_enumeration_falls_back_to_process_only(monkeypatch, capsys, error_kind, stage):
    """SCM enumeration denial must not abort a PID-file-discovered ordinary gateway update."""
    import psutil
    from hermes_cli import gateway_windows

    monkeypatch.setattr(gateway_windows, "hermes_service_roots", lambda: (r"C:\hermes\hermes-agent",))
    seen = []

    error = (PermissionError(5, "Access is denied (originated from OpenSCManager)")
             if error_kind == "winerror5" else psutil.AccessDenied(0, "OpenSCManager"))

    def services():
        if stage == "after_first":
            # No service may be inspected until enumeration completes.
            yield SimpleNamespace(name=lambda: pytest.fail("partial SCM service inspected"))
        raise error

    def enumerate_services():
        seen.append("enumeration")
        if stage == "call":
            raise error
        return services()

    fake_psutil = SimpleNamespace(
        win_service_iter=enumerate_services,
        AccessDenied=psutil.AccessDenied,
        Process=lambda pid: pytest.fail(f"unexpected SCM ownership walk for {pid}"),
    )
    profile = SimpleNamespace(profile="default", pid=18480, create_time=18480.0)
    assert gateway.find_windows_gateway_services(
        psutil_module=fake_psutil, profile_processes=[profile],
    ) == []
    assert seen == ["enumeration"]
    assert "process-only gateway handling" in capsys.readouterr().err


def test_non_permission_scm_enumeration_error_still_aborts():
    """RPC failures are not proof that it is safe to bypass service ownership."""
    import psutil

    def broken_enumerator():
        raise OSError(1722, "RPC server unavailable")

    with pytest.raises(RuntimeError, match="SCM service enumeration failed"):
        gateway.find_windows_gateway_services(
            psutil_module=SimpleNamespace(
                win_service_iter=broken_enumerator, AccessDenied=psutil.AccessDenied,
            ),
            profile_processes=[],
        )


def test_owned_scm_service_inspection_access_denied_still_aborts(monkeypatch):
    """A denial inspecting a Hermes-owned service is not an enumeration denial."""
    import psutil
    from hermes_cli import gateway_windows

    monkeypatch.setattr(gateway_windows, "hermes_service_roots", lambda: (r"C:\hermes\hermes-agent",))

    def denied_status():
        raise psutil.AccessDenied(42, "HermesGateway")

    service = SimpleNamespace(name=lambda: "HermesGateway", status=denied_status)
    with pytest.raises(RuntimeError, match="SCM service enumeration failed") as caught:
        gateway.find_windows_gateway_services(
            psutil_module=SimpleNamespace(
                win_service_iter=lambda: iter([service]), AccessDenied=psutil.AccessDenied,
            ),
            profile_processes=[],
        )
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert "SCM service inspection failed" in str(caught.value.__cause__)


def test_denied_scm_enumeration_keeps_manual_gateway_in_update_inventory(monkeypatch, tmp_path, capsys):
    """Exercise the real updater discovery caller without stopping any process."""
    from hermes_cli import update_cmd_windows

    profile = SimpleNamespace(profile="default", path=tmp_path, pid=18480, create_time=18480.0)

    def denied_enumerator():
        raise PermissionError(5, "OpenSCManager")

    discover_services = gateway.find_windows_gateway_services
    fake_psutil = SimpleNamespace(win_service_iter=denied_enumerator)
    monkeypatch.setattr(gateway, "find_profile_gateway_processes", lambda **kwargs: [profile])
    monkeypatch.setattr(gateway, "find_gateway_pids", lambda **kwargs: [])
    monkeypatch.setattr(gateway, "find_windows_gateway_services", lambda **kwargs:
                        discover_services(psutil_module=fake_psutil, **kwargs))

    processes, services, service_pids, running = update_cmd_windows._discover_windows_gateways()

    assert processes == {profile.pid: profile}
    assert services == []
    assert service_pids == set()
    assert running == [profile.pid]
    assert "process-only gateway handling" in capsys.readouterr().err


def test_successful_scm_enumeration_retains_service_ownership(monkeypatch):
    from hermes_cli import gateway_windows

    monkeypatch.setattr(gateway_windows, "hermes_service_roots", lambda: ())
    profile = SimpleNamespace(profile="default", pid=20, create_time=20.0)
    service = SimpleNamespace(name=lambda: "HermesGateway", status=lambda: "running", pid=lambda: 10)

    def process(pid):
        return SimpleNamespace(
            pid=pid, create_time=lambda: float(pid), parents=lambda: [process(10)],
            children=lambda **kwargs: [process(20)],
        )

    found = gateway.find_windows_gateway_services(
        psutil_module=SimpleNamespace(win_service_iter=lambda: iter([service]), Process=process),
        profile_processes=[profile],
    )

    assert [(s.name, s.service_pid, s.gateway_pid) for s in found] == [("HermesGateway", 10, 20)]


@pytest.mark.platforms("posix")
def test_native_non_windows_scm_discovery_is_inert():
    assert gateway.find_windows_gateway_services() == []
