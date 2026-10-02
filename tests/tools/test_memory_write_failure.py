"""Live memory inventories advance only after an atomic write succeeds."""

import errno
import json
from pathlib import Path

import pytest

import utils
from tools.memory_tool import MemoryStore, memory_tool
from tools.memory_tool_store import ENTRY_DELIMITER


@pytest.fixture
def disk_store(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    store = MemoryStore()
    store.load_from_disk()
    for target in ("memory", "user"):
        assert store.add(target, "Original project fact")["success"]
        assert store.add(target, "Neighbor project fact")["success"]
    store.load_from_disk()
    return store


def _operation(store, target, action):
    if action == "add":
        return store.add(target, "New project fact")
    if action == "replace":
        return store.replace(target, "Original project fact", "Updated project fact")
    if action == "remove":
        return store.remove(target, "Original project fact")
    return store.apply_batch(target, [
        {"action": "replace", "old_text": "Original project fact", "content": "Updated project fact"},
        {"action": "add", "content": "New project fact"},
    ])


@pytest.mark.parametrize("target", ["memory", "user"])
@pytest.mark.parametrize("action", ["add", "replace", "remove", "batch"])
def test_failed_write_preserves_live_inventory_and_retry(disk_store, monkeypatch, target, action):
    store = disk_store
    path = store._path_for(target)
    original = path.read_bytes()
    entries = list(store._entries_for(target))
    frozen = store.format_for_system_prompt(target)
    replace = utils.os.replace
    attempts = []

    def fail_target(source, destination):
        if Path(destination) == path:
            attempts.append(Path(source).read_bytes())
            raise OSError(errno.ENOSPC, "fixture disk full")
        return replace(source, destination)

    with monkeypatch.context() as fault:
        fault.setattr(utils.os, "replace", fail_target)
        with pytest.raises(RuntimeError, match="Failed to write memory file"):
            _operation(store, target, action)
    assert len(attempts) == 1 and attempts[0] != original
    assert path.read_bytes() == original
    assert not list(path.parent.glob(".mem_*.tmp"))
    assert store._entries_for(target) == entries
    # This validation response reads the live inventory without another disk reload.
    response = json.loads(memory_tool(action="replace", target=target, store=store))
    assert response["current_entries"] == entries
    assert store.format_for_system_prompt(target) == frozen
    assert _operation(store, target, action)["success"]
    assert path.read_text() == ENTRY_DELIMITER.join(store._entries_for(target))
    assert path.read_bytes() != original
    assert store.format_for_system_prompt(target) == frozen


@pytest.mark.parametrize("target", ["memory", "user"])
@pytest.mark.parametrize("action", ["add", "replace", "remove", "batch"])
def test_successful_write_publishes_persisted_inventory(disk_store, target, action):
    store = disk_store
    frozen = store.format_for_system_prompt(target)
    assert _operation(store, target, action)["success"]
    entries = store._entries_for(target)
    assert store._path_for(target).read_text() == ENTRY_DELIMITER.join(entries)
    response = json.loads(memory_tool(action="replace", target=target, store=store))
    assert response["current_entries"] == entries
    assert store.format_for_system_prompt(target) == frozen
