"""Shared probe harness: cold-pointer resolution and the K-gate on one labeled set.

One fixture (``labeled_store``) seeds a store from a single labeled set. Items labeled
``pinned`` live in chain docs and are reached only through an ``@doc:`` pointer in the
MEMORY.md anchor; items labeled ``episodic`` are never written. The first test reloads the
store the way a compaction boundary does (``load_from_disk``) and resolves every pointer
cold. The second runs the RFC's long-session K-gate over per-cycle measurements keyed to
the same labels: the gate fails on any point at or past cycle 300, at any ratio in 4x-8x,
where K-window recitation is below the K=0 baseline.
"""
import json

import pytest

from tools.memory_tool import MemoryStore, memory_tool

LABELED_SET = (
    {"id": "p1", "label": "pinned", "doc": "paths-2026-11", "text": "deploy key lives in vault/ops/deploy"},
    {"id": "p2", "label": "pinned", "doc": "shas-2026-11", "text": "release tag v4.2 is commit 9f3c1e2"},
    {"id": "e1", "label": "episodic", "doc": None, "text": "user said thanks after the build"},
)
GATE_MIN_CYCLE, GATE_RATIOS = 300, (4, 8)


def k_gate(points):
    """``(passed, failing_points)``; a point is ``{cycle, ratio, k, baseline}`` in percent."""
    lo, hi = GATE_RATIOS
    failing = [p for p in points
               if p["cycle"] >= GATE_MIN_CYCLE and lo <= p["ratio"] <= hi and p["k"] - p["baseline"] < 0]
    return not failing, failing


@pytest.fixture()
def labeled_store(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.memory_tool.get_memory_dir", lambda: tmp_path)
    store = MemoryStore(memory_char_limit=400, user_char_limit=150)
    store.load_from_disk()
    for item in (i for i in LABELED_SET if i["label"] == "pinned"):
        anchor = f"{item['id']}: @doc:{item['doc']}"
        assert json.loads(memory_tool(action="add", target="memory", content=anchor, store=store))["success"]
        added = memory_tool(action="add", target="memory", doc=item["doc"], content=item["text"], store=store)
        assert json.loads(added)["success"]
    return store


def test_pinned_pointers_resolve_cold_after_a_reload(labeled_store):
    labeled_store.load_from_disk()  # what invalidate_system_prompt does at a compaction boundary
    snapshot = labeled_store.format_for_system_prompt("memory") or ""
    for item in LABELED_SET:
        if item["label"] == "episodic":
            assert item["text"] not in snapshot
            continue
        assert item["doc"] in snapshot and item["text"] not in snapshot  # pointer warm, body cold
        read = json.loads(memory_tool(action="read", target="memory", doc=item["doc"], store=labeled_store))
        assert read["entries"] == [item["text"]], (item["id"], read)


@pytest.mark.parametrize(("points", "passed"), [
    ([{"cycle": 150, "ratio": 8, "k": 17.8, "baseline": 15.6}], True),   # short run only: not gated
    ([{"cycle": 300, "ratio": 4, "k": 9.7, "baseline": 9.6}], True),
    ([{"cycle": 300, "ratio": 4, "k": 6.1, "baseline": 9.6}], False),   # the RFC's -3.5pp point
    ([{"cycle": 320, "ratio": 16, "k": 1.0, "baseline": 2.0}], True),   # 16x is outside the gated band
])
def test_k_gate_judges_the_worst_point(points, passed):
    assert k_gate(points)[0] is passed
