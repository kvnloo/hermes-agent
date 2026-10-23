"""Downstream exploratory probes for Hermes RFC #143379 and consent #116788.

Copy into <worktree>/tests/tools/test_rfc_homework.py (runner does this) and run
with that checkout's scripts/run_tests.sh. Some safety probes are expected to
FAIL on the pinned PR heads: that is the diagnostic, not a green test claim.
Every fact used here is synthetic; HOME/HERMES_HOME is pytest-isolated.
"""
from __future__ import annotations

import json
from pathlib import Path
from threading import Event, Thread, current_thread

import pytest

from tools.memory_tool import MemoryStore, memory_tool
from tools.skill_provenance import reset_current_write_origin, set_current_write_origin

MARKER = "SYNTHETIC-CONSENT-CODE-PX7412"


@pytest.fixture()
def memory_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr("tools.memory_tool.get_memory_dir", lambda: tmp_path)
    store = MemoryStore(memory_char_limit=200000, user_char_limit=200000)
    store.load_from_disk()
    return store, tmp_path


def test_read_dispatch_contract(memory_env):
    """READ should be functional when promised by a PR's model-facing schema."""
    store, root = memory_env
    assert store.add("memory", "Synthetic read anchor")["success"]
    result = json.loads(memory_tool(action="read", target="memory", store=store))
    assert result["success"] is True
    assert "Synthetic read anchor" in result["entries"]
    assert (root / "MEMORY.md").exists()


def test_read_concurrency_snapshot(memory_env, monkeypatch):
    """If read races an add, a store's disk entries must match its cached entries.

    On the reviewed PR diff read() does not use the writer's file lock, then
    updates the mutable in-memory cache. The deliberately paused reader consumes
    an old snapshot after the new append. A lock-sharing fix should pass.
    """
    store, root = memory_env
    if not hasattr(store, "read"):
        pytest.skip("This head has no MemoryStore.read")
    assert store.add("memory", "original")['success']
    captured = Event()
    resume_reader = Event()
    read_result = []
    write_result = []
    source_reader = store._read_raw_checked

    def paused_read(path):
        raw, ok = source_reader(path)
        if current_thread().name == "rfc_read_probe" and path.name == "MEMORY.md":
            captured.set()
            if not resume_reader.wait(timeout=8):
                raise TimeoutError("reader interleave release timed out")
        return raw, ok

    monkeypatch.setattr(store, "_read_raw_checked", paused_read)

    read_thread = Thread(name="rfc_read_probe", target=lambda: read_result.append(store.read("memory")))
    write_thread = Thread(name="rfc_write_probe", target=lambda: write_result.append(store.add("memory", "newer")))
    read_thread.start()
    try:
        assert captured.wait(8), "read did not reach captured snapshot"
        write_thread.start()
        write_thread.join(0.5)  # might block if implementation locks read + write
    finally:
        resume_reader.set()
    read_thread.join(8)
    write_thread.join(8)
    assert not read_thread.is_alive() and not write_thread.is_alive()
    assert read_result and read_result[0]["success"]
    assert write_result and write_result[0]["success"]
    raw = (root / "MEMORY.md").read_text(encoding="utf-8")
    assert "newer" in raw
    assert "newer" in store._entries_for("memory"), "read overwrote newer in-memory entries"


def test_chain_doc_reference_race(memory_env, monkeypatch):
    """A document write may not commit after its anchor was removed.

    The test waits after a successful _anchor_gate() check and removes the
    reference *before* the document's target lock is acquired. Avoid treating
    this as an established production bug before testing the actual PR head.
    """
    store, root = memory_env
    if not hasattr(store, "_anchor_gate"):
        pytest.skip("No chain-doc gate on this head")
    assert store.add("memory", "Pointer @doc:rfc-notes")["success"]
    approved = Event()
    continue_writer = Event()
    results = []
    original_gate = store._anchor_gate

    def pause_after_gate(target):
        result = original_gate(target)
        if target == "doc:rfc-notes" and current_thread().name == "rfc_doc_writer":
            approved.set()
            if not continue_writer.wait(timeout=8):
                raise TimeoutError("doc-write interleave release timed out")
        return result

    monkeypatch.setattr(store, "_anchor_gate", pause_after_gate)
    writer = Thread(name="rfc_doc_writer", target=lambda: results.append(store.add("doc:rfc-notes", "new fact")))
    writer.start()
    try:
        assert approved.wait(8), "doc write did not cross reference gate"
        assert store.remove("memory", "Pointer @doc:rfc-notes")["success"]
    finally:
        continue_writer.set()
    writer.join(8)
    assert not writer.is_alive() and results
    archive = root / "docs" / "rfc-notes.md"
    anchor = (root / "MEMORY.md").read_text(encoding="utf-8")
    assert not (archive.exists() and "new fact" in archive.read_text(encoding="utf-8")
                and "@doc:rfc-notes" not in anchor), "write committed after reference was removed"


def test_chain_doc_read_response_budget_candidate(memory_env):
    """Candidate 4 KiB response contract, NOT a currently accepted Hermes spec.

    This probes the cost of an uncapped doc + unbounded response; failing it
    establishes a *policy decision* for maintainers, not necessarily a bug.
    """
    store, _ = memory_env
    if not hasattr(store, "_doc") or not hasattr(store, "read"):
        pytest.skip("No chain-doc read on this head")
    assert store.add("memory", "Pointer @doc:large-notes")["success"]
    assert store.add("doc:large-notes", "X" * 131072)["success"]
    response = store.read("doc:large-notes")
    assert response["success"]
    assert len(json.dumps(response, ensure_ascii=False).encode("utf-8")) <= 4096, (
        "unbounded read response; 4 KiB is only a proposed exploratory budget"
    )


@pytest.fixture(scope="module")
def consent_cases():
    # JSON fixture is copied beside this test by run_exact_heads.sh.
    path = Path(__file__).with_name("rfc_consent_scenarios.json")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case_index", range(12))
def test_no_save_never_lands_in_memory_or_pending(memory_env, consent_cases, case_index):
    """12 write-boundary challenges; review model is deliberately bypassed.

    A no-save instruction was explicitly present in the synthetic original
    source, even when the candidate paraphrase omits it. Tests *retention*, not
    merely whether the proposed write was postponed for approval.
    """
    store, root = memory_env
    case = consent_cases[case_index]
    assert case["source_no_save"] is True
    assert case["target"] in ("memory", "user")
    token = set_current_write_origin("background_review")
    try:
        kwargs = {"target": case["target"], "store": store}
        if "operations" in case:
            kwargs["operations"] = case["operations"]
        else:
            kwargs.update({"action": "add", "content": case["content"]})
        result = json.loads(memory_tool(**kwargs))
    finally:
        reset_current_write_origin(token)
    # A rejection or 'staged' outcome is not necessarily safe: stage_write
    # stores the whole payload and the summary in a pending JSON file.
    persisted = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
                 and MARKER in p.read_text(encoding="utf-8", errors="replace")]
    assert not persisted, f"{case['id']}: forbidden marker persisted in {persisted}; result={result.get('staged', False)}"
