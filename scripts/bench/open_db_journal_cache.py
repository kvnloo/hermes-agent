#!/usr/bin/env python3
"""Measure the original probe against the WAL-only memoized probe on real opens.

Run from the repository: python scripts/bench/open_db_journal_cache.py
No third-party benchmark dependencies; the actual Hermes open_db stack is used.
An old arm disables the fingerprint so each read uses the unchanged reference
probe. Runs alternate AB/BA; modes stay identical and never downgrade WAL.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import hermes_state_wal as wal
from hermes_cli.sqlite_util import open_db


def run_once(path: Path, count: int, cached: bool) -> dict[str, float | int]:
    original_key = wal._journal_mode_file_key
    original_probe = wal._read_journal_mode_uncached
    probes = 0
    errors = 0

    def counting_probe(conn: sqlite3.Connection) -> str | None:
        nonlocal probes
        probes += 1
        return original_probe(conn)

    with wal._journal_mode_cache_lock:
        wal._journal_mode_cache.clear()
    wal._journal_mode_file_key = original_key if cached else lambda _conn: None
    wal._read_journal_mode_uncached = counting_probe
    try:
        started = time.perf_counter()
        for _ in range(count):
            try:
                with closing(open_db(path, db_label="dsa-open-db-bench",
                                     busy_timeout_ms=10_000, foreign_keys=True)) as conn:
                    row = conn.execute("SELECT COUNT(*) FROM bench_rows").fetchone()
                    if row is None or row[0] != 1:
                        errors += 1
            except (OSError, sqlite3.Error):
                errors += 1
        elapsed = time.perf_counter() - started
    finally:
        wal._journal_mode_file_key = original_key
        wal._read_journal_mode_uncached = original_probe
    return {"seconds": elapsed, "errors": errors, "work_count": count, "pragma_probes": probes}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[1000, 10000, 100000])
    parser.add_argument("--runs", type=int, default=7)
    args = parser.parse_args()
    if args.runs < 1 or any(n < 1 for n in args.sizes):
        parser.error("runs and sizes must be positive")

    with tempfile.TemporaryDirectory(prefix="dsa-journal-probe-") as home:
        os.environ["HERMES_HOME"] = home
        path = Path(home) / "probe%_雪.db"
        # Keep the WAL sidecar alive across short-lived opens; no writes occur
        # during either arm, so cache invalidation measures stable generations.
        with closing(sqlite3.connect(path)) as anchor:
            actual = anchor.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if actual != "wal":
                raise RuntimeError(f"WAL baseline unavailable: {actual}")
            anchor.execute("CREATE TABLE bench_rows (v TEXT)")
            anchor.execute("INSERT INTO bench_rows VALUES (?)", ("x",))
            anchor.commit()
            report = []
            for n in args.sizes:
                results = {"old": [], "new": []}
                for repetition in range(args.runs):
                    order = ("old", "new") if repetition % 2 == 0 else ("new", "old")
                    for arm in order:
                        results[arm].append(run_once(path, n, cached=(arm == "new")))
                for arm in ("old", "new"):
                    samples = results[arm]
                    report.append({
                        "mechanism": arm,
                        "input_size": n,
                        "unit": "short_lived_opens",
                        "runs": args.runs,
                        "median_seconds": statistics.median(s["seconds"] for s in samples),
                        "median_pragma_probes": statistics.median(s["pragma_probes"] for s in samples),
                        "error_count": sum(s["errors"] for s in samples),
                        "work_count": sum(s["work_count"] for s in samples),
                    })
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
