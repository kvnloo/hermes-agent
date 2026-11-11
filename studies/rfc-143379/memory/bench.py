"""Deterministic policy/coverage benchmark, not an LLM or Hermes fidelity metric.

Generates a reproducible collection of exact identifiers; a simulated lossy
summarizer retains topic names but discards exact identifiers. An exact recency
window preserves K newest raw identifiers. A source archive can retrieve an
older identifier, provided its scope and source version match.
"""
import csv
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent
RATIOS = (2, 4, 8, 16, 32)
SIZES = (150, 300)
SEEDS = tuple(range(25))
PROBES_PER_RUN = 80


def simulate(n: int, ratio: int, seed: int, probes: int = PROBES_PER_RUN) -> dict:
    rng = random.Random(10000 * n + 100 * ratio + seed)
    event_values = [f"sha-{rng.getrandbits(80):020x}" for _ in range(n)]
    # Exact-working-memory budget is proportional to compressed fraction.
    budget = max(1, n // ratio)
    # Fixed-K may violate that budget: it must be clamped in a realistic setup.
    policies = {
        "summary_only": 0,
        "fixed_K10": min(10, budget),
        "scaled_K10pct": min(max(10, n // 10), budget),
        "exact_archive_retrieval": min(10, budget),
    }
    sample_indices = [rng.randrange(n) for _ in range(probes)]
    counters = {}
    for name, k in policies.items():
        eligible = 0
        for i in sample_indices:
            if i >= n - k:
                eligible += 1
            elif name == "exact_archive_retrieval":
                # Idealized resolver: immutable pointer, correct scope/version,
                # and source available. It is NOT an agent retrieval success rate.
                eligible += 1
        counters[name] = eligible
    return {"cycles": n, "ratio": ratio, "seed": seed,
            "probes": probes, "budget_exact_items": budget, **counters}


def main():
    rows = [simulate(n, r, seed) for n in SIZES for r in RATIOS for seed in SEEDS]
    with (OUT / "raw_coverage.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    keys = ("summary_only", "fixed_K10", "scaled_K10pct", "exact_archive_retrieval")
    agg = []
    for n in SIZES:
        for ratio in RATIOS:
            subset = [v for v in rows if v["cycles"] == n and v["ratio"] == ratio]
            total = sum(v["probes"] for v in subset)
            agg.append({"cycles": n, "ratio": ratio, "probes": total,
                        "budget_exact_items": subset[0]["budget_exact_items"],
                        **{k: round(100 * sum(v[k] for v in subset) / total, 2) for k in keys}})
    (OUT / "results.json").write_text(json.dumps({
        "description": "Toy exact-ID availability under a uniform historical probe distribution. Not LLM accuracy.",
        "sample": {"seeds": len(SEEDS), "probes_per_seed": PROBES_PER_RUN,
                   "cycles": list(SIZES), "compression_ratios": list(RATIOS)},
        "rows": agg}, indent=2) + "\n")
    for row in agg:
        print(row)


if __name__ == "__main__":
    main()
