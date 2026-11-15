#!/usr/bin/env python3
"""Stdlib-only DSA-T1 exact history-mention and write-cost benchmark.

From the repository root: python scripts/bench/history_mentions.py

Every case uses the same seeded SQLite database for old and new; disk cases
also measure on-disk page usage, write-trigger amplification, many candidate
digests, long matching tool outputs and NUL/escaped paths. Each arm receives
seven alternating, median-reported runs. Measurements are not speedup claims.
"""

import hashlib
import json
import random
import sqlite3
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter_ns

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SIZES = (1_000, 10_000, 100_000)
RUNS = 7
DIGESTS = 4
CASES = (
    ("memory_4", 4, False, False, False),
    ("disk_many_128", 128, True, False, False),
    ("disk_long_tools_16", 16, True, True, False),
    ("disk_nul_16", 16, True, False, True),
)


def _fixture(rows, digests, *, disk, long_tools, with_nul, directory):
    db_path = str(Path(directory) / "indexed.db") if disk else ":memory:"
    conn = sqlite3.connect(db_path, isolation_level=None)
    if disk:
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE state_meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, content TEXT)")
    refs = []
    for i in range(digests):
        digest = hashlib.sha256(str(i).encode("ascii")).hexdigest()
        basename = ("file%_雪\\slash.txt" if i % 2 else "normal.txt")
        refs.append({
            "sha256": digest,
            "path": "/bench/native-inputs/" + digest + "/" + basename,
        })
    rng = random.Random(1107)
    batch = []
    for i in range(rows):
        reference = refs[rng.randrange(digests)]
        tail = reference["sha256"] + "/" + Path(reference["path"]).name
        if i % 113 == 0:
            content = "tool_output: " + ("长输出" * 1024 if long_tools else "") + tail
        elif i % 137 == 0:
            content = json.dumps({"path": reference["path"]}, ensure_ascii=True)
        elif with_nul and i % 179 == 0:
            content = "before\x00" + tail
        elif i % 173 == 0:
            content = "visible: " + json.dumps(tail.replace("/", "\\"))
        elif long_tools and i % 11 == 0:
            content = "tool_output: " + "a" * 2048 + tail
        else:
            content = "unrelated transcript " + str(i) + " 雪☃"
        batch.append((content,))
        if len(batch) == 1000:
            conn.executemany("INSERT INTO messages(content) VALUES (?)", batch)
            batch.clear()
    if batch:
        conn.executemany("INSERT INTO messages(content) VALUES (?)", batch)
    return conn, refs


def _measure_write(conn, changes):
    """Rollback real UPDATEs to keep each measured arm on identical inputs."""
    started = perf_counter_ns()
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.executemany("UPDATE messages SET content=? WHERE id=?", changes)
    finally:
        conn.execute("ROLLBACK")
    return perf_counter_ns() - started


def _database_bytes(conn):
    return conn.execute("PRAGMA page_count").fetchone()[0] * conn.execute(
        "PRAGMA page_size").fetchone()[0]


def benchmark(rows, case):
    from gateway.session_ingress_media import _history_mentions, _history_mentions_scan
    from hermes_state_history_fts import HISTORY_FTS_READY_KEY, ensure_history_fts

    label, digests, disk, long_tools, with_nul = case
    errors = []
    with tempfile.TemporaryDirectory(prefix="dsa-history-") as directory:
        indexed, references = _fixture(rows, digests, disk=disk,
                                       long_tools=long_tools, with_nul=with_nul,
                                       directory=directory)
        baseline = sqlite3.connect(
            str(Path(directory) / "baseline.db") if disk else ":memory:",
            isolation_level=None)
        try:
            indexed.backup(baseline)
            if disk:
                baseline.execute("PRAGMA journal_mode=WAL")
            backfill_started = perf_counter_ns()
            backfill_batches = 0
            while indexed.execute(
                    "SELECT value FROM state_meta WHERE key=?",
                    (HISTORY_FTS_READY_KEY,)).fetchone() is None:
                ensure_history_fts(indexed.cursor(), enabled=True)
                backfill_batches += 1
                if backfill_batches > rows + 2:
                    raise RuntimeError("migration made no durable progress")
            backfill_ns = perf_counter_ns() - backfill_started
            expected = _history_mentions_scan(baseline, references)
            if _history_mentions(indexed, references) != expected:
                errors.append({"phase": "initial_parity", "error": "mismatch"})

            timings = {"old": [], "new": []}
            for attempt in range(RUNS):
                arms = (("old", baseline, _history_mentions_scan),
                        ("new", indexed, _history_mentions))
                if attempt % 2:
                    arms = tuple(reversed(arms))
                for name, conn, lookup in arms:
                    started = perf_counter_ns()
                    try:
                        actual = lookup(conn, references)
                        if actual != expected:
                            errors.append({"run": attempt + 1,
                                           "arm": name, "error": "mismatch"})
                    except Exception as exc:
                        errors.append({"run": attempt + 1, "arm": name,
                                       "error": type(exc).__name__ + ": " + str(exc)})
                    timings[name].append(perf_counter_ns() - started)

            # Updates touch existing rows and generate both FTS DELETE and
            # INSERT; rolling back permits identical seven-run comparison.
            rng = random.Random(1107)
            updates = []
            for i in range(64):
                reference = references[i % digests]
                tail = reference["sha256"] + "/" + Path(reference["path"]).name
                updates.append(("rewrite " + ("t" * 2048 if long_tools else "") + tail,
                                rng.randrange(1, rows + 1)))
            write_ns = {"old": [], "new": []}
            for attempt in range(RUNS):
                arms = (("old", baseline), ("new", indexed))
                if attempt % 2:
                    arms = tuple(reversed(arms))
                for name, conn in arms:
                    try:
                        write_ns[name].append(_measure_write(conn, updates))
                    except Exception as exc:
                        errors.append({"phase": "write", "run": attempt + 1,
                                       "arm": name,
                                       "error": type(exc).__name__ + ": " + str(exc)})
            if _history_mentions_scan(baseline, references) != expected:
                errors.append({"phase": "baseline_after_write", "error": "mismatch"})
            if _history_mentions(indexed, references) != expected:
                errors.append({"phase": "indexed_after_write", "error": "mismatch"})

            postings = sum(indexed.execute(
                "SELECT COUNT(*) FROM messages_history_fts "
                "WHERE messages_history_fts MATCH ?",
                ('"' + ref["sha256"] + '"',)
            ).fetchone()[0] for ref in references)
            exceptional = indexed.execute(
                "SELECT COUNT(*) FROM messages_history_fts_exact").fetchone()[0]
            return {
                "case": label,
                "rows": rows,
                "digests": digests,
                "disk": disk,
                "runs_per_arm": RUNS,
                "median_ns": {k: int(statistics.median(v)) for k, v in timings.items()},
                "median_write_ns": {k: int(statistics.median(v))
                                    for k, v in write_ns.items() if v},
                "backfill_ns": backfill_ns,
                "backfill_batches": backfill_batches,
                "database_bytes": {
                    "old": _database_bytes(baseline), "new": _database_bytes(indexed),
                },
                "error_count": len(errors),
                "errors": errors,
                "work_count": {
                    "old_row_digest_upper_bound": rows * digests,
                    "new_digest_index_probes": digests,
                    "new_candidate_rows": postings,
                    "new_exact_fallback_rows": exceptional,
                    "backfill_rows": rows,
                    "write_updates_per_arm": 64 * RUNS,
                    "long_matching_tool_outputs": long_tools,
                    "nul_text": with_nul,
                },
            }
        finally:
            baseline.close()
            indexed.close()


def main():
    results = []
    for case in CASES:
        for rows in SIZES:
            try:
                results.append(benchmark(rows, case))
            except Exception as exc:
                results.append({
                    "case": case[0], "rows": rows, "error_count": 1,
                    "errors": [{"error": type(exc).__name__ + ": " + str(exc)}],
                    "work_count": {"old_row_digest_upper_bound": rows * case[1],
                                   "new_digest_index_probes": case[1]},
                })
    print(json.dumps({
        "benchmark": "dsa-history-mentions",
        "status": "unreviewed-measurements",
        "results": results,
    }, sort_keys=True))
    return 1 if any(r["error_count"] for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
