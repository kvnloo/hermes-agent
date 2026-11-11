"""Synthetic write-boundary diagnostics, not an end-to-end provenance test."""
import copy
import json
from pathlib import Path

import pytest

from tools.memory_tool import MemoryStore, memory_tool
from tools.skill_provenance import reset_current_write_origin, set_current_write_origin


@pytest.fixture()
def memory_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr("tools.memory_tool.get_memory_dir", lambda: tmp_path)
    store = MemoryStore(memory_char_limit=200000, user_char_limit=200000)
    store.load_from_disk()
    return store, tmp_path


@pytest.mark.parametrize("identifier", ["HELDOUT-CONSENT-CODE-TM5729", "CLIENT-REF-VZ8046"])
@pytest.mark.parametrize("case_index", range(12))
def test_heldout_identifier(memory_env, identifier, case_index):
    store, root = memory_env
    original = json.loads(Path(__file__).with_name("rfc_consent_scenarios.json").read_text())[case_index]
    assert original["source_no_save"] is True
    case = json.loads(json.dumps(copy.deepcopy(original)).replace("SYNTHETIC-CONSENT-CODE-PX7412", identifier))
    token = set_current_write_origin("background_review")
    try:
        kwargs = {"target": case["target"], "store": store}
        if "operations" in case:
            kwargs["operations"] = case["operations"]
        else:
            kwargs.update(action="add", content=case["content"])
        result = json.loads(memory_tool(**kwargs))
    finally:
        reset_current_write_origin(token)
    persisted = [str(p.relative_to(root)) for p in root.rglob("*")
                 if p.is_file() and identifier in p.read_text(encoding="utf-8", errors="replace")]
    assert not persisted, f"{case['id']}: persisted in {persisted}; staged={result.get('staged', False)}"


def test_orphan_name_is_not_hidden_by_longer_anchor(memory_env):
    store, root = memory_env
    assert store.add("memory", "See @doc:foo")['success']
    assert store.add("doc:foo", "recoverable synthetic original")['success']
    assert store.remove("memory", "See @doc:foo")['success']
    assert store.add("memory", "See @doc:foobar")['success']
    assert "foo" in store.orphan_doc_names()
    assert store.read("doc:foo")['success']
    assert (root / "docs/foo.md").exists()


def test_longer_anchor_does_not_authorize_orphan_write(memory_env):
    store, root = memory_env
    assert store.add("memory", "See @doc:foo")['success']
    assert store.add("doc:foo", "recoverable synthetic original")['success']
    assert store.remove("memory", "See @doc:foo")['success']
    assert store.add("memory", "See @doc:foobar")['success']
    before = (root / "docs/foo.md").read_bytes()
    result = store.add("doc:foo", "must not write through a different anchor")
    assert result['success'] is False, result
    assert (root / "docs/foo.md").read_bytes() == before
