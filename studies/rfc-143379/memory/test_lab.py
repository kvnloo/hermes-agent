from pathlib import Path
from threading import Event as Signal, Thread
import tempfile
import pytest

from lab import IsolatedStore, SourceArchive, BoundedDocReader


def test_restore_read_returns_exact_disk_state(tmp_path):
    s = IsolatedStore(tmp_path)
    assert s.add("memory", "First lesson")["success"]
    before = (tmp_path / "MEMORY.md").read_bytes()
    assert s.read("memory")["entries"] == ["First lesson"]
    assert (tmp_path / "MEMORY.md").read_bytes() == before


def test_read_detects_chain_and_does_not_inject_body(tmp_path):
    s = IsolatedStore(tmp_path)
    s.add("memory", "Link: @doc:principles")
    assert s.add("doc:principles", "private, not automatically in prompt")["success"]
    anchor = s.read("memory")
    assert "chain_docs" in anchor
    assert anchor["chain_docs"][0]["name"] == "principles"
    assert "private, not" not in repr(anchor)
    assert s.read("doc:principles")["entries"] == ["private, not automatically in prompt"]


def test_orphan_read_remains_possible_but_write_refused(tmp_path):
    s = IsolatedStore(tmp_path)
    s.add("memory", "Link: @doc:history")
    s.add("doc:history", "2014 design")
    (tmp_path / "MEMORY.md").write_text("Ref removed", encoding="utf-8")
    assert s.read("memory")["orphan_docs"][0]["name"] == "history"
    assert s.read("doc:history")["entries"] == ["2014 design"]
    assert not s.add("doc:history", "new write")["success"]


def test_chain_doc_uncapped_but_read_response_is_unbounded(tmp_path):
    s = IsolatedStore(tmp_path)
    s.add("memory", "Link: @doc:large")
    entry = "x" * 131072
    assert s.add("doc:large", entry)["success"]
    whole = s.read("doc:large")
    assert len(whole["entries"][0]) == 131072
    bounded = BoundedDocReader(max_bytes=4096).read(tmp_path / "docs" / "large.md")
    assert bounded["bytes"] == 4096 and bounded["next_cursor"] == 4096


def test_invalid_doc_names(tmp_path):
    s = IsolatedStore(tmp_path)
    for name in ("../escape", "/etc/passwd", "./relative", "../../x"):
        with pytest.raises(ValueError):
            s.read("doc:" + name)


def test_concurrent_read_can_roll_back_in_memory_entries(tmp_path):
    """Deterministic schedule of PR-style read: old raw captured, newer locked
    add commits, then reader writes old entries into shared in-memory cache.
    The raw file is NOT lost; only the in-memory entries are rolled back."""
    s = IsolatedStore(tmp_path)
    s.add("memory", "original")
    raw_captured = Signal()
    allow_reader = Signal()

    def pause_after_disk_read(path, raw):
        if getattr(__import__('threading').current_thread(), 'name') == 'reader':
            raw_captured.set()
            assert allow_reader.wait(timeout=4)
        return raw

    s._read_hook = pause_after_disk_read
    t = Thread(name="reader", target=lambda: s.read("memory"))
    t.start()
    assert raw_captured.wait(timeout=4)
    assert s.add("memory", "newer")["success"]
    allow_reader.set()
    t.join(timeout=4)
    assert not t.is_alive()
    assert "newer" in s._read_file(tmp_path / "MEMORY.md")
    assert s.memory_entries == ["original"]  # PR-style unlocked read caused cache rollback
    assert s.read("memory")["entries"] == ["original", "newer"]


def test_source_backed_correction_and_scope(tmp_path):
    a = SourceArchive()
    old = a.append(scope="hermes", source_id="log-1", value="Use v1")
    a.append(scope="hermes", source_id="log-2", value="Use v2", replaces_id=old.event_id)
    assert a.retrieve(scope="hermes", source_id="log-1")["value"] == "Use v2"
    assert a.retrieve(scope="unrelated", source_id="log-1")["verdict"] == "ABSTAIN"


def test_unknown_scope_does_not_become_global(tmp_path):
    a = SourceArchive()
    a.append(scope=None, source_id="unknown", value="secrets")
    assert a.retrieve(scope="hermes", source_id="unknown")["verdict"] == "ABSTAIN"


def test_tampered_evidence_is_rejected(tmp_path):
    a = SourceArchive()
    a.append(scope="hermes", source_id="log-1", value="true fact")
    a.sources["log-1"] = "modified fact"
    assert a.retrieve(scope="hermes", source_id="log-1")["verdict"] == "ABSTAIN"


def test_synthetic_non_user_correction_does_not_supersede_user(tmp_path):
    a = SourceArchive()
    orig = a.append(scope="hermes", source_id="e1", value="user decision")
    a.append(scope="hermes", source_id="e2", value="model guess", replaces_id=orig.event_id, caller="synthetic")
    assert a.retrieve(scope="hermes", source_id="e1")["value"] == "user decision"


def test_corrupted_disk_read_fails_without_fabricating_content(tmp_path):
    s = IsolatedStore(tmp_path)
    s.add("memory", "legit")
    (tmp_path / "MEMORY.md").write_bytes(b"\xff")
    result = s.read("memory")
    assert not result["success"]


def test_corrected_source_hash_verified(tmp_path):
    a = SourceArchive()
    original = a.append(scope="hermes", source_id="decision-old", value="use A")
    a.append(scope="hermes", source_id="decision-new", value="use B", replaces_id=original.event_id)
    a.sources["decision-new"] = "tampered"  # Original hash intact; correction hash changed
    result = a.retrieve(scope="hermes", source_id="decision-old")
    assert result["verdict"] == "ABSTAIN"
    assert result["reason"] == "corrected source revision mismatch"


def test_bounded_unicode_read_is_lossless(tmp_path):
    p = tmp_path / "utf8.md"
    expected = "start ✨ accents café / 中文 / continuation " * 40
    p.write_text(expected, encoding="utf-8")
    reader = BoundedDocReader(max_bytes=29)
    chunks, cursor = [], 0
    while True:
        result = reader.read(p, cursor)
        chunks.append(result["data"])
        if result["next_cursor"] is None:
            break
        assert result["next_cursor"] > cursor
        cursor = result["next_cursor"]
    assert "".join(chunks) == expected


def test_bounded_read_rejects_out_of_range_cursor(tmp_path):
    p = tmp_path / "small.md"
    p.write_text("hello")
    with pytest.raises(ValueError):
        BoundedDocReader().read(p, start=9999)


def test_anchor_reference_gate_is_toctou_between_files(tmp_path):
    """A pre-lock anchor check followed by a doc write is not atomic with
    another thread unlinking the anchor. This is a model of the PR's ordering.
    """
    s = IsolatedStore(tmp_path)
    assert s.add("memory", "Index: @doc:notes")["success"]
    assert s.add("doc:notes", "old")["success"]
    gate_checked, continue_write = Signal(), Signal()
    normal_gate = s._anchor_gate

    def gated(target):
        permitted = normal_gate(target)
        if target == "doc:notes":
            gate_checked.set()
            assert continue_write.wait(timeout=4)
        return permitted

    s._anchor_gate = gated
    result = {}

    def write_doc():
        result.update(s.add("doc:notes", "new after unlink"))

    t = Thread(target=write_doc)
    t.start()
    assert gate_checked.wait(timeout=4)
    (tmp_path / "MEMORY.md").write_text("No longer references notes", encoding="utf-8")
    continue_write.set()
    t.join(timeout=4)
    assert not t.is_alive()
    assert result["success"] is True   # The gate passed against stale anchor state.
    assert "new after unlink" in s.read("doc:notes")["entries"]
    assert "notes" in s.orphan_doc_names()


def test_original_file_is_unchanged_by_failed_budget_write(tmp_path):
    s = IsolatedStore(tmp_path, anchor_limit=40)
    s.add("memory", "keep exact evidence")
    before = (tmp_path / "MEMORY.md").read_bytes()
    assert not s.add("memory", "x" * 500)["success"]
    assert (tmp_path / "MEMORY.md").read_bytes() == before


def test_shared_read_lock_prevents_rollback_in_control(tmp_path):
    """Mitigation control: serialize read and add on the SAME per-target lock.
    Unlike the PR-style read this ends with disk/cache agreement.
    """
    s = IsolatedStore(tmp_path)
    s.add("memory", "original")
    reader_has_raw = Signal()
    release_reader = Signal()
    add_started = Signal()

    def hook(path, raw):
        if __import__('threading').current_thread().name == "locked-reader":
            reader_has_raw.set()
            assert release_reader.wait(timeout=4)
        return raw

    s._read_hook = hook
    path = s._path_for("memory")

    def locked_read():
        with s._locks[path]:
            s.read("memory")

    def writer():
        add_started.set()
        s.add("memory", "newer")

    reader = Thread(target=locked_read, name="locked-reader")
    reader.start()
    assert reader_has_raw.wait(timeout=4)
    writer_thread = Thread(target=writer, name="locked-writer")
    writer_thread.start()
    assert add_started.wait(timeout=4)
    release_reader.set()
    reader.join(timeout=4)
    writer_thread.join(timeout=4)
    assert not reader.is_alive() and not writer_thread.is_alive()
    assert s.memory_entries == s._read_file(tmp_path / "MEMORY.md") == ["original", "newer"]
