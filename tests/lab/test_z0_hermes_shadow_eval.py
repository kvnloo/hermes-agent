from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "lab" / "z0_hermes_observer" / "evaluate_shadow.py"


def _load():
    spec = importlib.util.spec_from_file_location("evaluate_shadow_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row(p, y, latency=2.0):
    return {
        "verified_outcome": y,
        "decision": {
            "backend": "fake",
            "latency_ms": latency,
            "answers": [{
                "question_id": "api.attempt_will_fail",
                "probabilities": {"false": 1.0 - p, "true": p},
                "value": p >= 0.5,
            }],
        },
    }


def test_perfect_shadow_beats_base_rate_and_never_promotes():
    module = _load()
    report = module.evaluate([
        _row(0.01, False),
        _row(0.02, False),
        _row(0.98, True),
        _row(0.99, True),
    ])
    assert report["n"] == 4
    assert report["brier"] < report["base_rate_brier"]
    assert report["brier_improvement"] > 0
    assert report["accuracy_at_0_5"] == 1.0
    assert report["promotion_ready"] is False
    assert report["mean_latency_ms"] == 2.0


def test_missing_decisions_are_coverage_gaps_not_invented_predictions():
    module = _load()
    report = module.evaluate([
        {"verified_outcome": True},
        _row(0.8, True),
        {"verified_outcome": None, "decision": {}},
    ])
    assert report["n"] == 1
    assert report["positive_rate"] == 1.0


def test_no_scored_examples_is_explicit_zero_evidence():
    module = _load()
    report = module.evaluate([])
    assert report == {
        "schema": "z0int.hermes_shadow_eval.v1",
        "question_id": "api.attempt_will_fail",
        "n": 0,
    }
