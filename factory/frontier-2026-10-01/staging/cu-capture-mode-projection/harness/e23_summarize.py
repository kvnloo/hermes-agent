"""E23 summary: per (target, mode, arm) n / median / p95 / timeouts / errors, and the median delta of each
candidate arm against the base arm with a seeded paired-free bootstrap 95% CI. The A/A arm (same tree as the base,
separate blocks) gives the noise floor: a candidate delta only counts when its CI excludes 0 AND its magnitude
exceeds the A/A |delta| upper bound. Stdlib only.

Usage: e23_summarize.py rows.jsonl [...] --base main --aa main-aa --candidates c126447
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from collections import defaultdict


def pct(xs, p):
    xs = sorted(xs)
    return xs[max(0, math.ceil(p / 100 * len(xs)) - 1)] if xs else None


def boot_delta(a, b, reps=2000, seed=0):
    rng = random.Random(seed)
    ds = sorted(statistics.median(rng.choices(b, k=len(b))) - statistics.median(rng.choices(a, k=len(a)))
                for _ in range(reps))
    return ds[int(0.025 * reps)], ds[int(0.975 * reps) - 1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--aa")
    ap.add_argument("--candidates", nargs="+", required=True)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    rows = [json.loads(line) for f in a.files for line in open(f, encoding="utf-8") if line.strip()]
    rows = [r for r in rows if not r.get("warmup")]
    fake = any(r.get("fake") for r in rows)
    cells = defaultdict(list)
    for r in rows:
        cells[(r["target"], r["mode"], r["arm"])].append(r)
    stats = {}
    for (target, mode, arm), rs in sorted(cells.items()):
        ok = [r["wall_ms"] for r in rs if r.get("ok")]
        stats[f"{target}|{mode}|{arm}"] = {
            "n": len(rs), "ok": len(ok), "timeouts": sum(1 for r in rs if r.get("timeout")),
            "errors": sum(1 for r in rs if not r.get("ok")),
            "median_ms": statistics.median(ok) if ok else None, "p95_ms": pct(ok, 95),
            "gws_median_ms": statistics.median([r["gws_ms"] for r in rs if r.get("ok") and "gws_ms" in r] or [0]),
            "sent": sorted({",".join(r.get("sent", [])) for r in rs}),
            "png_bytes_median": statistics.median([r.get("png_bytes", 0) for r in rs if r.get("ok")] or [0]),
            "elements_median": statistics.median([r.get("n_elements", 0) for r in rs if r.get("ok")] or [0]),
        }
    deltas = {}
    for target, mode in sorted({(t, m) for t, m, _ in cells}):
        base = [r["wall_ms"] for r in cells.get((target, mode, a.base), []) if r.get("ok")]
        if not base:
            continue
        floor = None
        if a.aa and (aa := [r["wall_ms"] for r in cells.get((target, mode, a.aa), []) if r.get("ok")]):
            lo, hi = boot_delta(base, aa)
            floor = {"median_delta_ms": statistics.median(aa) - statistics.median(base), "ci95": [lo, hi],
                     "abs_bound_ms": max(abs(lo), abs(hi))}
        for cand in a.candidates:
            cs = [r["wall_ms"] for r in cells.get((target, mode, cand), []) if r.get("ok")]
            if not cs:
                continue
            lo, hi = boot_delta(base, cs)
            d = statistics.median(cs) - statistics.median(base)
            beyond_noise = (hi < 0 or lo > 0) and (floor is None or abs(d) > floor["abs_bound_ms"])
            deltas[f"{target}|{mode}|{cand}-{a.base}"] = {
                "median_delta_ms": d, "ci95": [lo, hi], "aa_floor": floor, "beyond_noise": beyond_noise,
                "p95_delta_ms": pct(cs, 95) - pct(base, 95)}
    print(json.dumps({"label": "MODELED (fake driver; harness check only)" if fake else "OBSERVED",
                      "rows": len(rows), "cells": stats, "deltas": deltas}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
