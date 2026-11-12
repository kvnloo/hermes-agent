from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = Path(__file__).resolve().parent
START = HARNESS / "start.py"
LIVE = HARNESS / "live.json"
PRODUCT = "e78904f1ffb2af707d896c0de9fcb298c4d747fb"


def _port_closed(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


@pytest.mark.parametrize("attempt", [1, 2])
def test_clean_exact_export_starts_twice_without_leaks(tmp_path: Path, attempt: int) -> None:
    home = tmp_path / f"run-{attempt}"
    completed = subprocess.run(
        [sys.executable, str(START), "--home", str(home), "--readiness-timeout", "120",
         "--progress-seconds", "1", "--exit-after-ready", "--cleanup-on-exit"],
        cwd=ROOT, capture_output=True, text=True, timeout=150,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    assert live["home"] == str(home)
    assert live["commit"] == PRODUCT
    assert live["source_identity"]["product_commit"] == PRODUCT
    assert live["source_identity"]["assets"] == live["assets"]
    assert _port_closed(live["port"])
    assert not home.exists()


def test_start_failure_preserves_atomic_evidence_and_removes_stale_live(tmp_path: Path) -> None:
    home = tmp_path / "failed"
    LIVE.write_text('{"stale": true}\n', encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(START), "--home", str(home), "--readiness-timeout", "2",
         "--backend-command", "/bin/false"],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert completed.returncode == 1
    assert home.is_dir()
    assert not LIVE.exists()
    failure = json.loads((home / "failure.json").read_text(encoding="utf-8"))
    assert failure["phase"] == "backend-start"
    assert failure["command"] == ["/bin/false"]
    assert failure["exit_status"] == 1
    assert Path(failure["stdout"]).is_file()
    assert Path(failure["stderr"]).is_file()
    assert failure["process_tree"]["root_pid"]
    assert failure["port_checks"]
    assert not failure["port_checks"][0]["connectable"]
    assert set(failure["asset_expectations"])


def test_old_product_pin_is_rejected_before_evidence_home_creation(tmp_path: Path) -> None:
    home = tmp_path / "old-pin"
    completed = subprocess.run(
        [sys.executable, str(START), "--home", str(home),
         "--product-commit", "27a452edfa475de1b7ec72f09ac481bbb0190164"],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert completed.returncode != 0
    assert PRODUCT in completed.stderr
    assert not home.exists()
