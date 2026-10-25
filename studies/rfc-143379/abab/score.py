"""Strict A/B/A/B verifier for Hermes RFC #143379 native read/cached-state experiments.

This validates receipts; it does not run a model, compressor, or external service.
"""
from __future__ import annotations

import json
from pathlib import Path

PERIODS = ("A1", "B1", "A2", "B2")
POLICIES = ("native", "stateless", "native", "stateless")
REQUIRED = (
    "reader_observed_pre_write_snapshot",
    "read_success",
    "write_success",
    "disk_survived",
    "prompt_frozen",
    "usage_matches_read_snapshot",
)


def evaluate(report: dict) -> dict:
    runs = report.get("runs")
    if not isinstance(runs, list) or len(runs) != 4:
        return {"status": "BLOCKED", "reason": "four complete periods required"}
    if [r.get("period") for r in runs] != list(PERIODS):
        return {"status": "BLOCKED", "reason": "ABAB order changed"}
    if [r.get("policy") for r in runs] != list(POLICIES):
        return {"status": "BLOCKED", "reason": "intervention order changed"}
    if report.get("real_modules") is not True or report.get("real_model") is not False:
        return {"status": "BLOCKED", "reason": "unverified runtime or model claims"}
    if report.get("real_compressor") is not False:
        return {"status": "BLOCKED", "reason": "compressor scope mismatch"}
    head = report.get("head")
    fixture_sha = report.get("fixture_sha256")
    method_sha = report.get("read_source_sha256")
    if not all(isinstance(s, str) and len(s) == 64 for s in (fixture_sha, method_sha)):
        return {"status": "BLOCKED", "reason": "missing fixture or read-source digest"}
    if not isinstance(head, str) or len(head) != 40:
        return {"status": "BLOCKED", "reason": "missing exact checkout identity"}
    if any(r.get("head") != head or r.get("fixture_sha256") != fixture_sha for r in runs):
        return {"status": "BLOCKED", "reason": "unpaired source/fixture identity"}
    if len({r.get("profile") for r in runs}) != 4 or any(not r.get("profile") for r in runs):
        return {"status": "BLOCKED", "reason": "episodes must use isolated profiles"}
    for r in runs:
        if any(r.get(key) is not True for key in REQUIRED):
            return {"status": "BLOCKED", "reason": "run failed shared quality gates",
                    "period": r["period"], "checks": {k: r.get(k) for k in REQUIRED}}
        if r.get("writer_committed_before_reader_release") is not True:
            return {"status": "BLOCKED", "reason": "race ordering not established",
                    "period": r["period"]}
        if not isinstance(r.get("cache_fresh_after_join"), bool):
            return {"status": "BLOCKED", "reason": "missing observed cache freshness"}
    a = [runs[0]["cache_fresh_after_join"], runs[2]["cache_fresh_after_join"]]
    b = [runs[1]["cache_fresh_after_join"], runs[3]["cache_fresh_after_join"]]
    if not all(b):
        status = "FAIL_CANDIDATE"
    elif not any(a):
        status = "PASS_MECHANISM"
    elif all(a):
        status = "NO_GAP"
    else:
        status = "INCONCLUSIVE"
    return {"status": status, "native_fresh": a, "stateless_fresh": b,
            "interpretation": "Same-module controlled cache race, not model recall or consent certification"}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["status"] in ("PASS_MECHANISM", "NO_GAP") else 1


if __name__ == "__main__":
    raise SystemExit(main())
