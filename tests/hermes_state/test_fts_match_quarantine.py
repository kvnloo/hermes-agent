"""Regression for #149585: FTS-only MATCH corruption must not quarantine state.db."""

import sqlite3
from contextlib import contextmanager

import pytest

from hermes_state import SessionDB, StateDbCorruptError
from hermes_state_health import STORAGE_CORRUPT, STORAGE_OK, reset_storage_state, storage_state


@pytest.mark.parametrize("canonical_ok", [True, False])
def test_bare_corrupt_trigram_match_checks_canonical_integrity(tmp_path, monkeypatch, canonical_ok):
    db = SessionDB(db_path=tmp_path / "state.db")
    try:
        if not db._fts_enabled or not db._trigram_available:
            pytest.skip("FTS5 trigram is unavailable in this SQLite runtime")
        db.create_session("s1", source="cli")
        db.append_message("s1", "user", "中文测试 is durable")
        # Force the real search route to use trigram, not the optional CJK extension.
        db._fts_cjk_available = False
        original_read_ctx = db._read_ctx
        failed_matches = []

        class TrigramErrorConnection:
            def __init__(self, conn):
                self.conn = conn

            def execute(self, sql, *args, **kwargs):
                if "messages_fts_trigram MATCH" in sql:
                    failed_matches.append(sql)
                    error = sqlite3.DatabaseError("database disk image is malformed")
                    error.sqlite_errorcode = sqlite3.SQLITE_CORRUPT
                    raise error
                if not canonical_ok and sql == "PRAGMA integrity_check('messages')":
                    return self.conn.execute("SELECT 'corrupt canonical table'")
                return self.conn.execute(sql, *args, **kwargs)

            def __getattr__(self, name):
                return getattr(self.conn, name)

        @contextmanager
        def corrupt_fts_read(*args, **kwargs):
            with original_read_ctx(*args, **kwargs) as conn:
                yield TrigramErrorConnection(conn)

        monkeypatch.setattr(db, "_read_ctx", corrupt_fts_read)
        if not canonical_ok:
            with pytest.raises(sqlite3.DatabaseError, match="malformed"):
                db.search_messages("中文测试")
            assert failed_matches
            assert storage_state(db.db_path) == STORAGE_CORRUPT
            assert db._fts_stale is False
            with pytest.raises(StateDbCorruptError):
                db.append_message("s1", "user", "must not write after structural damage")
            return

        matches = db.search_messages("中文测试")
        assert failed_matches, "must reach the real trigram MATCH"
        assert matches, "search should fall back to canonical LIKE"
        assert storage_state(db.db_path) == STORAGE_OK
        assert db._db_corrupt is False
        assert db._fts_stale is True

        db.append_message("s1", "user", "writes continue after FTS error")
        assert db._read_one("SELECT content FROM messages ORDER BY id DESC LIMIT 1")[0] == (
            "writes continue after FTS error"
        )
    finally:
        db.close()
        reset_storage_state(db.db_path)
