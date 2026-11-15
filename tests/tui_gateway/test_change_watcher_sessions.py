from __future__ import annotations

import sqlite3
import time

from tui_gateway import server


def _seed_store(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            last_activity_at REAL,
            message_count INTEGER,
            archived INTEGER DEFAULT 0,
            pinned INTEGER DEFAULT 0
        );
        CREATE TABLE gateway_heartbeats (
            backend_id TEXT PRIMARY KEY,
            last_heartbeat REAL
        );
        INSERT INTO sessions(id, title, last_activity_at, message_count)
        VALUES ('session-1', 'Original', 100, 1);
        INSERT INTO gateway_heartbeats(backend_id, last_heartbeat)
        VALUES ('backend-1', 100);
        """
    )
    conn.commit()
    conn.close()


def test_sessions_signature_ignores_gateway_heartbeat_only_writes(tmp_path, monkeypatch):
    db_path = tmp_path / "state.db"
    _seed_store(db_path)
    monkeypatch.setattr(server, "_watcher_home", lambda: tmp_path)
    monkeypatch.setattr(server, "_served_profile_homes", [])

    before = server._sessions_sig()
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE gateway_heartbeats SET last_heartbeat = 200")
    conn.commit()
    conn.close()

    assert server._sessions_sig() == before


def test_sessions_signature_changes_for_session_metadata_updates(tmp_path, monkeypatch):
    db_path = tmp_path / "state.db"
    _seed_store(db_path)
    monkeypatch.setattr(server, "_watcher_home", lambda: tmp_path)
    monkeypatch.setattr(server, "_served_profile_homes", [])

    before = server._sessions_sig()
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE sessions SET title = 'Renamed' WHERE id = 'session-1'")
    conn.commit()
    conn.close()

    assert server._sessions_sig() != before


def test_sessions_signature_confirms_same_tick_commit_when_mtime_settles(tmp_path, monkeypatch):
    """A racy mtime is scanned once, then confirmed when the real 2 s window closes.

    A same-tick commit may be delayed to that confirmation, matching the 2 s
    sessions.changed broadcast floor rather than scanning every watcher tick.
    """
    db_path = tmp_path / "state.db"
    _seed_store(db_path)
    monkeypatch.setattr(server, "_watcher_home", lambda: tmp_path)
    monkeypatch.setattr(server, "_served_profile_homes", [])
    monkeypatch.setattr(server, "_sessions_db_sig_cache", {})
    frozen_mtime = time.time_ns()
    monkeypatch.setattr(server, "_newest_mtime_ns", lambda _paths: frozen_mtime)
    racy = [True]
    monkeypatch.setattr("utils.mtime_is_racy", lambda _stamp: racy[0])
    scans = []
    read = server._session_rows_sig

    def count_scan(conn, stamp):
        scans.append(1)
        return read(conn, stamp)

    monkeypatch.setattr(server, "_session_rows_sig", count_scan)
    before = server._sessions_sig()
    assert server._sessions_sig() == before
    assert len(scans) == 1

    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE sessions SET title = 'Renamed' WHERE id = 'session-1'")
    conn.commit()
    conn.close()
    assert server._sessions_sig() == before  # same tick: defer until mtime settles
    assert len(scans) == 1

    racy[0] = False  # the real RACY_MTIME_WINDOW_NS elapsed, without lowering it
    changed = server._sessions_sig()
    assert changed != before
    assert len(scans) == 2
    assert server._sessions_sig() == changed
    assert len(scans) == 2


def test_sessions_signature_avoids_text_pk_index_scan(tmp_path):
    """The production TEXT PRIMARY KEY must not cause one table seek per session row."""
    db_path = tmp_path / "state.db"
    _seed_store(db_path)
    conn = sqlite3.connect(db_path)
    try:
        statements = []
        conn.set_trace_callback(statements.append)
        server._session_rows_sig(conn, db_path.stat().st_mtime_ns)
        conn.set_trace_callback(None)
        selects = [sql for sql in statements if sql.lstrip().upper().startswith("SELECT ")]
        assert len(selects) == 1
        plan = [row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + selects[0])]
        assert plan
        assert not any("USING INDEX sqlite_autoindex_sessions" in step for step in plan)
    finally:
        conn.close()
