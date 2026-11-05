"""Preservation contracts for bounded curated memory, using synthetic source IDs."""

import pytest

from tools.memory_tool import ENTRY_DELIMITER, MemoryStore


@pytest.fixture(params=["memory", "user"])
def bounded_store(request, tmp_path, monkeypatch):
    monkeypatch.setattr("tools.memory_tool.get_memory_dir", lambda: tmp_path)
    store = MemoryStore(memory_char_limit=500, user_char_limit=500)
    store.load_from_disk()
    return store, request.param, tmp_path / ("USER.md" if request.param == "user" else "MEMORY.md")


OWNER_FACTS = [
    "[source:fixture-owner-1] ln means last night.",
    "[source:fixture-owner-2] Use the existing owner checkout.",
]


def seed(store, target):
    for entry in OWNER_FACTS:
        assert store.add(target, entry)["success"]


def test_repeated_overflow_and_duplicates_do_not_grow_or_evict(bounded_store):
    store, target, path = bounded_store
    seed(store, target)
    before = path.read_bytes()
    for _ in range(12):
        store.reset_consolidation_failures()
        assert not store.add(target, "x" * 501)["success"]
        assert store.add(target, OWNER_FACTS[0])["success"]
        assert path.read_bytes() == before
    assert store._entries_for(target) == OWNER_FACTS
    assert store._char_count(target) <= store._char_limit(target)


def test_overflowing_replacement_keeps_source_references(bounded_store):
    store, target, path = bounded_store
    seed(store, target)
    before = path.read_bytes()
    assert not store.replace(target, "fixture-owner-1", "x" * 501)["success"]
    assert path.read_bytes() == before
    assert store._entries_for(target) == OWNER_FACTS


def test_explicit_prune_removes_only_named_ephemera(bounded_store):
    store, target, path = bounded_store
    seed(store, target)
    prefix = "[source:fixture-expired] Temporary build directory "
    filler = store._char_limit(target) - store._char_count(target) - len(ENTRY_DELIMITER) - len(prefix) - 10
    ephemeral = prefix + "x" * filler
    assert store.add(target, ephemeral)["success"]
    before = len(path.read_text())
    replacement = "[source:fixture-new] Use source-linked recall for old details."
    assert not store.add(target, replacement)["success"]
    result = store.apply_batch(target, [
        {"action": "add", "content": replacement},
        {"action": "remove", "old_text": "fixture-expired"},
    ])
    assert result["success"]
    assert len(path.read_text()) < before
    reloaded = MemoryStore(memory_char_limit=500, user_char_limit=500)
    reloaded.load_from_disk()
    assert reloaded._entries_for(target) == OWNER_FACTS + [replacement]
    assert "fixture-expired" not in reloaded.format_for_system_prompt(target)
    assert reloaded._char_count(target) <= reloaded._char_limit(target)


@pytest.mark.parametrize("selector", ["", "fixture-owner", "not-present"])
def test_unsafe_delete_aborts_entire_batch(bounded_store, selector):
    store, target, path = bounded_store
    seed(store, target)
    before = path.read_bytes()
    result = store.apply_batch(target, [
        {"action": "add", "content": "[source:fixture-new] New fact."},
        {"action": "remove", "old_text": selector},
    ])
    assert not result["success"]
    assert path.read_bytes() == before
    assert store._entries_for(target) == OWNER_FACTS


def test_correction_reaches_next_snapshot_without_changing_current_prompt(bounded_store):
    store, target, _ = bounded_store
    seed(store, target)
    store.load_from_disk()
    frozen = store.format_for_system_prompt(target)
    correction = "[source:fixture-owner-2; correction:fixture-owner-3] Use an isolated worktree when dirty."
    assert store.replace(target, "fixture-owner-2", correction)["success"]
    assert store.format_for_system_prompt(target) == frozen
    reloaded = MemoryStore(memory_char_limit=500, user_char_limit=500)
    reloaded.load_from_disk()
    assert correction in reloaded.format_for_system_prompt(target)
    assert OWNER_FACTS[0] in reloaded.format_for_system_prompt(target)
    assert OWNER_FACTS[1] not in reloaded.format_for_system_prompt(target)


def test_stale_writer_preserves_new_source_entry(bounded_store):
    store, target, _ = bounded_store
    seed(store, target)
    other = MemoryStore(memory_char_limit=500, user_char_limit=500)
    other.load_from_disk()
    added = "[source:fixture-owner-3] Retain original source IDs."
    assert other.add(target, added)["success"]
    assert store.remove(target, "fixture-owner-1")["success"]
    store.load_from_disk()
    assert store._entries_for(target) == [OWNER_FACTS[1], added]


def test_oversized_external_append_is_not_deleted(bounded_store):
    store, target, path = bounded_store
    seed(store, target)
    with path.open("a") as stream:
        stream.write("\n[source:fixture-external] Keep this owner correction. " + "x" * 501)
    before = path.read_bytes()
    result = store.remove(target, "fixture-owner-1")
    assert not result["success"]
    assert path.read_bytes() == before
    assert result.get("drift_backup")


def test_oversized_existing_memory_is_not_automatically_pruned(bounded_store):
    store, target, path = bounded_store
    entries = OWNER_FACTS + ["[source:fixture-legacy] " + "x" * 501]
    path.write_text(ENTRY_DELIMITER.join(entries) + "\n")
    before = path.read_bytes()
    store.load_from_disk()
    assert path.read_bytes() == before
    assert store._entries_for(target) == entries
    assert not store.add(target, "[source:fixture-new] Another fact.")["success"]
    assert path.read_bytes() == before
