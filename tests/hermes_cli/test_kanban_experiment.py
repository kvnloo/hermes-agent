"""Opt-in receipt checking and real Kanban attachment/review integration."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_cli.kanban_experiment import evaluate, main


@pytest.fixture
def experiment():
    cohort = {"host": "fleet-test", "workload": "fixed-v1", "toolchain": "python3"}
    sources = {"baseline": "a" * 64, "candidate": "b" * 64}
    document = {"schema": 1, "required_metrics": ["claim_ops", "lookup_ops"], "cohort": cohort, "sources": sources}
    for side, value in (("baseline", 100), ("candidate", 110)):
        document[side] = [
            {"receipt_id": f"{side}-{i}", "source_sha256": sources[side], "cohort": dict(cohort),
             "correctness_passed": True, "metrics": {"claim_ops": value, "lookup_ops": value}}
            for i in range(3)
        ]
    return document


def test_accepts_complete_separated_evidence(experiment):
    result = evaluate(experiment)
    assert result["outcome"] == "accepted"
    assert result["advisory_only"] is True
    assert result["measurement_counts"] == {"baseline": 3, "candidate": 3}
    assert len(result["input_sha256"]) == 64
    assert result["input_sha256"] == evaluate(copy.deepcopy(experiment))["input_sha256"]


def test_required_metric_cannot_disappear(experiment):
    for row in experiment["candidate"]:
        del row["metrics"]["lookup_ops"]
    result = evaluate(experiment)
    assert result["outcome"] == "invalid"
    assert "lookup_ops" in result["reason"]


@pytest.mark.parametrize("side", ["baseline", "candidate"])
def test_both_sides_need_three_runs(experiment, side):
    experiment[side].pop()
    assert evaluate(experiment)["outcome"] == "insufficient-evidence"


@pytest.mark.parametrize("field,value", [
    ("receipt_id", "baseline-0"), ("source_sha256", "c" * 64),
    ("cohort", {"host": "other"}), ("correctness_passed", False),
])
def test_rejects_incomparable_or_repeated_runs(experiment, field, value):
    experiment["candidate"][0][field] = value
    assert evaluate(experiment)["outcome"] == "invalid"


@pytest.mark.parametrize("value", [0, -1, True, "110", None, float("nan"), float("inf"), 10**1000])
def test_rejects_invalid_numeric_evidence(experiment, value):
    experiment["candidate"][0]["metrics"]["claim_ops"] = value
    assert evaluate(experiment)["outcome"] == "invalid"


def test_extra_metrics_cannot_hide_a_required_regression(experiment):
    for row in experiment["candidate"]:
        row["metrics"].update(claim_ops=95, lookup_ops=200, new_metric=10000)
    assert evaluate(experiment)["outcome"] == "rejected"
    assert "per-metric" in evaluate(experiment)["reason"]


def test_small_gain_is_rejected(experiment):
    for row in experiment["candidate"]:
        row["metrics"] = {name: 100.5 for name in row["metrics"]}
    assert evaluate(experiment)["outcome"] == "rejected"


def test_overlapping_runs_are_not_a_win(experiment):
    experiment["candidate"][0]["metrics"] = {"claim_ops": 99, "lookup_ops": 99}
    assert "not separated" in evaluate(experiment)["reason"]


def test_extreme_finite_values_still_produce_json(experiment):
    for side, value in (("baseline", 1e-300), ("candidate", 1e308)):
        experiment[side].append(copy.deepcopy(experiment[side][-1]))
        experiment[side][-1]["receipt_id"] += "-extra"
        for row in experiment[side]:
            row["metrics"] = {name: value for name in row["metrics"]}
    assert evaluate(experiment)["outcome"] == "accepted"
    json.dumps(evaluate(experiment), allow_nan=False)


@pytest.mark.parametrize("document", [None, [], {"schema": True}, {"schema": 1, "required_metrics": []}])
def test_bad_contract_is_invalid(document):
    assert evaluate(document)["outcome"] == "invalid"


def test_cli_reports_json_errors_without_traceback(tmp_path, capsys):
    path = tmp_path / "invalid.json"
    path.write_text("{bad json")
    assert main([str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["outcome"] == "invalid"


def test_receipt_survives_real_kanban_review_and_losing_experiment_completion(experiment, tmp_path, monkeypatch):
    from hermes_cli import kanban_db as kb

    home = tmp_path / "isolated-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(home))
    monkeypatch.setenv("HERMES_KANBAN_DB", str(home / "kanban.db"))
    monkeypatch.setattr(Path, "home", lambda: home)
    kb.init_db()
    path = tmp_path / "experiment.json"
    for row in experiment["candidate"]:
        del row["metrics"]["lookup_ops"]
    path.write_text(json.dumps(experiment))
    process = subprocess.run(
        [sys.executable, "-m", "hermes_cli.kanban_experiment", str(path)],
        text=True, capture_output=True, check=False,
    )
    assert process.returncode == 2, process.stderr
    decision = json.loads(process.stdout)
    with kb.connect() as conn:
        tid = kb.create_task(conn, title="C06 evidence-safety replay", assignee="worker", created_by="C06")
        claimed = kb.claim_task(conn, tid)
        assert claimed is not None
        kb.store_attachment_bytes(conn, tid, "decision.json", process.stdout.encode(), content_type="application/json")
        assert kb.request_review(conn, tid, summary="Measured experiment; candidate evidence invalid", expected_run_id=claimed.current_run_id)
        assert kb.get_task(conn, tid).status == "review"
        # Evidence validity is separate from whether the experiment task completed.
        assert kb.complete_task(conn, tid, result="Experiment completed; no candidate promotion")
        assert kb.get_task(conn, tid).status == "done"
        attachment = kb.list_attachments(conn, tid)[0]
        assert json.loads(Path(attachment.stored_path).read_text()) == decision
        assert decision["outcome"] == "invalid"
        assert {e.kind for e in kb.list_events(conn, tid)} >= {"attached", "review_requested", "completed"}
