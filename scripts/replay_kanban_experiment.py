#!/usr/bin/env python3
"""Replay one missing-required-metric hazard on an isolated real Kanban DB.

The throughput values are synthetic. The measured result is the count of
unsafe acceptances by the pinned _pm comparator and the opt-in checker.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hermes_cli.kanban_experiment import evaluate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pm-evaluator", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    home = (args.out / "isolated-home").resolve()
    home.mkdir()
    # This is an isolated replay, never a connection to the operator's board.
    for name in list(os.environ):
        if name.startswith("HERMES_KANBAN_"):
            del os.environ[name]
    os.environ.update(HOME=str(home), HERMES_HOME=str(home), HERMES_KANBAN_HOME=str(home), HERMES_KANBAN_DB=str(home / "kanban.db"))
    from hermes_cli import kanban_db as kb

    spec = importlib.util.spec_from_file_location("pinned_pm_autoresearch", args.pm_evaluator)
    pm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pm)
    cohort = {"host": "synthetic-replay", "workload": "missing-metric-v1", "toolchain": sys.version.split()[0]}
    sources = {"baseline": "a" * 64, "candidate": "b" * 64}
    document = {"schema": 1, "required_metrics": ["claim_ops", "lookup_ops"], "cohort": cohort, "sources": sources}
    for side, value in (("baseline", 100), ("candidate", 110)):
        document[side] = [
            {"receipt_id": f"{side}-{i}", "source_sha256": sources[side], "cohort": dict(cohort), "correctness_passed": True,
             "metrics": {"claim_ops": value, "lookup_ops": value}}
            for i in range(3)
        ]
    positive = copy.deepcopy(document)
    for row in document["candidate"]:
        del row["metrics"]["lookup_ops"]
    baseline = pm.compare(
        {"median_ops_per_second": document["baseline"][0]["metrics"]},
        {"median_ops_per_second": document["candidate"][0]["metrics"]},
    )
    decision = evaluate(document)
    control = evaluate(positive)
    result = {
        "measurement": "unsafe acceptance count on one missing-required-metric replay",
        "synthetic_throughput_values": True,
        "pm_evaluator_sha256": hashlib.sha256(args.pm_evaluator.read_bytes()).hexdigest(),
        "checker_sha256": hashlib.sha256((Path(__file__).resolve().parents[1] / "hermes_cli/kanban_experiment.py").read_bytes()).hexdigest(),
        "case_count": 1,
        "baseline_unsafe_acceptances": int(baseline["accepted"]),
        "candidate_unsafe_acceptances": int(decision["outcome"] == "accepted"),
        "baseline_decision": baseline,
        "candidate_decision": decision,
        "valid_control": control,
        "live_board_touched": False,
    }
    kb.init_db()
    with kb.connect() as conn:
        tid = kb.create_task(conn, title="C06 _pm required-metric safety replay", assignee="replay", created_by="C06")
        claimed = kb.claim_task(conn, tid)
        assert claimed is not None
        for filename, payload in (("experiment.json", document), ("decision.json", decision), ("comparison.json", result)):
            data = json.dumps(payload, indent=2, sort_keys=True).encode()
            (args.out / filename).write_bytes(data)
            kb.store_attachment_bytes(conn, tid, filename, data, content_type="application/json", uploaded_by="C06")
        assert kb.request_review(conn, tid, summary="Evidence checker closes the missing-metric replay; no performance claim", expected_run_id=claimed.current_run_id)
        result["status_at_review"] = kb.get_task(conn, tid).status
        assert kb.complete_task(conn, tid, result="Replay completed; incomplete candidate not promoted", summary="Unsafe acceptances 1 -> 0 on one synthetic case")
        result["task_id"] = tid
        result["final_status"] = kb.get_task(conn, tid).status
        result["events"] = [event.kind for event in kb.list_events(conn, tid)]
        result["attachments"] = []
        for attachment in kb.list_attachments(conn, tid):
            stored = Path(attachment.stored_path)
            result["attachments"].append({"filename": attachment.filename, "stored_path": str(stored), "sha256": hashlib.sha256(stored.read_bytes()).hexdigest()})
            assert stored.read_bytes() == (args.out / attachment.filename).read_bytes()
    assert result["baseline_unsafe_acceptances"] == 1
    assert result["candidate_unsafe_acceptances"] == 0
    assert result["valid_control"]["outcome"] == "accepted"
    assert result["status_at_review"] == "review" and result["final_status"] == "done"
    (args.out / "receipt.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
