"""Behavior contracts for the order_by_last_active tip-ordering CTE in
``list_sessions_rich`` (recursive chain walk + per-chain freshness MAX).

These pin the observable semantics — chain-tip freshness wins, heartbeat vs
message vs started_at fallback, search across chain members, delegate/tool
exclusions — so the CTE internals can be re-planned without changing meaning.
"""
import sqlite3

import pytest

from hermes_state import SessionDB

T0 = 1_700_000_000


@pytest.fixture()
def db(tmp_path):
    session_db = SessionDB(db_path=tmp_path / "test_state.db")
    yield session_db
    session_db.close()


def _stamp(db, sid, **cols):
    db._conn.execute(
        f"UPDATE sessions SET {', '.join(f'{k}=?' for k in cols)} WHERE id=?",
        (*cols.values(), sid),
    )
    db._conn.commit()


def _chain(db, root, mids, tip):
    """Build a compression chain root -> mids -> tip; every link but the tip
    ends with end_reason='compression'."""
    prev = root
    for i, mid in enumerate(mids):
        db.create_session(mid, "cli", parent_session_id=prev)
        _stamp(db, prev, ended_at=T0 + 10 + i, end_reason="compression")
        prev = mid
    db.create_session(tip, "cli", parent_session_id=prev)
    _stamp(db, prev, ended_at=T0 + 20 + len(mids), end_reason="compression")


def test_tip_ordering_uses_freshest_chain_activity(db):
    """Effective activity is the freshest of heartbeat and message timestamps
    across the whole compression chain (started_at fallback); rows sort by it."""
    # Heartbeat newer than message on the tip: chain effective = t0+200.
    db.create_session("root1", "cli")
    _stamp(db, "root1", started_at=T0, last_activity_at=None)
    _chain(db, "root1", [], "tip1")
    _stamp(db, "tip1", started_at=T0 + 20, last_activity_at=T0 + 200)
    db.append_message("tip1", "user", "old news", timestamp=T0 + 100)
    # Message newer than heartbeat: chain effective = t0+280.
    db.create_session("root3", "cli")
    _stamp(db, "root3", started_at=T0 + 10, last_activity_at=None)
    _chain(db, "root3", [], "tip3")
    _stamp(db, "tip3", started_at=T0 + 40, last_activity_at=T0 + 150)
    db.append_message("tip3", "user", "fresh news", timestamp=T0 + 280)
    # No activity at all: falls back to started_at = t0+250.
    db.create_session("solo", "cli")
    _stamp(db, "solo", started_at=T0 + 250, last_activity_at=None)
    # Plain session whose newest message sets its activity: t0+300.
    db.create_session("root2", "cli")
    _stamp(db, "root2", started_at=T0 + 30, last_activity_at=None)
    db.append_message("root2", "user", "newest", timestamp=T0 + 300)

    rows = db.list_sessions_rich(
        limit=20, order_by_last_active=True, project_compression_tips=False)
    assert [r["id"] for r in rows] == ["root2", "root3", "solo", "root1"]


def test_tip_ordering_search_spans_chain_and_ignores_excluded_children(db):
    """search_query matches a mid-chain title; delegate and tool children of a
    compression-ended parent never contribute their activity to the chain."""
    db.create_session("root1", "cli")
    _chain(db, "root1", ["mid1"], "tip1")
    _stamp(db, "root1", started_at=T0, last_activity_at=T0 + 10)
    _stamp(db, "mid1", started_at=T0 + 5, last_activity_at=None)
    _stamp(db, "mid1", title="SecretProject notes")
    _stamp(db, "tip1", started_at=T0 + 20, last_activity_at=T0 + 60)
    # Excluded children with FAR newer activity: must not leak into the chain.
    db.create_session("del1", "cli", parent_session_id="root1",
                      model_config={"_delegate_from": "root1"})
    db.append_message("del1", "user", "delegate work", timestamp=T0 + 999)
    db.create_session("tool1", "tool", parent_session_id="root1")
    db.append_message("tool1", "user", "tool work", timestamp=T0 + 998)
    # Plain session active between the chain tip and the excluded children.
    db.create_session("other", "cli")
    _stamp(db, "other", started_at=T0 + 5, last_activity_at=T0 + 500)

    rows = db.list_sessions_rich(
        limit=20, order_by_last_active=True, search_query="secretproject",
        project_compression_tips=False)
    ids = [r["id"] for r in rows]
    assert ids == ["root1"]  # admitted via mid1's title; excluded kids stay out
    # Without the search filter the excluded children's t0+999/t0+998 activity
    # must not outrank `other`'s t0+500: chain effective stays t0+60.
    rows = db.list_sessions_rich(
        limit=20, order_by_last_active=True, project_compression_tips=False)
    ids = [r["id"] for r in rows]
    assert ids.index("other") < ids.index("root1")
    assert "del1" not in ids and "tool1" not in ids
