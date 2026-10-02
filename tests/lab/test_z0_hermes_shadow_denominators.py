"""Denominator hygiene for the z0 shadow lab scripts (kvnloo/hermes-agent#319 sample collection).

Every failure stays in a denominator: unmatched observer rows are counted, a backend error on one
example is recorded on that row instead of aborting the run, and rows without a usable probability
are counted as coverage gaps.  None of this changes what Hermes does; the scripts run offline.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab" / "z0_hermes_observer"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"{name}_denominator_test", LAB / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _event(event, call, *, request_id="req", **fields):
    return {
        "schema": "z0int.hermes_observer_event.v1",
        "event": event,
        "identity": {"harness_id": "hermes", "session_id": "s", "turn_id": "t",
                     "trace_id": "trace", "api_request_id": request_id},
        "fields": {"api_call_count": call, **fields},
    }


def test_join_audit_counts_every_unmatched_row():
    module = _load("shadow_api_failure")
    rows = [
        _event("pre_api_request", 1, request_id="a"),
        _event("pre_api_request", 1, request_id="a", retry_count=1),  # overwrites the first pre
        _event("api_request_error", 1, request_id="a"),
        _event("pre_api_request", 1, request_id="b"),
        _event("post_api_request", 1, request_id="b"),
        _event("post_api_request", 7, request_id="ghost"),             # terminal without pre
        _event("pre_api_request", 1, request_id="c"),                  # never closed
        {"schema": "z0int.hermes_observer_event.v1", "event": "observer_rows_dropped",
         "identity": {"harness_id": "hermes"}, "fields": {"dropped_rows": 3}},
    ]
    audit = module.join_audit(rows)
    assert audit["n_pre"] == 4
    assert audit["n_joined"] == len(module.joined_examples(rows)) == 2
    assert audit["n_positive"] == 1 and audit["n_negative"] == 1
    assert audit["n_orphan_pre_overwritten"] == 1
    assert audit["n_orphan_pre_unclosed"] == 1
    assert audit["n_terminal_without_pre"] == 1
    assert audit["observer_rows_dropped"] == 3
    assert audit["n_pre"] == audit["n_joined"] + audit["n_orphan_pre_overwritten"] + audit["n_orphan_pre_unclosed"]


class _FlakyBackend:
    def __init__(self):
        self.calls = 0

    def evaluate(self, request):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("backend fell over")
        return "ok"


def _fake_z0int(monkeypatch, factory):
    base = types.ModuleType("z0int.backends.base")
    base.request_from_mapping = lambda raw: raw
    base.result_to_dict = lambda result: {"backend": "fake", "answers": [], "latency_ms": 1.0}
    registry = types.ModuleType("z0int.backends.registry")
    registry.create_backend = factory
    for name, mod in {"z0int": types.ModuleType("z0int"), "z0int.backends": types.ModuleType("z0int.backends"),
                      "z0int.backends.base": base, "z0int.backends.registry": registry}.items():
        monkeypatch.setitem(sys.modules, name, mod)


def test_backend_error_is_recorded_per_row_not_fatal(monkeypatch):
    module = _load("shadow_api_failure")
    backend = _FlakyBackend()
    _fake_z0int(monkeypatch, lambda name: backend)
    examples = [{"request": {"i": i}, "verified_outcome": False} for i in range(3)]
    rows = module.score_examples(examples, "fake", None)
    assert len(rows) == 3
    assert rows[0]["decision"] is not None and rows[2]["decision"] is not None
    assert rows[1]["decision"] is None
    assert rows[1]["backend_error"]["type"] == "RuntimeError"


def test_backend_that_cannot_start_yields_full_coverage_gap(monkeypatch):
    module = _load("shadow_api_failure")

    def broken(name):
        raise OSError("weights missing")

    _fake_z0int(monkeypatch, broken)
    examples = [{"request": {}, "verified_outcome": False}, {"request": {}, "verified_outcome": True}]
    rows = module.score_examples(examples, "fake", None)
    assert [row["decision"] for row in rows] == [None, None]
    assert all(row["backend_error"]["stage"] == "create" for row in rows)


def _scored(p, y, qid="verification_needed"):
    return {"verified_outcome": y, "decision": {"backend": "fake", "latency_ms": 3.0, "answers": [
        {"question_id": qid, "probabilities": {"false": 1 - p, "true": p}, "value": p >= 0.5}]}}


def test_evaluate_takes_question_id_and_reports_every_denominator():
    module = _load("evaluate_shadow")
    rows = [
        _scored(0.9, True),
        _scored(0.2, False),
        _scored(0.7, True, qid="api.attempt_will_fail"),     # other question: missing probability
        {"verified_outcome": False, "decision": None, "backend_error": {"type": "X"}},
        {"verified_outcome": None, "decision": _scored(0.5, True)["decision"]},  # unknown label
    ]
    report = module.evaluate(rows, question_id="verification_needed")
    assert report["question_id"] == "verification_needed"
    assert report["n"] == 2
    d = report["denominators"]
    assert d == {"n_rows": 5, "n_labelled": 4, "n_unknown_label": 1, "n_backend_error": 1,
                 "n_missing_probability": 1, "n_scored": 2, "coverage": 0.5}


def test_evaluate_default_question_is_unchanged():
    module = _load("evaluate_shadow")
    report = module.evaluate([_scored(0.1, False, qid="api.attempt_will_fail")])
    assert report["question_id"] == "api.attempt_will_fail" and report["n"] == 1


class _FakeOllama:
    def __init__(self, top):
        self.top = top
        self.bodies = []

    def __call__(self, path, body):
        self.bodies.append((path, body))
        return {"message": {"content": self.top[0]["token"]},
                "logprobs": [{"token": self.top[0]["token"], "top_logprobs": self.top}]}


def _request():
    return {"state": {"tool_call_count": 2}, "request_id": "r1", "questions": [{
        "id": "verification_needed", "type": "boolean",
        "instructions": "Does this turn require an explicit verification pass before responding?",
        "criteria": {"false": "Safe to respond without extra verification",
                     "true": "Run verification before responding"}}]}


def test_ollama_backend_returns_renormalised_first_token_distribution():
    pytest.importorskip("z0int.backends.base")
    module = _load("ollama_logprob_backend")
    from z0int.backends.base import request_from_mapping
    fake = _FakeOllama([{"token": "true", "logprob": -0.2}, {"token": " False", "logprob": -1.8},
                        {"token": "maybe", "logprob": -3.0}])
    backend = module.OllamaLogprobBackend("qwen2.5:3b", post=fake, revision="digest")
    result = backend.evaluate(request_from_mapping(_request()))
    probs = result.answers[0].probabilities
    assert set(probs) == {"false", "true"}
    assert 0.0 < probs["false"] < probs["true"] < 1.0      # a real distribution, never one-hot
    assert abs(probs["true"] + probs["false"] - 1.0) < 1e-9
    assert result.diagnostics["covered_mass"] < 1.0
    body = fake.bodies[0][1]
    assert body["logprobs"] is True and body["options"]["temperature"] == 0
    assert "tool_call_count" in json.dumps(body["messages"])


def test_ollama_backend_refuses_when_no_label_token_has_mass():
    pytest.importorskip("z0int.backends.base")
    module = _load("ollama_logprob_backend")
    from z0int.backends.base import request_from_mapping
    backend = module.OllamaLogprobBackend("m", post=_FakeOllama([{"token": "Sure", "logprob": -0.1}]), revision="d")
    with pytest.raises(ValueError):
        backend.evaluate(request_from_mapping(_request()))
