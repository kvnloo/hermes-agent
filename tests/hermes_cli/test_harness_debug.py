from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from hermes_cli.harness_debug import (
    HarnessDebugController,
    HarnessDebugRefused,
    make_local_receipt,
    run_argv,
)
from hermes_cli.kanban_db import init_db


def _production(path: Path) -> Path:
    init_db(path)
    return path


def _authority(tmp_path: Path, production: Path, *, nonce: str = "a" * 64,
               now: int | None = None, seed: int = 7, fanout: int = 1):
    key = b"k" * 32
    key_path = tmp_path / "authority.key"
    key_path.write_bytes(key)
    key_path.chmod(0o600)
    receipt = make_local_receipt(key, production_db=production, nonce=nonce,
                                 now=now, seed=seed, fanout=fanout)
    receipt_path = tmp_path / f"receipt-{nonce[:8]}.json"
    receipt_path.write_text(json.dumps(receipt))
    return key, key_path, receipt, receipt_path


def test_forged_expired_mismatched_and_replayed_receipts_fail_closed(tmp_path: Path):
    production = _production(tmp_path / "production.db")
    controller = HarnessDebugController(tmp_path / "runs")
    key, _, receipt, _ = _authority(tmp_path, production)

    forged = dict(receipt); forged["operator"] = "attacker"
    with pytest.raises(HarnessDebugRefused, match="REFUSED_AUTHORITY"):
        controller.start_smoke(production_db=production, receipt=forged,
                               authority_key=key, seed=7, fanout=1)

    expired = make_local_receipt(key, production_db=production, nonce="b" * 64,
                                 now=1, seed=7, fanout=1)
    with pytest.raises(HarnessDebugRefused, match="expired"):
        controller.start_smoke(production_db=production, receipt=expired,
                               authority_key=key, seed=7, fanout=1)

    with pytest.raises(HarnessDebugRefused, match="scope mismatch"):
        controller.start_smoke(production_db=production, receipt=receipt,
                               authority_key=key, seed=8, fanout=1)

    report = controller.start_smoke(production_db=production, receipt=receipt,
                                    authority_key=key, seed=7, fanout=1)
    assert report["overallStatus"] == "PASS"
    with pytest.raises(HarnessDebugRefused, match="REFUSED_REPLAY"):
        controller.start_smoke(production_db=production, receipt=receipt,
                               authority_key=key, seed=7, fanout=1)


def test_real_behavior_red_green_and_production_sentinel(tmp_path: Path):
    production = _production(tmp_path / "production.db")
    before = production.read_bytes()
    key, _, receipt, _ = _authority(tmp_path, production)
    controller = HarnessDebugController(tmp_path / "runs")
    report = controller.start_smoke(production_db=production, receipt=receipt,
                                    authority_key=key, seed=7, fanout=1)
    assert report["fixtures"][0]["status"] == "PASS"
    assert report["fixtures"][0]["observed"]["blockedChildClaim"] is True
    pair = report["mutationPairs"][0]
    assert pair["red"]["status"] == "FAIL"
    assert pair["green"]["status"] == "PASS"
    assert pair["red"]["observed"] != pair["green"]["observed"]
    assert production.read_bytes() == before
    assert report["productionSentinel"]["equal"] is True
    assert report["security"] == {"gatewayEnabled": False, "networkDenied": True,
                                  "secretCanaryObserved": False}


@pytest.mark.parametrize("target", ["report.json", "evidence/green-trace.json", "envelope.json", "RUN_MARKER.json", "board/green.db"])
def test_report_and_cleanup_reject_every_tampered_sealed_component(tmp_path: Path, target: str):
    production = _production(tmp_path / "production.db")
    key, _, receipt, _ = _authority(tmp_path, production)
    controller = HarnessDebugController(tmp_path / "runs")
    report = controller.start_smoke(production_db=production, receipt=receipt,
                                    authority_key=key, seed=7, fanout=1)
    path = controller.root / report["runId"] / target
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(HarnessDebugRefused, match="TAMPERED"):
        controller.report(report["runId"])
    with pytest.raises(HarnessDebugRefused, match="TAMPERED"):
        controller.cleanup(report["runId"])
    assert controller.status(report["runId"])["runs"][0]["state"] == "TAMPERED"


def test_cleanup_is_idempotent_and_retains_complete_seal(tmp_path: Path):
    production = _production(tmp_path / "production.db")
    key, _, receipt, _ = _authority(tmp_path, production)
    controller = HarnessDebugController(tmp_path / "runs")
    report = controller.start_smoke(production_db=production, receipt=receipt,
                                    authority_key=key, seed=7, fanout=1)
    first = controller.cleanup(report["runId"])
    second = controller.cleanup(report["runId"])
    assert first == second
    assert first["status"] == "RETAINED_SEALED"
    assert controller.report(report["runId"])["overallStatus"] == "PASS"


def test_cli_has_no_caller_captain_and_requires_protected_receipt_key(tmp_path: Path):
    production = _production(tmp_path / "production.db")
    _, key_path, _, receipt_path = _authority(tmp_path, production)
    controller = HarnessDebugController(tmp_path / "runs")
    with pytest.raises(SystemExit):
        run_argv(["debug", "start", "smoke", "--production-db", str(production),
                  "--captain", "forged"], controller)
    output = run_argv(["debug", "start", "smoke", "--production-db", str(production),
                       "--receipt", str(receipt_path), "--authority-key", str(key_path),
                       "--seed", "7", "--fanout", "1"], controller)
    assert json.loads(output)["overallStatus"] == "PASS"


def test_concurrent_replay_spends_receipt_once(tmp_path: Path):
    production = _production(tmp_path / "production.db")
    key, _, receipt, _ = _authority(tmp_path, production)
    controller = HarnessDebugController(tmp_path / "runs")
    def attempt():
        try:
            controller.start_smoke(production_db=production, receipt=receipt,
                                   authority_key=key, seed=7, fanout=1)
            return "PASS"
        except HarnessDebugRefused as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == ["PASS", "REFUSED_REPLAY"]


def test_path_component_symlink_is_refused(tmp_path: Path):
    production = _production(tmp_path / "production.db")
    key, _, receipt, _ = _authority(tmp_path, production)
    root = tmp_path / "runs"
    elsewhere = tmp_path / "elsewhere"; elsewhere.mkdir()
    root.symlink_to(elsewhere, target_is_directory=True)
    controller = HarnessDebugController(root)
    with pytest.raises((HarnessDebugRefused, FileExistsError, OSError)):
        controller.start_smoke(production_db=production, receipt=receipt,
                               authority_key=key, seed=7, fanout=1)