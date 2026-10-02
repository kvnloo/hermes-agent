"""Bounded browsing must not let one malformed metadata row hide healthy peers."""

import pytest

from hermes_state import SessionDB


@pytest.mark.parametrize("raw", [None, "{}", '{"_branched_from":"root"}', '{"_branched_from":'])
def test_bounded_browse_preserves_metadata_and_healthy_peer(tmp_path, raw):
    db = SessionDB(tmp_path / "state.db")
    try:
        db.create_session("root", source="cli")
        db.append_message("root", role="user", content="original conversation")
        db.end_session("root", "compression")
        db.create_session("tip", source="cli", parent_session_id="root")
        db.append_message("tip", role="user", content="continued conversation")
        db.create_session("peer", source="cli")
        db.append_message("peer", role="user", content="independent conversation")
        db._conn.execute("UPDATE sessions SET model_config = ? WHERE id = 'tip'", (raw,))
        db._conn.commit()
        # The existing rich-browser path already tolerates this marker read.
        reference = db.list_sessions_rich(limit=10, order_by_last_active=True)
        assert "peer" in {row["id"] for row in reference}
        try:
            rows = db.list_recent_sessions_bounded(limit=10)
            ids = {row["id"] for row in rows}
            assert "peer" in ids
            if raw in (None, "{}"):
                assert "tip" in ids
            elif raw == '{"_branched_from":"root"}':
                assert {"root", "tip"} <= ids
        finally:
            assert db._conn.execute("SELECT model_config FROM sessions WHERE id = 'tip'").fetchone()[0] == raw
            assert db._conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        db.close()
