from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from hermes_cli.harness_debug import (
    HarnessDebugController,
    HarnessDebugRefused,
    aggregate_status,
    fixture_seed,
    guard_debug_db,
    run_argv,
)
from hermes_cli.kanban_db import init_db


def _production_db(path: Path) -> Path:
    init_db(path)
    return path


def test_seed_and_status_oracles_are_deterministic():
    assert fixture_seed(7, "fixture", 1) == fixture_seed(7, "fixture", 1)
    assert fixture_seed(7, "fixture", 1) != fixture_seed(8, "fixture", 1)
    assert aggregate_status(["PASS", "PASS"]) == "PASS"
    assert aggregate_status(["PASS", "UNKNOWN"]) == "UNKNOWN"
    assert aggregate_status(["UNKNOWN", "FAIL"]) == "FAIL"


def test_guard_refuses_direct_symlink_hardlink_and_traversal(tmp_path: Path):
    production = _production_db(tmp_path / "production.db")
    root = tmp_path / "runs" / "hd_test"
    board = root / "board"
    board.mkdir(parents=True)

    guard_debug_db(board / "fresh.db", root, [production])
    with pytest.raises(HarnessDebugRefused, match="REFUSED_ISOLATION"):
        guard_debug_db(production, root, [production])
    with pytest.raises(HarnessDebugRefused, match="REFUSED_ISOLATION"):
        guard_debug_db(root / ".." / "escape.db", root, [production])

    symlink = board / "symlink.db"
    symlink.symlink_to(production)
    with pytest.raises(HarnessDebugRefused, match="REFUSED_ISOLATION"):
        guard_debug_db(symlink, root, [production])

    hardlink = board / "hardlink.db"
    os.link(production, hardlink)
    with pytest.raises(HarnessDebugRefused, match="REFUSED_ISOLATION"):
        guard_debug_db(hardlink, root, [production])


def test_smoke_is_disposable_exact_and_production_read_only(tmp_path: Path, monkeypatch):
    production = _production_db(tmp_path / "production" / "kanban.db")
    config = tmp_path / "config.yaml"
    config.write_text("sentinel: production\n")
    current = tmp_path / "current"
    current.symlink_to(production.parent)
    before = {
        "db": production.read_bytes(),
        "config": config.read_bytes(),
        "current": os.readlink(current),
    }
    # Ambient values are hostile inputs. The controller may include an existing
    # production DB as an additional sentinel, but it must not resolve writes
    # through any of them.
    monkeypatch.setenv("HERMES_KANBAN_DB", str(production))
    monkeypatch.setenv("HERMES_KANBAN_BOARD", "canonical-production")
    monkeypatch.setenv("HERMES_KANBAN_TASK", "production-task")

    controller = HarnessDebugController(tmp_path / "debug-runs")
    report = controller.start_smoke(
        production_db=production,
        captain_identity="cli:captain-test",
        seed=0xC0FFEE,
        fanout=2,
    )

    assert report["overallStatus"] == "PASS"
    assert report["productionSentinel"]["equal"] is True
    assert report["modelIdentities"]["orchestrator"]["model"] == "gpt-5.6-sol"
    assert report["modelIdentities"]["specialist"]["model"] == "gpt-5.6-luna"
    assert report["budgets"]["observed"]["agentWorkers"] == 0
    assert [f["id"] for f in report["fixtures"]] == [
        "smoke.lifecycle.v1",
        "smoke.capacity-starvation.v1",
        "smoke.contamination.v1",
    ]
    contamination = report["fixtures"][2]
    assert contamination["observed"] == {"links": 239, "dangling": 165, "namespaced": True}
    assert report["mutationPairs"][0]["red"]["reasonCode"] == "REFUSED_ISOLATION"
    assert report["mutationPairs"][0]["green"]["status"] == "GREEN"
    assert report["mutationPairs"][0]["writeAttempted"] is False

    run_root = controller.root / report["runId"]
    assert (run_root / "SEALED").is_file()
    assert json.loads((run_root / "report.json").read_text())["sealedHash"] == report["sealedHash"]
    debug_conn = sqlite3.connect(run_root / "board" / "kanban.db")
    try:
        assert debug_conn.execute("SELECT count(*) FROM harness_debug_edges").fetchone()[0] == 239
        assert debug_conn.execute("SELECT count(*) FROM harness_debug_trace").fetchone()[0] == 11
    finally:
        debug_conn.close()

    assert production.read_bytes() == before["db"]
    assert config.read_bytes() == before["config"]
    assert os.readlink(current) == before["current"]

    status = controller.status(report["runId"])
    assert status["runs"][0]["state"] == "SEALED"
    assert controller.stop(report["runId"])["status"] == "already-sealed"
    cleanup = controller.cleanup(report["runId"])
    assert cleanup["status"] == "CLEANED"
    assert cleanup["rootAbsent"] is True
    assert production.read_bytes() == before["db"]


def test_cli_service_requires_explicit_authority_and_supports_report(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(
        "hermes_cli.config.load_config",
        lambda: {"orchestration": {"harness_debug": {"enabled": True}}},
    )
    production = _production_db(tmp_path / "production.db")
    controller = HarnessDebugController(tmp_path / "runs")
    with pytest.raises(SystemExit):
        run_argv(["debug", "start", "smoke", "--production-db", str(production)], controller)

    output = run_argv([
        "debug", "start", "smoke", "--production-db", str(production),
        "--captain", "cli:test", "--seed", "9", "--fanout", "1",
    ], controller)
    run_id = json.loads(output)["runId"]
    report = json.loads(run_argv(["debug", "report", run_id], controller))
    assert report["authorityReceipt"]["captainIdentity"] == "cli:test"
    markdown = run_argv(["debug", "report", run_id, "--format", "markdown"], controller)
    assert f"PASS / smoke / {run_id}" in markdown


def test_cleanup_refuses_unsealed_or_marker_mismatch(tmp_path: Path):
    controller = HarnessDebugController(tmp_path / "runs")
    root = controller.root / "hd_foreign"
    root.mkdir(parents=True)
    (root / "RUN_MARKER.json").write_text('{"runId":"other"}')
    with pytest.raises(HarnessDebugRefused, match="REFUSED_ISOLATION"):
        controller.cleanup("hd_foreign")
