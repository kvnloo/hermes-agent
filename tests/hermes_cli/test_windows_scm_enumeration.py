"""Windows SCM enumeration failure regressions for NousResearch/hermes-agent#148204."""

from types import SimpleNamespace

import pytest

from hermes_cli import gateway


@pytest.mark.platforms("windows")
@pytest.mark.parametrize("error_kind", ["winerror5", "psutil"], ids=["openscmanager", "psutil"])
@pytest.mark.parametrize("partial", [False, True], ids=["before_first", "after_first"])
def test_denied_scm_enumeration_falls_back_to_process_only(monkeypatch, capsys, error_kind, partial):
    """SCM enumeration denial must not abort a PID-file-discovered ordinary gateway update."""
    import psutil
    from hermes_cli import gateway_windows

    monkeypatch.setattr(gateway_windows, "hermes_service_roots", lambda: (r"C:\hermes\hermes-agent",))
    seen = []

    def enumerate_services():
        seen.append("enumeration")
        if partial:
            # A partial enumeration must not be mistaken for complete service ownership.
            yield SimpleNamespace(name=lambda: "HermesGateway", status=lambda: "running", pid=lambda: 42)
        if error_kind == "winerror5":
            raise PermissionError(5, "Access is denied (originated from OpenSCManager)")
        raise psutil.AccessDenied(0, "OpenSCManager")

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


@pytest.mark.platforms("windows")
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


@pytest.mark.platforms("windows")
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
