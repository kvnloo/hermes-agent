"""Session/branch metadata browsing and durable copied-session boundaries (#567)."""
from __future__ import annotations

import json
import threading

import pytest

from hermes_state import SessionDB
from tui_gateway import server


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    db = SessionDB(db_path=tmp_path / "state.db")
    monkeypatch.setattr(server, "_db", db)
    monkeypatch.setattr(server, "_make_agent", lambda *a, **kw: pytest.fail("Browsing must not build an agent"))
    yield db
    db.close()


def create(db, key, *, parent=None, title=None, source="tui", config=None, **kw):
    db.create_session(key, source=source, parent_session_id=parent, cwd=f"/work/{key}", model_config=config, **kw)
    db.set_session_title(key, title or key)


def rpc(method="session.tree", **params):
    return server.handle_request({"id": "tree-request", "method": method, "params": params})


def test_nested_filtered_forks_keep_ancestor_context_without_reading_transcripts(store, monkeypatch):
    create(store, "root")
    create(store, "fork", parent="root", config={"_branched_from": "root"})
    create(store, "nested", parent="fork", title="needle", config={"_branched_from": "fork"})
    monkeypatch.setattr(store, "get_resume_conversations", lambda *a: pytest.fail("No transcript read"))
    before = store._conn.total_changes
    result = rpc(query="needle")["result"]
    assert [row["id"] for row in result["sessions"]] == ["nested"]
    assert [row["id"] for row in result["ancestors"]] == ["fork", "root"]
    assert result["sessions"][0]["edge_kind"] == "fork"
    assert result["total"] == 1
    assert store._conn.total_changes == before


def test_active_ancestry_is_first_and_selection_survives_sort(store):
    create(store, "root", title="ZZZ root")
    create(store, "current", parent="root", title="ZZZ fork", config={"_branched_from": "root"})
    create(store, "other", title="AAA")
    create(store, "selected", title="YYY")
    for sort in ("recent", "title", "path"):
        result = rpc(active_session_id="current", selected_session_id="selected", sort=sort)["result"]
        ids = [row["id"] for row in result["sessions"]]
        assert set(ids[:2]) == {"root", "current"}
        assert ids[2] == "selected"


def test_missing_parents_cycles_and_compression_are_metadata_not_recursive_walks(store):
    for key in ("missing", "cycle-a", "cycle-b", "compressed", "tip"):
        create(store, key)
    # Simulate a legacy/corrupt store imported without FK enforcement.
    store._conn.execute("PRAGMA foreign_keys = OFF")
    store._write_sql("UPDATE sessions SET parent_session_id = 'gone' WHERE id = 'missing'")
    store._conn.execute("PRAGMA foreign_keys = ON")
    store._write_sql("UPDATE sessions SET parent_session_id = 'cycle-b' WHERE id = 'cycle-a'")
    store._write_sql("UPDATE sessions SET parent_session_id = 'cycle-a' WHERE id = 'cycle-b'")
    store._write_sql("UPDATE sessions SET end_reason = 'compression' WHERE id = 'compressed'")
    store._write_sql("UPDATE sessions SET parent_session_id = 'compressed' WHERE id = 'tip'")
    result = rpc(active_session_id="cycle-a")["result"]
    assert len(result["sessions"]) == 5
    by_id = {row["id"]: row for row in result["sessions"]}
    assert by_id["missing"]["parent_session_id"] == "gone"
    assert by_id["tip"]["edge_kind"] == "continuation"
    assert by_id["cycle-a"]["parent_session_id"] == "cycle-b"


def test_more_than_two_hundred_sessions_have_exact_disjoint_pages_and_global_search(store):
    for index in range(237):
        create(store, f"session-{index:03}")
    pages, offset = [], 0
    while offset is not None:
        result = rpc(offset=offset, limit=200, sort="title")["result"]
        pages.extend(row["id"] for row in result["sessions"])
        offset = result["next_offset"]
        assert result["total"] == 237
    assert len(pages) == len(set(pages)) == 237
    assert pages == sorted(pages)
    assert rpc(query="session-236")["result"]["sessions"][0]["id"] == "session-236"


def test_rename_returns_durable_readback_and_sort_path_search_follow_it(store):
    create(store, "one")
    create(store, "two")
    result = rpc("session.rename", session_key="two", title="  A new name  ")["result"]
    assert result == {"session_key": "two", "title": "A new name"}
    assert store.get_session_title("two") == "A new name"
    assert [row["id"] for row in rpc(sort="title")["result"]["sessions"]] == ["two", "one"]
    assert [row["id"] for row in rpc(query="/work/two")["result"]["sessions"]] == ["two"]
    assert rpc(query="A new")["result"]["sessions"][0]["title"] == "A new name"


def test_rename_rejects_invalid_wire_values_before_writing(store):
    create(store, "one")
    assert rpc("session.rename", session_key="one", title=123)["error"]["code"] == 4000
    assert rpc("session.rename", title="missing target")["error"]["code"] == 4000
    assert store.get_session_title("one") == "one"


def test_listing_and_rename_never_expose_hidden_archived_or_internal_sessions(store):
    for key, source in (("visible", "tui"), ("hidden", "tui"), ("archived", "tui"), ("internal", "tool")):
        create(store, key, source=source)
    store.set_session_hidden("hidden", True)
    store.set_session_archived("archived", True)
    assert [row["id"] for row in rpc()["result"]["sessions"]] == ["visible"]
    for key in ("hidden", "archived", "internal", "absent"):
        assert rpc("session.rename", session_key=key, title="no")["error"]["code"] == 4007


@pytest.mark.parametrize("params", [{"offset": -1}, {"limit": 501}, {"sort": "sql injection"}])
def test_page_contract_rejects_invalid_bounds(store, params):
    assert rpc(**params)["error"]["code"] == 4000


def test_fork_boundary_is_durable_and_not_recomputed_from_child_row_ids(store, monkeypatch):
    create(store, "parent")
    store.append_message("parent", "user", "question")
    store.append_message("parent", "assistant", "answer")
    history = store.get_messages_as_conversation("parent", include_row_ids=True)
    source_row = history[0]["_row_id"]
    session = {"agent": None, "history": history, "history_lock": threading.Lock(), "running": False,
               "session_key": "parent", "source": "tui", "cwd": "/work/parent"}
    monkeypatch.setitem(server._sessions, "parent-live", session)
    key = rpc("session.fork", session_id="parent-live", target_message_id=source_row)["result"]["session_id"]
    config = json.loads(store.get_session(key)["model_config"])
    assert config["_branch_point"] == {"parent_session_id": "parent", "message_id": source_row, "copied_message_count": 1}
    store.append_message(key, "assistant", "child-only reply")
    result = {row["id"]: row for row in rpc()["result"]["sessions"]}[key]
    assert result["branch_message_id"] == source_row
    assert result["copied_message_count"] == 1
    assert result["message_count"] == 2


def test_legacy_and_bad_branch_boundaries_are_explicitly_unknown(store):
    create(store, "root")
    create(store, "old", parent="root", config={"_branched_from": "root"})
    create(store, "bad", parent="root", config={"_branched_from": "root", "_branch_point": {
        "parent_session_id": "root", "message_id": True, "copied_message_count": "99"}})
    for row in rpc()["result"]["sessions"]:
        assert row["branch_message_id"] is None
        assert row["copied_message_count"] is None


def test_secondary_profile_listing_and_rename_stay_in_own_store(store, tmp_path, monkeypatch):
    other_home = tmp_path / "other"
    other_home.mkdir()
    other = SessionDB(db_path=other_home / "state.db")
    create(store, "same", title="launch title")
    create(other, "same", title="secondary title")
    monkeypatch.setattr(server, "_profile_home", lambda profile: other_home if profile == "secondary" else None)
    try:
        assert rpc(profile="secondary")["result"]["sessions"][0]["title"] == "secondary title"
        rpc("session.rename", profile="secondary", session_key="same", title="secondary renamed")
        assert other.get_session_title("same") == "secondary renamed"
        assert store.get_session_title("same") == "launch title"
    finally:
        other.close()
