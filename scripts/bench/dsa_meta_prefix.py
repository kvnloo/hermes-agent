#!/usr/bin/env python3
"""Stdlib-only old-SCAN vs NOCASE-indexed state_meta prefix benchmark.

Run on groot: python scripts/bench/dsa_meta_prefix.py
Seven alternating runs per arm; reported row-work counts are estimates, not
instrumented SQLite page/VM counts. No performance claim until measured.
"""

import json
import random
import sqlite3
import statistics
import time


SIZES = (1_000, 10_000, 100_000)
RUNS = 7
OLD_SQL = "SELECT key, value FROM state_meta NOT INDEXED WHERE key LIKE ? ESCAPE '\\'"
NEW_SQL = (
    "SELECT key, value FROM state_meta INDEXED BY idx_state_meta_key_nocase"
    " WHERE key COLLATE NOCASE >= ?"
)


def _escape_like(text):
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _upper(prefix):
    folded = "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in prefix)
    for pos in range(len(folded) - 1, -1, -1):
        cp = ord(folded[pos])
        if cp < 0x10FFFF:
            return folded[:pos] + chr(cp + 1)
    return None


def _new_query(prefix):
    if "\x00" in prefix:
        return OLD_SQL, [_escape_like(prefix) + "%"]
    upper = _upper(prefix)
    sql = NEW_SQL
    args = [prefix]
    if upper is not None:
        sql += " AND key COLLATE NOCASE < ?"
        args.append(upper)
    sql += " AND key LIKE ? ESCAPE '\\' ORDER BY rowid"
    args.append(_escape_like(prefix) + "%")
    return sql, args


def _rows(conn, arm, prefix):
    if not prefix:
        return []
    if arm == "old":
        return conn.execute(OLD_SQL, (_escape_like(prefix) + "%",)).fetchall()
    sql, params = _new_query(prefix)
    return conn.execute(sql, params).fetchall()


def _build(n):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE state_meta (key TEXT PRIMARY KEY, value TEXT)")
    rng = random.Random(1107)
    chars = ("a", "A", "%", "_", "\\", "/", "🧪", "é", "\U0010ffff")
    values = []
    # Edge cases include a duplicate UPSERT; keep exactly n distinct keys.
    for i in range(n - 12):
        stem = "loop:" if i % 44 == 0 else "LOOP:" if i % 44 == 1 else "other:"
        key = stem + f"{i:07d}" + rng.choice(chars)
        values.append((key, str(i)))
    values.extend([
        ("LOOP:dup", "first"), ("LOOP:dup", "updated"),
        ("LoOp:%", "percent"), ("loop:_", "underscore"), ("loop:\\", "backslash"),
        ("loop:🧪", "non-bmp"), ("loop:\U0010ffff", "max-codepoint"),
        ("loop:\U0010ffff-tail", "max-codepoint-tail"),
        ("loop:" + json.dumps({"path": r"C:\data\test"}, ensure_ascii=True), "json-escaped"),
        ('LOOP:a"ZZAa', "quoted-upper-z"),
        ('LOOP:a"[tail', "quoted-bracket"),
        ("LOOP:éZtail", "unicode-z"),
        ("LOOP:\x00tail", "embedded-nul"),
    ])
    conn.executemany(
        "INSERT INTO state_meta(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        values,
    )
    conn.execute("CREATE INDEX idx_state_meta_key_nocase ON state_meta(key COLLATE NOCASE)")
    return conn


def _candidate_count(conn, prefix):
    if not prefix:
        return 0
    if "\x00" in prefix:
        return conn.execute("SELECT count(*) FROM state_meta").fetchone()[0]
    upper = _upper(prefix)
    sql = (
        "SELECT count(*) FROM state_meta INDEXED BY idx_state_meta_key_nocase "
        "WHERE key COLLATE NOCASE >= ?"
    )
    params = [prefix]
    if upper is not None:
        sql += " AND key COLLATE NOCASE < ?"
        params.append(upper)
    return conn.execute(sql, params).fetchone()[0]


def _benchmark(n):
    conn = _build(n)
    path = json.dumps({"path": r"C:\data\test"}, ensure_ascii=True)
    prefixes = (
        "", "loop:", "LOOP:", "lOoP:", "loop:%", "loop:_", "loop:\\",
        "loop:\U0010ffff", "loop:🧪", "loop:" + path, "other:", "missing:",
        'LOOP:a"Z', "LOOP:éZ", "LOOP:\x00tail",
    )
    try:
        baseline = {prefix: _rows(conn, "old", prefix) for prefix in prefixes}
        actual_n = conn.execute("SELECT count(*) FROM state_meta").fetchone()[0]
        candidates = sum(_candidate_count(conn, prefix) for prefix in prefixes)
        samples = {"old": [], "new": []}
        errors = {"old": 0, "new": 0}
        matched = {"old": 0, "new": 0}
        for repeat in range(RUNS):
            order = ("old", "new") if repeat % 2 == 0 else ("new", "old")
            for arm in order:
                start = time.perf_counter_ns()
                results = [_rows(conn, arm, prefix) for prefix in prefixes]
                samples[arm].append(time.perf_counter_ns() - start)
                errors[arm] += sum(
                    result != baseline[prefix] for prefix, result in zip(prefixes, results)
                )
                matched[arm] += sum(len(rows) for rows in results)
        return {
            "size_requested": n,
            "rows": actual_n,
            "runs": RUNS,
            "prefixes": len(prefixes),
            "old": {
                "median_ns_7": statistics.median(samples["old"]),
                "error_count": errors["old"],
                "work_count": {
                    "estimated_candidate_rows_per_run": actual_n * (len(prefixes) - 1),
                    "returned_rows_all_runs": matched["old"],
                },
            },
            "new": {
                "median_ns_7": statistics.median(samples["new"]),
                "error_count": errors["new"],
                "work_count": {
                    "estimated_candidate_rows_per_run": candidates,
                    "returned_rows_all_runs": matched["new"],
                },
            },
            "work_count_note": "estimated candidates, not measured SQLite visits",
        }
    finally:
        conn.close()


def main():
    for n in SIZES:
        print(json.dumps(_benchmark(n), ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
