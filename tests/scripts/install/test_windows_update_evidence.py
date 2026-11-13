"""A failed Windows packaged update keeps App Installer's version and the AppX logs.

Stable rehearsal rc.2-v0.23.2's x64 leg showed App Installer's "Cannot open app package:
Error in parsing the app package" for the NEW bundle on the Windows Server 2025 runner, and
its artifact held neither App Installer's version nor the AppX event that names the cause.
"""
import json
import os
import time
from pathlib import Path
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.platforms("windows")
COLLECTOR = Path(__file__).resolve().parents[3] / "tests" / "install" / "e2e-assets" / "windows-update-evidence.ps1"


def test_collects_packages_and_appx_logs_without_the_package_installed(tmp_path):
    powershell = shutil.which("powershell")
    assert powershell, "Windows PowerShell 5.1 is part of every supported Windows"
    out = tmp_path / "evidence"
    result = subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
         f"$ErrorActionPreference = 'Stop'; & '{COLLECTOR}' -OutDir '{out}' "
         "-Since (Get-Date).AddHours(-1) -Identity 'NousResearch.Hermes.NotInstalled'"],
        capture_output=True, text=True, timeout=300, check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    packages = json.loads((out / "packages.json").read_text(encoding="utf-8-sig"))
    assert all(p["Name"] != "NousResearch.Hermes.NotInstalled" for p in packages)
    for log in ("AppxPackaging_Operational", "AppXDeploymentServer_Operational",
                "AppXDeployment_Operational", "AppModel-Runtime_Admin"):
        assert (out / f"Microsoft-Windows-{log}.txt").is_file()
    assert f"saved under {out}" in result.stdout


def test_preserves_appinstaller_diagnostics_written_during_the_leg(tmp_path):
    powershell = shutil.which("powershell")
    assert powershell, "Windows PowerShell 5.1 is part of every supported Windows"
    local_data = tmp_path / "LocalAppData"
    diag_dir = (local_data / "Packages" / "Microsoft.DesktopAppInstaller_8wekyb3d8bbwe"
                / "LocalState" / "DiagOutputDir")
    diag_dir.mkdir(parents=True)
    current = diag_dir / "parse-failure.log"
    message = "Cannot open app package: error in parsing the app package"
    current.write_text(message, encoding="utf-8")
    old = diag_dir / "previous-run.log"
    old.write_text("unrelated earlier install", encoding="utf-8")
    old_time = time.time() - 7200
    os.utime(old, (old_time, old_time))

    out = tmp_path / "proof"
    env = {**os.environ, "LOCALAPPDATA": str(local_data)}
    result = subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
         f"$ErrorActionPreference = 'Stop'; & '{COLLECTOR}' -OutDir '{out}' "
         "-Since (Get-Date).AddMinutes(-30) -Identity 'NousResearch.Hermes.NotInstalled'"],
        env=env, capture_output=True, text=True, timeout=300, check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    saved = out / "appinstaller-diagnostics"
    assert (saved / current.name).read_text(encoding="utf-8") == message
    assert not (saved / old.name).exists()
    assert "App Installer diagnostic files saved: 1" in result.stdout
