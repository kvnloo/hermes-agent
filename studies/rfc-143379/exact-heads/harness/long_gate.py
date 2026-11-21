#!/usr/bin/env python3
"""RFC #143379 K=10 long-horizon acceptance evaluator; no compressor is run.

Consumes real model/compressor per-cycle score receipts. Incomplete or mocked
input is BLOCKED, even when every supplied point is positive. Synthetic unit
tests validate gate arithmetic, not memory/compression performance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

RATIOS = (4, 8)
FLAGS = ("probe_scope_fixed", "real_paraphrase", "real_compressor",
         "model_graded_recall", "pruning_as_production")
IDENTITIES = ("baseline_head", "bench_source_sha", "fixture_sha", "seed_registry")


def evaluate(data: dict) -> dict:
    meta = data.get("metadata") or {}
    absent = [key for key in FLAGS if meta.get(key) is not True]
    absent.extend(key for key in IDENTITIES if not isinstance(meta.get(key), str)
                  or not meta.get(key).strip())
    if meta.get("k") != 10:
        absent.append("fixed_K10")
    if absent:
        return {"status": "BLOCKED", "reason": "missing certification prerequisites", "missing": absent}
    rows = data.get("rows") or []
    maxima = data.get("max_cycle")
    if not isinstance(maxima, int) or maxima <= 300:
        return {"status": "BLOCKED", "reason": "requires measured cycles > 300"}
    seen = {}
    for item in rows:
        try:
            ratio, cycle = item["ratio"], item["cycle"]
            total, base, k = item["probes"], item["baseline_correct"], item["k_correct"]
            identity = item["probe_set_id"]
        except (KeyError, TypeError):
            return {"status": "BLOCKED", "reason": "malformed/missing paired score row"}
        if ratio not in RATIOS or not isinstance(cycle, int) or not 300 <= cycle <= maxima:
            continue
        if (ratio, cycle) in seen:
            return {"status": "BLOCKED", "reason": "duplicate point", "point": [ratio, cycle]}
        if (not isinstance(total, int) or isinstance(total, bool) or total <= 0
                or type(base) is not int or type(k) is not int
                or not 0 <= base <= total or not 0 <= k <= total or not isinstance(identity, str) or not identity.strip()):
            return {"status": "BLOCKED", "reason": "invalid counts or unpaired probe identity"}
        seen[(ratio, cycle)] = {"delta_pp": round(100 * (k - base) / total, 8),
                                "probes": total, "probe_set_id": identity}
    required_points = {(ratio, cycle) for ratio in RATIOS for cycle in range(300, maxima + 1)}
    missing_points = sorted(required_points - seen.keys())
    if missing_points:
        return {"status": "BLOCKED", "reason": "incomplete >=300 curve",
                "missing_points": missing_points[:20], "missing_count": len(missing_points)}
    worst_key = min(required_points, key=lambda point: seen[point]["delta_pp"])
    worst = seen[worst_key]["delta_pp"]
    return {"status": "PASS" if worst >= 0 else "FAIL",
            "minimum_delta_pp": worst, "worst_point": {"ratio": worst_key[0], "cycle": worst_key[1]},
            "points_checked": len(required_points),
            "scope": "evaluates submitted paired score receipts; does not independently verify claimed metadata"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    result = evaluate(json.loads(a.input.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
