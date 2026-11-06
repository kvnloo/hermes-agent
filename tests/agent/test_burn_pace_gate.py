import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from agent import burn_pace_gate as g


def _setup(tmp_path, monkeypatch, lanes, at=None):
    monkeypatch.setenv("BURN_GATE_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_BURN_GATE_OVERRIDE", raising=False)
    g._cache.update(at=0.0, key=None, val=None)
    (tmp_path / ".config/burn-gate").mkdir(parents=True)
    (tmp_path / ".config/burn-gate/pool-lanes.json").write_text(json.dumps(
        {"anthropic": {"ultra": "claude3", "sub2": "claude2", "tok": "claude"}}))
    (tmp_path / ".z0int/state/posture").mkdir(parents=True)
    row = {"at": at or datetime.now(UTC).isoformat(), "lanes": lanes}
    (tmp_path / ".z0int/state/posture/burn-pace.jsonl").write_text(json.dumps(row) + "\n")


E = [SimpleNamespace(label=n) for n in ("ultra", "sub2", "tok", "unmapped")]


def labels(xs):
    return [x.label for x in xs]


def test_exhausted_and_hot_rows_skipped_rest_coolest_first(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, {
        "claude3": {"weekly_used_pct": 100.0, "pace_ratio": None},
        "claude2": {"weekly_used_pct": 40.0, "pace_ratio": 0.6},
        "claude": {"weekly_used_pct": 12.0, "pace_ratio": 1.6},
    })
    assert labels(g.admit("anthropic", E)) == ["sub2", "unmapped"]


def test_stale_reading_fails_closed_for_mapped_rows(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, {"claude2": {"weekly_used_pct": 1.0, "pace_ratio": 0.1}},
           at="2020-01-01T00:00:00+00:00")
    assert labels(g.admit("anthropic", E)) == ["unmapped"]


def test_unmapped_provider_untouched_and_override(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, {})
    assert g.admit("openrouter", E) == E
    monkeypatch.setenv("HERMES_BURN_GATE_OVERRIDE", "1")
    assert g.admit("anthropic", E) == E
