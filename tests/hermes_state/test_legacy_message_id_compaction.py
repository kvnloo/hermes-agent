"""A legacy message id must not be truncated into another row's address (#143402)."""

import sqlite3

from hermes_state import SessionDB


def test_legacy_null_and_fractional_ids_do_not_name_rows_during_compaction(tmp_path):
    """An upgraded store can carry NULL ids and REAL ids that aren't valid integer addresses."""
    from agent.context_compressor import _DB_PERSISTED_MARKER

    path = tmp_path / "state.db"
    db = SessionDB(db_path=path)
    try:
        db.create_session("s1", "cli", model="test/model")
        db.append_message("s1", "user", "held")
        db.append_message("s1", "assistant", "fractional")
        ddl = db._conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'messages'").fetchone()[0]
        stored = [tuple(row) for row in db._conn.execute(
            "SELECT session_id, role, content, timestamp FROM messages "
            "WHERE session_id = 's1' ORDER BY id").fetchall()]
    finally:
        db.close()

    legacy = ddl.replace("id INTEGER PRIMARY KEY AUTOINCREMENT", "id INTEGER")
    assert legacy != ddl, "the fixture requires the shipped messages DDL"
    conn = sqlite3.connect(path)
    try:
        conn.execute("DROP TABLE messages")
        conn.execute(legacy)
        conn.executemany(
            "INSERT INTO messages (session_id, role, content, timestamp) "
            "VALUES (?, ?, ?, ?)", stored)
        conn.execute("UPDATE messages SET id = 1.5 WHERE content = 'fractional'")
        assert conn.execute(
            "SELECT COUNT(*) FROM messages WHERE id IS NULL").fetchone()[0] == 1
        assert conn.execute(
            "SELECT typeof(id) FROM messages WHERE content = 'fractional'").fetchone()[0] == "real"
        conn.commit()
    finally:
        conn.close()

    db = SessionDB(db_path=path)
    try:
        # NULL cannot be named; REAL 1.5 cannot be safely treated as integer id 1.
        assert db._matching_active_ids(db._conn, "s1", {"role": "user", "content": "held"}) == []
        assert db._matching_active_ids(
            db._conn, "s1", {"role": "assistant", "content": "fractional"}) == []

        count = db.archive_and_compact(
            "s1", [{"role": "user", "content": "summary"}],
            covered_ids=[],
            unresolved_held=[{"role": "user", "content": "held", _DB_PERSISTED_MARKER: True}],
        )
        assert count == 1
        assert [row["content"] for row in db._conn.execute(
            "SELECT content FROM messages WHERE session_id = 's1' AND active = 1"
        ).fetchall()] == ["summary"]
    finally:
        db.close()
