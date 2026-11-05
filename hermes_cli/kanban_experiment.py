"""Check opt-in throughput experiment receipts without changing Kanban state.

Run ``python -m hermes_cli.kanban_experiment experiment.json``. Attach its
JSON output with the existing ``hermes kanban attach`` command. Exit codes:
0 accepted, 1 rejected, 2 invalid or insufficient evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any


class InvalidEvidence(ValueError):
    """The receipt does not satisfy the experiment contract."""


def _object(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise InvalidEvidence(f"{label} must be an object")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidEvidence(f"{label} must be a nonempty string")
    return value


def _parse(document: dict) -> tuple[list[str], dict[str, list[dict[str, float]]]]:
    if type(document.get("schema")) is not int or document["schema"] != 1:
        raise InvalidEvidence("schema must be 1")
    names = document.get("required_metrics")
    if not isinstance(names, list) or not names:
        raise InvalidEvidence("required_metrics must be a nonempty list")
    names = [_text(name, "required metric") for name in names]
    if len(set(names)) != len(names):
        raise InvalidEvidence("required_metrics contains duplicates")
    cohort = _object(document.get("cohort"), "cohort")
    if set(cohort) != {"host", "workload", "toolchain"}:
        raise InvalidEvidence("cohort requires host, workload, and toolchain")
    for key, value in cohort.items():
        _text(value, f"cohort.{key}")
    sources = _object(document.get("sources"), "sources")
    if set(sources) != {"baseline", "candidate"}:
        raise InvalidEvidence("sources requires baseline and candidate")
    for source in sources.values():
        if not isinstance(source, str) or re.fullmatch(r"[0-9a-f]{64}", source) is None:
            raise InvalidEvidence("sources must contain lowercase SHA-256 digests")
    if sources["baseline"] == sources["candidate"]:
        raise InvalidEvidence("baseline and candidate sources must differ")
    seen = set()
    samples = {}
    for side in ("baseline", "candidate"):
        rows = document.get(side)
        if not isinstance(rows, list):
            raise InvalidEvidence(f"{side} must be a list")
        samples[side] = []
        for raw in rows:
            row = _object(raw, f"{side} run")
            identity = _text(row.get("receipt_id"), "receipt_id")
            if identity in seen:
                raise InvalidEvidence(f"duplicate receipt_id: {identity}")
            seen.add(identity)
            if row.get("source_sha256") != sources[side]:
                raise InvalidEvidence(f"{side} source does not match contract")
            if row.get("cohort") != cohort:
                raise InvalidEvidence(f"{side} cohort does not match contract")
            if row.get("correctness_passed") is not True:
                raise InvalidEvidence(f"{side} correctness gate did not pass")
            metrics = _object(row.get("metrics"), f"{side} metrics")
            missing = sorted(set(names) - set(metrics))
            if missing:
                raise InvalidEvidence(f"{side} missing required metrics: {', '.join(missing)}")
            values = {}
            for name in names:
                value = metrics[name]
                try:
                    valid = type(value) in (int, float) and math.isfinite(value) and value > 0
                except OverflowError:
                    valid = False
                if not valid:
                    raise InvalidEvidence(f"{side} metric {name} must be finite and positive")
                values[name] = float(value)
            samples[side].append(values)
    return names, samples


def evaluate(document: Any) -> dict:
    """Return a conservative, advisory decision for one predeclared comparison."""
    try:
        document = _object(document, "experiment")
        canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), allow_nan=False)
        digest = hashlib.sha256(canonical.encode()).hexdigest()
    except (InvalidEvidence, ValueError, TypeError, OverflowError) as exc:
        return {"schema": 1, "outcome": "invalid", "reason": str(exc)}
    result = {"schema": 1, "input_sha256": digest, "outcome": "invalid"}
    try:
        names, samples = _parse(document)
    except InvalidEvidence as exc:
        return {**result, "reason": str(exc)}
    result["sources"] = document["sources"]
    result["measurement_counts"] = {side: len(rows) for side, rows in samples.items()}
    if min(result["measurement_counts"].values()) < 3:
        return {**result, "outcome": "insufficient-evidence", "reason": "need three distinct runs on both sides"}
    # Stay in log space so even extreme finite inputs cannot overflow.
    medians = {
        side: {name: statistics.median(math.log(row[name]) for row in rows) for name in names}
        for side, rows in samples.items()
    }
    gains = {name: medians["candidate"][name] - medians["baseline"][name] for name in names}
    aggregate = statistics.fmean(gains.values())
    reference = medians["baseline"]
    composites = {
        side: [statistics.fmean(math.log(row[name]) - reference[name] for name in names) for row in rows]
        for side, rows in samples.items()
    }
    if min(gains.values()) < math.log(0.97):
        reason = "per-metric regression exceeds 3%"
    elif aggregate < math.log(1.01):
        reason = "aggregate gain below 1%"
    elif min(composites["candidate"]) <= max(composites["baseline"]):
        reason = "gain not separated from baseline runs"
    else:
        reason = "accepted"
    return {
        **result,
        "outcome": "accepted" if reason == "accepted" else "rejected",
        "reason": reason,
        "metric_log_ratios": gains,
        "aggregate_log_ratio": aggregate,
        "advisory_only": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    args = parser.parse_args(argv)
    try:
        decision = evaluate(json.loads(args.experiment.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        decision = {"schema": 1, "outcome": "invalid", "reason": str(exc)}
    print(json.dumps(decision, sort_keys=True, indent=2, allow_nan=False))
    return {"accepted": 0, "rejected": 1}.get(decision["outcome"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
