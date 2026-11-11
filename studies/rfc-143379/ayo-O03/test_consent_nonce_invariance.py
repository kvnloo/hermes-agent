"""Independent diagnostic, not author certification or end-to-end model consent.

Preserve each existing no-retain scenario's source_no_save, target, text, and
origin. Rename only the synthetic identifier. An identity-specific denial must
not be mistaken for an intent/provenance-based no-retain mechanism.
"""
import copy
import json
from pathlib import Path

import pytest

from tools.memory_tool import MemoryStore, memory_tool
from tools.skill_provenance import reset_current_write_origin, set_current_write_origin

OLD = "SYNTHETIC-CONSENT-CODE-PX7412"
NEW = "PRIVATE-EXPERIMENT-IDENTIFIER-NQ9281"


@pytest.mark.parametrize("case_index", range(12))
def test_no_retain_identifier_rename(tmp_path, monkeypatch, case_index):
    cases = json.loads(Path(__file__).with_name("rfc_consent_scenarios.json").read_text())
    original = cases[case_index]
    assert original["source_no_save"] is True
    assert OLD in json.dumps(original)
    case = json.loads(json.dumps(copy.deepcopy(original)).replace(OLD, NEW))
    assert case["source_no_save"] is True
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr("tools.memory_tool.get_memory_dir", lambda: tmp_path)
    store = MemoryStore(memory_char_limit=200000, user_char_limit=200000)
    store.load_from_disk()
    origin = set_current_write_origin("background_review")
    try:
        kwargs = {"target": case["target"], "store": store}
        if "operations" in case:
            kwargs["operations"] = case["operations"]
        else:
            kwargs.update(action="add", content=case["content"])
        result = json.loads(memory_tool(**kwargs))
    finally:
        reset_current_write_origin(origin)
    persisted = [str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")
                 if p.is_file() and NEW in p.read_text(encoding="utf-8", errors="replace")]
    assert not persisted, f"{case['id']}: renamed identifier persisted in {persisted}; staged={result.get('staged', False)}"
