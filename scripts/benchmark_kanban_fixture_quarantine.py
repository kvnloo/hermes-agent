#!/usr/bin/env python3
"""Reproduce fixture-quarantine performance on an SQLite online-backup copy."""

import argparse
import hashlib
import json
import sqlite3
import statistics
import time
from pathlib import Path

PREDICATE = """(
    (tenant = 'bench' AND title GLOB 'bench [0-9]*'
     AND substr(title, 7) NOT GLOB '*[^0-9]*')
 OR (created_by IN ('desktop-e2e', 'preview-fixture') AND title LIKE 'Synthetic %')
 OR (created_at = 1787030032 AND created_by IS NULL AND tenant IS NULL
     AND title GLOB 'Long card [0-7] detail*')
)"""
QUERIES = {
    "list_active": "SELECT id, title, status FROM tasks WHERE status != 'archived' ORDER BY created_at DESC, id",
    "ready_dispatch_scan": "SELECT id FROM tasks WHERE status = 'ready' ORDER BY created_at, id",
    "board_status_counts": "SELECT status, count(*) FROM tasks GROUP BY status ORDER BY status",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(db: sqlite3.Connection, sql: str, warmups: int, runs: int) -> dict:
    for _ in range(warmups):
        db.execute(sql).fetchall()
    samples = []
    rows = 0
    for _ in range(runs):
        started = time.perf_counter_ns()
        result = db.execute(sql).fetchall()
        samples.append((time.perf_counter_ns() - started) / 1_000_000)
        rows = len(result)
    return {
        "sql": sql,
        "rows": rows,
        "median_ms": round(statistics.median(samples), 3),
        "min_ms": round(min(samples), 3),
        "max_ms": round(max(samples), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--copy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--warmups", type=int, default=3)
    parser.add_argument("--runs", type=int, default=15)
    args = parser.parse_args()
    if args.copy.exists():
        raise SystemExit(f"refusing to overwrite copy: {args.copy}")
    if args.warmups < 0 or args.runs < 1:
        raise SystemExit("warmups must be >= 0 and runs must be >= 1")

    source_before = sha256(args.source)
    with sqlite3.connect(f"file:{args.source}?mode=ro", uri=True) as source, sqlite3.connect(args.copy) as target:
        source.backup(target)
    source_after = sha256(args.source)
    if source_before != source_after:
        raise SystemExit("source DB file changed during online backup; retry from a stable source")
    copy_before = sha256(args.copy)

    db = sqlite3.connect(args.copy)
    classified = db.execute(f"SELECT count(*) FROM tasks WHERE {PREDICATE}").fetchone()[0]
    if classified != 26659:
        raise SystemExit(f"classification guard failed: expected 26659, got {classified}")
    before = {name: measure(db, sql, args.warmups, args.runs) for name, sql in QUERIES.items()}
    db.execute("BEGIN IMMEDIATE")
    db.execute(f"UPDATE tasks SET status='archived', claim_lock=NULL, claim_expires=NULL, worker_pid=NULL, current_run_id=NULL WHERE {PREDICATE}")
    active_after = db.execute(f"SELECT count(*) FROM tasks WHERE {PREDICATE} AND status != 'archived'").fetchone()[0]
    after = {name: measure(db, sql, args.warmups, args.runs) for name, sql in QUERIES.items()}
    db.rollback()
    db.close()
    copy_after = sha256(args.copy)
    if copy_before != copy_after:
        raise SystemExit("dry-run rollback changed copied DB bytes")

    evidence = {
        "runner_command": f"python {Path(__file__).resolve()} --source {args.source} --copy {args.copy} --output {args.output} --warmups {args.warmups} --runs {args.runs}",
        "copy_creation_method": "sqlite3.Connection.backup",
        "sqlite_version": sqlite3.sqlite_version,
        "source": str(args.source),
        "copy": str(args.copy),
        "source_sha256_before": source_before,
        "source_sha256_after": source_after,
        "copy_sha256_before": copy_before,
        "copy_sha256_after": copy_after,
        "warmup_runs": args.warmups,
        "measured_runs": args.runs,
        "classification_sql": f"SELECT count(*) FROM tasks WHERE {PREDICATE}",
        "classified_before": classified,
        "classified_active_after": active_after,
        "queries": {name: {"sql": sql, "before": before[name], "after": after[name]} for name, sql in QUERIES.items()},
    }
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    main()
