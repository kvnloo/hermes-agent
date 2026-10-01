#!/usr/bin/env python3
"""Index build cost of the three new rows (round 5; $0, T0, no LLM, no network).

Same ~443K-char synthetic region as anchor_coverage.py's timing_big_region
(synthetic_region([], "dense", 999) * 3). For each arm: median of 7 wall-clock builds of
_build_anchor_index, plus the median time of each new row's pattern alone (finditer over the
region text). Arms run in separate subprocesses, one after another, on a shared host: only
the order of magnitude is claimed.

On main the loop ``break``s at the first section that overflows, so on this region the rows
after ``files`` never run there; in #117462 (no ``break``) every row always runs. The per-row
time is the cost wherever the rows do run.

Usage: index_cost.py --checkout <worktree> --arm name=<file> ... --out <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import anchor_coverage as ac  # noqa: E402

REPS = 7
NEW_LABELS = ("task ids", "dotted keys", "error messages")


def worker(checkout: str, arm_file: str, out: str) -> None:
    mod = ac.load_arm(checkout, arm_file)
    region = ac.synthetic_region([], "dense", 999) * 3
    text = "\n".join(m["content"] for m in region)
    builds = []
    for _ in range(REPS):
        t0 = time.perf_counter()
        mod._build_anchor_index(region)
        builds.append(time.perf_counter() - t0)
    rows = {}
    for label, pattern, _cap in mod._ANCHOR_PATTERNS:
        if label not in NEW_LABELS:
            continue
        ts = []
        for _ in range(REPS):
            t0 = time.perf_counter()
            sum(1 for _ in pattern.finditer(text))
            ts.append(time.perf_counter() - t0)
        rows[label] = round(st.median(ts), 4)
    Path(out).write_text(json.dumps({
        "arm_file_sha256": hashlib.sha256(Path(arm_file).read_bytes()).hexdigest(),
        "region_chars": len(text), "reps": REPS,
        "build_s_median": round(st.median(builds), 4), "build_s_all": [round(b, 4) for b in builds],
        "new_row_s_median": rows, "new_rows_s_sum": round(sum(rows.values()), 4),
        "egress_blocked": list(ac._blocked)}), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkout", required=True)
    ap.add_argument("--arm", action="append", default=[])
    ap.add_argument("--out")
    ap.add_argument("--worker", nargs=2, metavar=("ARM_FILE", "OUT"))
    a = ap.parse_args()
    if a.worker:
        worker(a.checkout, *a.worker)
        return
    res = {}
    for spec in a.arm:
        name, path = spec.split("=", 1)
        tmp = f"{a.out}.{name}.part"
        subprocess.run([sys.executable, __file__, "--checkout", a.checkout, "--worker", path, tmp], check=True)
        res[name] = json.loads(Path(tmp).read_text(encoding="utf-8"))
        Path(tmp).unlink()
    Path(a.out).write_text(json.dumps({"arms": res}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
