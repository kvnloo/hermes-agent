#!/usr/bin/env python3
"""Check A19's delivered report against retained raw observations. No workloads run."""
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess

root = Path(__file__).resolve().parent.parent
raw = json.loads((root / "probe-results-v3.json").read_text())
result = json.loads((root / "RESULT.json").read_text())
doc = (root / "SANDBOX-EVAL.md").read_text()
assert raw["host"] == "groot" and raw["elapsed_s"] < 10
assert raw["failures"] == [] and len(raw["rows"]) == 68
assert all(row["exit"] == 0 for row in raw["rows"])
print("PASS: 68 successful observations on groot; invocation under 10 seconds")
for strategy in ("bare", "bubblewrap", "landlock-setpriv"):
    rows = [r for r in raw["rows"] if r["strategy"] == strategy]
    escape = json.loads(next(r for r in rows if r["kind"] == "escape")["stdout"])
    assert len(escape) == 5
    for name, value in escape.items():
        assert (value == "ALLOWED") == (strategy == "bare" or name == "inside_write")
    tasks = [json.loads(r["stdout"]) for r in rows if r["kind"] == "file_task"]
    expected = hashlib.sha256((b"A19 owned fixture\n" * 256).upper()).hexdigest()
    assert len(tasks) == 5 and all(t["sha256"] == expected for t in tasks)
    for kind, summary in raw["summary"][strategy].items():
        times = [r["wall_ms"] for r in rows if r["kind"] == kind]
        assert len(times) == summary["n"] == 5
        assert statistics.median(times) == summary["median_ms"]
        assert f"{summary['median_ms']:.3f}" in doc
    if strategy != "bare":
        native = next(r for r in rows if r["kind"] == "hermes_native")
        output = json.loads(native["stdout"])
        assert output["first"]["returncode"] == output["second"]["returncode"] == 0
        assert output["second"]["output"] == "preserved:child\n"
    print(f"PASS: {strategy} file hash, escape controls, timing summaries, and applicable native checks")
assert set(result) == {"id", "done", "evidence", "remaining", "needs_kevin", "draft_public_actions"}
assert result["id"] == "A19" and result["done"] is False
assert result["remaining"] and result["needs_kevin"] and result["draft_public_actions"] == []
assert len((root / "REPORT.md").read_text().splitlines()) <= 40
for evidence in result["evidence"]:
    if re.fullmatch("[0-9a-f]{40}", evidence):
        subprocess.run(["git", "-C", str(root / "ayo-A19"), "cat-file", "-e", evidence + "^{commit}"], check=True)
    else:
        assert Path(evidence).is_file(), evidence
assert "no host lane" in (root / "fleet-groot.log").read_text()
assert (root / "source-preservation.log").read_text().strip() == "source-dirty-state comparison exit=0"
print("PASS: result schema, explicit partial status, evidence paths, local commit, report length, and blockers")
print("Not verified: browser E2E, rootless/container/worktree/VM workloads, disk throughput, live runtime, performance equivalence")
