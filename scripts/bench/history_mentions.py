#!/usr/bin/env python3
"""Stdlib-only DSA-T1 transcript media-mention benchmark.

From the repository root: python scripts/bench/history_mentions.py
Times the preserved full scan and the new indexed lookup on identical data.
Median of seven runs per arm, after a one-time migration/backfill, with exact
result checks. Work counts are deterministic row/digest and indexed-hit counts;
timings and counts are evidence, not a claimed speedup.
"""

import hashlib
import json
import random
import sqlite3
import statistics
import sys
from pathlib import Path
from time import perf_counter_ns

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SIZES = (1_000, 10_000, 100_000)
RUNS = 7
DIGESTS = 4


def _fixture(rows):
    conn = sqlite3.connect(":memory:", isolation_level=None)
    conn.execute("CREATE TABLE state_meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, content TEXT)")
    references = [
        {"sha256": hashlib.sha256(str(i).encode("ascii")).hexdigest(), "path": ""}
        for i in range(DIGESTS)
    ]
    for i, reference in enumerate(references):
        reference["path"] = "/bench/native-inputs/" + reference["sha256"] + (
            "/file%_literal_\u96ea.txt" if i % 2 else "/normal.txt"
        )
    rng = random.Random(1107)
    batch = []
    for i in range(rows):
        reference = references[rng.randrange(DIGESTS)]
        tail = reference["sha256"] + "/" + Path(reference["path"]).name
        if i % 113 == 0:
            content = "path: " + tail
        elif i % 137 == 0:
            content = json.dumps({"path": reference["path"]}, ensure_ascii=True)
        elif i % 173 == 0:
            content = "visible: " + json.dumps(tail.replace("/", "\\"))
        else:
            content = "no retained path at row " + str(i) + " \u96ea\u2603"
        batch.append((content,))
    conn.executemany("INSERT INTO messages(content) VALUES (?)", batch)
    return conn, references


def benchmark(rows):
    from gateway.session_ingress_media import _history_mentions, _history_mentions_scan
    from hermes_state_history_fts import ensure_history_fts

    conn, references = _fixture(rows)
    errors = []
    try:
        index_start = perf_counter_ns()
        ensure_history_fts(conn.cursor(), enabled=True)
        backfill_ns = perf_counter_ns() - index_start
        expected = _history_mentions_scan(conn, references)
        timings = {"old": [], "new": []}
        for attempt in range(RUNS):
            arms = (("old", _history_mentions_scan), ("new", _history_mentions))
            if attempt % 2:
                arms = tuple(reversed(arms))
            for name, implementation in arms:
                started = perf_counter_ns()
                try:
                    actual = implementation(conn, references)
                    if actual != expected:
                        errors.append({"run": attempt + 1, "arm": name, "error": "mismatch"})
                except Exception as exc:
                    errors.append({"run": attempt + 1, "arm": name,
                                   "error": type(exc).__name__ + ": " + str(exc)})
                timings[name].append(perf_counter_ns() - started)

        postings = sum(conn.execute(
            "SELECT COUNT(*) FROM messages_history_fts WHERE messages_history_fts MATCH ?",
            ('"' + reference["sha256"] + '"',),
        ).fetchone()[0] for reference in references)
        return {
            "rows": rows,
            "digests": len(references),
            "runs_per_arm": RUNS,
            "median_ns": {name: int(statistics.median(values))
                          for name, values in timings.items()},
            "backfill_ns": backfill_ns,
            "errors": errors,
            "error_count": len(errors),
            "work_count": {
                "old_row_digest_upper_bound": rows * len(references),
                "new_digest_index_probes": len(references),
                "new_candidate_rows": postings,
                "backfill_rows": rows,
            },
        }
    finally:
        conn.close()


def main():
    results = []
    for rows in SIZES:
        try:
            results.append(benchmark(rows))
        except Exception as exc:
            results.append({"rows": rows, "errors": [
                {"error": type(exc).__name__ + ": " + str(exc)}
            ], "error_count": 1, "work_count": {
                "old_row_digest_upper_bound": rows * DIGESTS,
                "new_digest_index_probes": DIGESTS,
            }})
    print(json.dumps({"benchmark": "dsa-history-mentions",
                      "status": "measured-not-claimed",
                      "results": results}, sort_keys=True))
    return 1 if any(result["error_count"] for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
