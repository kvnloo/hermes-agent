#!/usr/bin/env python3
"""Compare one JSON disk parse with repeated no-copy memo hits.

Stdlib only, synthetic 1k/10k/100k JSON rows, seven alternating reads per arm.
Reports measured medians, comparison flags, error counts and work counts as JSON.
No measurement is asserted here; groot decides KEEP/REVERT on its harness.

Run: python -m scripts.bench.dsa_models_dev_nocopy_memo
"""

from __future__ import annotations

import json
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import json_disk_memo as memo


SIZES = (1_000, 10_000, 100_000)
REPEATS = 7


def _make_registry(rows: int) -> dict[str, Any]:
    labels = ("", "%", "_", r"C:\catalog\_100%", "模型", "a\\b")
    return {
        "providers": [
            {
                "id": i % 11,
                "name": labels[i % len(labels)],
                "path": r"C:\registry\model_%\\" + str(i),
                "models": {"model": f"model-{i}", "limits": {"context": i + 1}},
            }
            for i in range(rows)
        ]
    }


def _old_reader(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def _measure(path: Path, expected: dict[str, Any], size: int) -> dict[str, Any]:
    times: dict[str, list[int]] = {"old_parse": [], "memo_hit": []}
    errors = {"old_parse": 0, "memo_hit": 0}
    memo.clear_json_disk_memo()
    try:
        if memo.read_json_disk_memo(path) != expected:
            errors["memo_hit"] += 1
    except (OSError, ValueError, TypeError):
        errors["memo_hit"] += 1

    readers: tuple[tuple[str, Callable[[Path], Any]], ...] = (
        ("old_parse", _old_reader),
        ("memo_hit", memo.read_json_disk_memo),
    )
    for repetition in range(REPEATS):
        # Reverse order on alternate repetitions, avoiding a fixed warm-cache bias.
        for label, reader in (readers if repetition % 2 == 0 else readers[::-1]):
            started = time.perf_counter_ns()
            try:
                data = reader(path)
            except (OSError, ValueError, TypeError):
                elapsed = time.perf_counter_ns() - started
                errors[label] += 1
            else:
                elapsed = time.perf_counter_ns() - started
                if data != expected:
                    errors[label] += 1
            times[label].append(elapsed)

    memo_parses = memo.json_disk_memo_parse_count()
    result = {}
    for label, parse_calls in (("old_parse", REPEATS), ("memo_hit", memo_parses)):
        median_ns = int(statistics.median(times[label]))
        result[label] = {
            "median_ns": median_ns,
            "median_ms": round(median_ns / 1_000_000, 3),
            "runs": REPEATS,
            "error_count": errors[label],
            "work_count": {
                "json_parses": parse_calls,
                "rows_parsed": parse_calls * size,
                "rows_copied": 0,
                "rows_returned": REPEATS * size,
            },
        }
    result["memo_hit_cheaper_than_one_parse"] = (
        result["memo_hit"]["median_ns"] < result["old_parse"]["median_ns"]
    )
    return result


def main() -> None:
    results = []
    with tempfile.TemporaryDirectory(prefix="dsa-models-dev-nocopy-") as directory:
        for size in SIZES:
            expected = _make_registry(size)
            path = Path(directory) / f"models-{size}.json"
            with path.open("w", encoding="utf-8") as stream:
                json.dump(expected, stream, ensure_ascii=True)
            results.append({"size_rows": size, **_measure(path, expected, size)})
    print(json.dumps({"benchmark": "dsa-models-dev-nocopy-memo",
                      "repetitions": REPEATS, "results": results}))


if __name__ == "__main__":
    main()
