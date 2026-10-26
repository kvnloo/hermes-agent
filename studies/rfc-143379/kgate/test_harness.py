"""Hermes integration tests: run only in the hosted CI-parity environment."""
import json
from pathlib import Path
import socket

import pytest

from harness import exact_present, no_network, run_arm, verify_pin
from manifest import load_manifest, source


@pytest.fixture(autouse=True)
def isolation(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HERMES_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)


def test_exact_scorer_ignores_arguments():
    assert exact_present([{"role": "assistant", "content": "nothing", "tool_calls": ["target"]}], "target") == 0
    assert exact_present([{"role": "assistant", "content": "exact target here"}], "target") == 1


def test_frozen_manifest_rejects_drift(tmp_path):
    path = Path(__file__).with_name("frozen-manifest.json")
    payload, probes = load_manifest(path)
    assert len(probes) == 12
    payload["probes"][0]["target_literal"] += "changed"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="mismatch"):
        load_manifest(bad)


def test_real_repeated_boundary_is_reproducible():
    cc = verify_pin()
    _, probes = load_manifest(Path(__file__).with_name("frozen-manifest.json"))
    subset = [p for p in probes if p.session_seed == 10]
    first, trace = run_arm(cc, 10, 4, 10, subset, (2, 3))
    second, trace2 = run_arm(cc, 10, 4, 10, subset, (2, 3))
    assert first == second and trace == trace2
    assert len(trace) == 3
    assert trace[-1]["compression_count"] == 3
    assert trace[-1]["summary_calls"] == 3
    assert all(t["tokens_after"] < t["tokens_before"] for t in trace)
    assert sum(t["tool_results_pruned"] for t in trace) >= 3
    _, zero = run_arm(cc, 10, 4, 0, subset, (2, 3))
    assert trace[-1]["retained_K_tokens"] > zero[-1]["retained_K_tokens"]
