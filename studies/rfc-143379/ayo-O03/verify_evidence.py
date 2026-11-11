#!/usr/bin/env python3
"""Check saved GitHub bindings and diagnostic records without running tests."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("evidence_root", type=Path)
parser.add_argument("--diagnostic-dir", type=Path)
args = parser.parse_args()
root = args.evidence_root

def load(name):
    return json.loads((root / "evidence" / name).read_text())

comment = load("comment-readback.json")
request = load("candidate-request.json")
commit = load("candidate-commit.json")
run = load("actions-run.json")
workflow = (root / "logs/workflow.http").read_text()
log = (root / "logs/actions-full.log").read_text()
assert comment["id"] == 6625116852
assert comment["html_url"].endswith("#issuecomment-6625116852")
assert "Nothing here is certified or deployable yet." in comment["body"]
assert commit["sha"] == "a8baeb7e0d35d6961e4b8ee358ab434657ad802e"
assert commit["sha"] in request["body"]
for name in ["comment-readback", "candidate-request", "candidate-commit", "actions-run", "actions-jobs", "workflow"]:
    assert re.search(r"HTTP/\S+ 200", (root / f"logs/{name}.http").read_text()), name
checkout = re.search(r"^\s+ref: ([a-f0-9]{40})$", workflow, re.M).group(1)
assert checkout == "d1bdb4582cd5d16be6a6b486f696f8240c222b96"
assert checkout != commit["sha"]
assert f"git checkout --progress --force {checkout}" in log
assert f"git log -1 --format=%H" in log
assert "continue-on-error: true" in workflow and "|| true" in workflow
for row in load("patch-hashes.json"):
    name = Path(row["path"]).name
    assert hashlib.sha256((root / "evidence" / name).read_bytes()).hexdigest() == row["sha256"]
summary = dict(existing_reply=comment["html_url"], reply_created=comment["created_at"],
               candidate_sha=commit["sha"], workflow_event_sha=run["head_sha"],
               actual_checkout_sha=checkout, job_conclusion=run["conclusion"],
               qualifies_candidate=False, test_failures_masked=True,
               diagnostic_execution="NOT_RUN_OR_NOT_RECOVERED")
historical = root / "evidence/historical"
if historical.is_dir():
    old_receipt = json.loads((historical / "diagnostic-receipt.json").read_text())
    assert old_receipt["candidate_sha"] == "b84150e9be88911280f981467de9628fcfb0f60f"
    history = []
    for name in ["unchanged_shared_probes.xml", "nonce_invariance.xml"]:
        cases = list(ET.parse(historical / name).getroot().iter("testcase"))
        counts = dict(tests=len(cases), failures=sum(c.find("failure") is not None for c in cases),
                      errors=sum(c.find("error") is not None for c in cases),
                      skipped=sum(c.find("skipped") is not None for c in cases))
        history.append(dict(file=name, **counts))
    assert history[0] == dict(file="unchanged_shared_probes.xml", tests=23, failures=0, errors=0, skipped=1)
    assert history[1] == dict(file="nonce_invariance.xml", tests=12, failures=12, errors=0, skipped=0)
    summary["historical_diagnostics"] = dict(candidate_sha=old_receipt["candidate_sha"], results=history)
if args.diagnostic_dir:
    receipt = json.loads((args.diagnostic_dir / "receipt.json").read_text())
    assert receipt["candidate_sha"] == commit["sha"]
    assert receipt["source_changed"] == []
    counts = dict(tests=0, failures=0, errors=0, skipped=0)
    for row in receipt["results"]:
        doc = ET.parse(args.diagnostic_dir / row["junit"]).getroot()
        cases = list(doc.iter("testcase"))
        actual = dict(tests=len(cases), failures=sum(c.find("failure") is not None for c in cases),
                      errors=sum(c.find("error") is not None for c in cases),
                      skipped=sum(c.find("skipped") is not None for c in cases))
        assert all(actual[k] == row[k] for k in actual), (row["label"], actual)
        for key in counts:
            counts[key] += actual[key]
    assert counts["tests"] > counts["errors"], "No executable diagnostics recovered"
    counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    summary.update(diagnostic_execution="EXECUTED_COMPATIBILITY_ONLY", diagnostic_counts=counts)
(root / "evidence/binding-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
