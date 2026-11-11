"""Follow-up probes for RFC #143379 comment 6412944809 (xngg1021), run on the PR heads.

PASS = the comment's claim reproduces on the checked-out head.

P1 (#140008 @ e543544a): preserve_session() writes kind="message"; DreamCycle.light_sleep()
   stages only LOAD_BEARING_KINDS, so nothing preserved by the integration is ever staged.
P2 (#139606 @ 5b31ccb7): verify_post_write() reads the in-memory entry list, not the file,
   so it attests a remove while the file on disk still holds old_text.
"""
import importlib.util
import json

import pytest


def _has(mod):
    return importlib.util.find_spec(mod) is not None


@pytest.mark.skipif(not _has("tools.spa_integration"), reason="not the #140008 head")
def test_p1_preserved_items_never_staged():
    from tools.spa_integration import preserve_session
    from tools.dream_cycle import DreamCycle, LOAD_BEARING_KINDS

    class Store:
        def __init__(self):
            self.writes = []

        def add(self, target, content):
            self.writes.append((target, content))
            return {"success": True}

    store = Store()
    msgs = [{"role": "user", "content": f"decision: keep {m} measured verified 12 of 12 at tools/x.py:4"}
            for m in ("receipt", "decision", "falsifier", "steer", "measured", "doctrine")]
    doc = preserve_session(store, "probe", msgs)
    assert doc, "preserve_session preserved nothing (markers did not match)"
    payload = json.loads([c for t, c in store.writes if t.startswith("doc:")][0])
    kinds = {i["kind"] for i in payload["load_bearing"]}
    assert kinds == {"message"} and not kinds & LOAD_BEARING_KINDS
    assert DreamCycle().light_sleep([payload]) == 0, "claim: 100% of preserved items skipped"


@pytest.mark.skipif(not _has("tools.write_gate"), reason="not the #139606 head")
def test_p2_readback_checks_memory_not_disk(tmp_path, monkeypatch):
    from tools.memory_tool import MemoryStore
    from tools.write_gate import verify_post_write

    monkeypatch.setattr("tools.memory_tool.get_memory_dir", lambda: tmp_path)
    store = MemoryStore(memory_char_limit=5000, user_char_limit=3000)
    store.load_from_disk()
    old = "Deploy key rotation happens on Fridays."
    store.add("memory", old)
    store.add("memory", "Unrelated entry stays.")
    path = store._path_for("memory")

    # Case A: the file write is lost (fault injection: _write_file no-op) during remove.
    real_write = type(store)._write_file
    monkeypatch.setattr(type(store), "_write_file", staticmethod(lambda p, e: None))
    res = store.remove("memory", old)
    monkeypatch.setattr(type(store), "_write_file", real_write)
    assert res.get("success") is True
    assert old in path.read_text(encoding="utf-8"), "disk still holds old_text"
    assert verify_post_write(store, "memory", "remove", old) is None, "claim: attests from memory"

    # Case B: a concurrent writer restores the entry on disk after the remove lands.
    store2 = MemoryStore(memory_char_limit=5000, user_char_limit=3000)
    store2.load_from_disk()
    old2 = "Unrelated entry stays."
    assert store2.remove("memory", old2).get("success") is True
    path.write_text(path.read_text(encoding="utf-8") + "\n§\n" + old2, encoding="utf-8")
    assert old2 in path.read_text(encoding="utf-8")
    assert verify_post_write(store2, "memory", "remove", old2) is None
