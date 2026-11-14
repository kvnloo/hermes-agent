#!/usr/bin/env python3
"""Cold/warm JSON and a real offline models.dev consumer, old vs memo.

Stdlib benchmark harness (plus the repository's actual models.dev module).
The registry is provider-keyed, as in models.dev, not a synthetic providers
list. Both arms force the same in-memory registry state before each consumer
call to avoid counting the already-hot in-memory fast path as disk savings.
All numbers are produced at run time; this script claims no speedup.

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
from agent import models_dev as md

SIZES = (1_000, 10_000, 100_000)
REPEATS = 7
PROVIDERS = ("xai", "openai", "anthropic", "google", "openrouter",
             "deepseek", "mistral", "groq", "cohere", "together", "cerebras")


def _make_registry(rows: int) -> dict[str, Any]:
    registry: dict[str, Any] = {
        key: {"name": key, "models": {}} for key in PROVIDERS
    }
    names = ("", "%", "_", r"C:\catalog\_100%", "模型", "a\\b", "東京")
    for i in range(rows):
        provider = PROVIDERS[i % len(PROVIDERS)]
        registry[provider]["models"][f"model-{i}"] = {
            "name": names[i % len(names)],
            "limit": {"context": 8192 + i, "output": 4096},
            "modalities": {"input": ["text", "image"] if i % 3 == 0 else ["text"],
                           "output": ["text"]},
            "cost": {"input": i / 1000, "output": i / 500},
            "path": r"C:\models\_%" + str(i),
        }
    return registry


def _legacy_read(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def _consumer(path: Path, reader: Callable[[Path], Any]) -> tuple[int, str | None]:
    """Exercise the real _registry_models -> fetch_models_dev -> disk path."""
    saved = (md._models_dev_cache, md._models_dev_cache_time,
             md.read_json_disk_memo, md._get_cache_path)
    try:
        md._models_dev_cache = {}
        md._models_dev_cache_time = 0
        md.read_json_disk_memo = reader
        md._get_cache_path = lambda: path
        models = md._registry_models("xai", allow_network=False)
        return len(models or {}), next(iter(models), None) if models else None
    finally:
        (md._models_dev_cache, md._models_dev_cache_time,
         md.read_json_disk_memo, md._get_cache_path) = saved


def _run(path: Path, registry: dict[str, Any], rows: int) -> dict[str, Any]:
    expected_consumer = (len(registry["xai"]["models"]), "model-0")
    modes = ("disk_cold", "disk_warm", "consumer_cold", "consumer_warm")
    output: dict[str, Any] = {}
    for mode in modes:
        times = {"old": [], "memo": []}
        errors = {"old": 0, "memo": 0}
        calls = {"old": 0, "memo": 0}
        parses = {"old": 0, "memo": 0}
        memo.clear_json_disk_memo()
        if mode.endswith("warm"):
            memo.read_json_disk_memo(path)
        for iteration in range(REPEATS):
            # AB/BA order; no fixed always-first arm.
            for label in (("old", "memo") if iteration % 2 == 0 else ("memo", "old")):
                reader = _legacy_read if label == "old" else memo.read_json_disk_memo
                if mode.endswith("cold") and label == "memo":
                    memo.clear_json_disk_memo()
                operation = (
                    (lambda: _consumer(path, reader))
                    if mode.startswith("consumer") else (lambda: reader(path))
                )
                started = time.perf_counter_ns()
                try:
                    actual = operation()
                except Exception:
                    elapsed = time.perf_counter_ns() - started
                    errors[label] += 1
                else:
                    elapsed = time.perf_counter_ns() - started
                    if actual != (expected_consumer if mode.startswith("consumer") else registry):
                        errors[label] += 1
                times[label].append(elapsed)
                calls[label] += 1
                if label == "old" or mode.endswith("cold"):
                    parses[label] += 1
        output[mode] = {
            label: {
                "median_ns": int(statistics.median(times[label])),
                "median_ms": round(statistics.median(times[label]) / 1_000_000, 3),
                "runs": REPEATS,
                "error_count": errors[label],
                "work_count": {
                    "operations": calls[label],
                    "json_parses": parses[label],
                    "rows_decoded": rows * parses[label],
                    "rows_frozen": rows * parses[label] if label == "memo" else 0,
                    "consumer_lookups": calls[label] if mode.startswith("consumer") else 0,
                    "consumer_models_returned": (
                        expected_consumer[0] * calls[label]
                        if mode.startswith("consumer") else 0
                    ),
                },
            }
            for label in ("old", "memo")
        }
    return output


def main() -> None:
    results = []
    with tempfile.TemporaryDirectory(prefix="dsa-models-dev-memo-") as directory:
        for rows in SIZES:
            registry = _make_registry(rows)
            path = Path(directory) / f"models-{rows}.json"
            with path.open("w", encoding="utf-8") as stream:
                json.dump(registry, stream, ensure_ascii=True)
            results.append({"size_rows": rows, "cases": _run(path, registry, rows)})
    print(json.dumps({
        "benchmark": "dsa-models-dev-readonly-memo",
        "repetitions": REPEATS,
        "results": results,
    }))


if __name__ == "__main__":
    main()
