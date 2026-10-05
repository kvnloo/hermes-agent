"""SQLite rebuild failures retain the existing no-progress contract."""

import logging
import sqlite3

import pytest

from hermes_state import SessionDB


@pytest.mark.parametrize("error_type", [sqlite3.OperationalError, sqlite3.DatabaseError])
def test_rebuild_failure_rolls_back_and_reports_no_progress(tmp_path, monkeypatch, caplog, error_type):
    db = SessionDB(db_path=tmp_path / "state.db")
    connection = db._conn
    rollbacks = []

    class FailingRebuildConnection:
        def execute(self, sql, *args):
            if sql == "INSERT INTO messages_fts(messages_fts) VALUES('rebuild')":
                raise error_type("synthetic index rebuild failure")
            return connection.execute(sql, *args)

        def rollback(self):
            rollbacks.append(True)
            return connection.rollback()

        def __getattr__(self, name):
            return getattr(connection, name)

    try:
        if not db._fts_enabled:
            pytest.skip("FTS5 unavailable")
        db.create_session("ordinary", source="test")
        db.append_message("ordinary", "user", "ordinary persisted text")
        before = connection.execute("SELECT content FROM messages").fetchall()
        with monkeypatch.context() as patch:
            patch.setattr(db, "_conn", FailingRebuildConnection())
            patch.setattr(db, "_present_fts_tables", lambda: ["messages_fts"])
            with caplog.at_level(logging.WARNING):
                assert db.rebuild_fts() == 0
        assert rollbacks == [True]
        assert "FTS rebuild failed for messages_fts: synthetic index rebuild failure" in caplog.text
        assert connection.execute("SELECT content FROM messages").fetchall() == before
    finally:
        db.close()
