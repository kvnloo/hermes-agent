"""Regression for #154335: MSIX login tasks must enter through package identity."""

from pathlib import Path

import pytest

from hermes_cli import gateway_windows
from hermes_cli.gateway_runtime_service_identity import _vbs_identity


_PACKAGE_PYTHON = (
    r"C:\Program Files\WindowsApps\NousResearchInc.HermesAgent_2026.7512.1650.0_x64__sznbd6dv1j3v4"
    r"\app\resources\agent-payload\tools\python-3.14\python.exe"
)
_ALIAS = r"C:\Users\Sam\AppData\Local\Microsoft\WindowsApps\hermes.exe"
_HOME = r"C:\Users\Sam\AppData\Local\hermes"


def _package_task(monkeypatch, alias_is_file):
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\Sam\AppData\Local")
    monkeypatch.setattr(
        gateway_windows, "_resolve_detached_python",
        lambda executable: (_PACKAGE_PYTHON, Path(r"C:\Program Files\WindowsApps\bundle"), []),
    )
    monkeypatch.setattr(Path, "is_file", lambda path: alias_is_file)
    return gateway_windows._build_gateway_vbs_script(
        _PACKAGE_PYTHON, _HOME, _HOME, "--profile work",
    )


def test_msix_login_gateway_activates_through_package_alias(monkeypatch):
    """A Scheduled Task lacks the package identity required by bundled Python."""
    script = _package_task(monkeypatch, alias_is_file=True)
    configured, argv = _vbs_identity(script)
    assert configured == _HOME
    assert argv == [_ALIAS, "--profile", "work", "gateway", "run"]
    assert "sh.Run" in script and ", 0, False" in script


def test_msix_login_gateway_refuses_missing_alias(monkeypatch):
    """An absent/disabled execution alias cannot silently register a dead task."""
    with pytest.raises(RuntimeError, match="MSIX execution alias is missing"):
        _package_task(monkeypatch, alias_is_file=False)
