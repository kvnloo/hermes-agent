#!/usr/bin/env python3
"""stdlib old-vs-memo JSON disk reader benchmark; no network or host assumptions.

Run from the repository root:
    python -m scripts.bench.dsa_models_dev_memo

Results are descriptive, not a speedup claim. The harness interleaves seven
old/new reads at each of 1k, 10k, and 100k JSON rows. Timing excludes
correctness comparison and file generation. Groot owns final ABAB measurement.
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
    times: dict[str, list[int]] = {"old": [], "memo": []}
    errors = {"old": 0, "memo": 0}
    readers: tuple[tuple[str, Callable[[Path], Any]], ...] = (
        ("old", _old_reader),
        ("memo", memo.read_json_disk_memo),
    )
    for _ in range(REPEATS):
        for label, reader in readers:
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
    for label, parse_calls, copy_calls in (
        ("old", REPEATS, 0),
        ("memo", memo_parses, REPEATS),
    ):
        ns = statistics.median(times[label])
        result[label] = {
            "median_ns": int(ns),
            "median_ms": round(ns / 1_000_000, 3),
            "runs": REPEATS,
            "error_count": errors[label],
            "work_count": {
                "json_parses": parse_calls,
                "rows_parsed": parse_calls * size,
                "rows_copied": copy_calls * size,
                "rows_returned": REPEATS * size,
            },
        }
    return result


def main() -> None:
    results = []
    with tempfile.TemporaryDirectory(prefix="dsa-models-dev-memo-") as directory:
        for size in SIZES:
            expected = _make_registry(size)
            path = Path(directory) / f"models-{size}.json"
            with path.open("w", encoding="utf-8") as stream:
                json.dump(expected, stream, ensure_ascii=True)
            memo.clear_json_disk_memo()
            results.append({"size_rows": size, **_measure(path, expected, size)})
    print(json.dumps({"benchmark": "dsa-models-dev-memo", "repetitions": REPEATS, "results": results}))


if __name__ == "__main__":
    main()
