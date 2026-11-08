"""Native Windows regression: the supervised gateway launcher must survive a missing Python."""

import subprocess

import pytest

from hermes_cli import gateway_windows
from hermes_cli.gateway_runtime_service_identity import _vbs_identity


@pytest.mark.platforms("windows")
def test_missing_python_does_not_park_task_supervisor(monkeypatch, tmp_path):
    """WshShell.Run can return zero for an absent executable: this is not a clean gateway exit."""
    missing = tmp_path / "missing python.exe"
    monkeypatch.setattr(
        gateway_windows,
        "_resolve_detached_python",
        lambda _python: (str(missing), tmp_path, []),
    )
    script_text = gateway_windows._build_gateway_vbs_script(
        str(missing), str(tmp_path), str(tmp_path), ""
    )
    home, argv = _vbs_identity(script_text)
    assert home == str(tmp_path)
    assert argv == [str(missing), "-m", "hermes_cli.main", "gateway", "run"]

    script = tmp_path / "Hermes_Gateway.vbs"
    script.write_text(script_text, encoding="utf-16", newline="")
    launcher = subprocess.Popen(
        ["cscript.exe", "//B", "//Nologo", str(script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        # On the carrier head WshShell.Run of a missing exe returns 0, parking the task.
        # A supervised launcher must remain running to retry when the venv is restored.
        with pytest.raises(subprocess.TimeoutExpired):
            launcher.wait(timeout=2)
    finally:
        if launcher.poll() is None:
            launcher.kill()
        launcher.wait(timeout=5)
