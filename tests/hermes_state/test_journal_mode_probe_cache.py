"""Differential and safety coverage for the in-process journal-mode probe cache.

DSA1107-T3-OPEN-DB-PRAGMA: the original read-only SQLite probe is preserved as
_read_journal_mode_uncached so new/old run against identical generated inputs.
"""

from __future__ import annotations

import json
import os
import random
import sqlite3
from contextlib import closing

import pytest

import hermes_state_wal as wal
from hermes_cli.sqlite_util import open_db


@pytest.fixture(autouse=True)
def clear_journal_mode_cache():
    with wal._journal_mode_cache_lock:
        wal._journal_mode_cache.clear()
    yield
    with wal._journal_mode_cache_lock:
        wal._journal_mode_cache.clear()


@pytest.mark.parametrize("mode", ["delete", "wal"])
def test_generated_old_new_journal_modes_match(tmp_path, mode):
    """Empty, duplicates, Unicode, SQL LIKE characters and JSON-escaped paths."""
    random_gen = random.Random(1107)
    labels = [
        "", "same", "same", "café-雪", "like%_wildcards",
        r"back\slash", json.loads(json.dumps("json\\escaped-雪%_")),
    ]
    for _ in range(28):
        name = labels[random_gen.randrange(len(labels))]
        path = tmp_path / (name + ".db" if name else "zero-page.db")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with closing(sqlite3.connect(path)) as seed:
                if name:
                    seed.execute(f"PRAGMA journal_mode={mode}").fetchone()
                    seed.execute("CREATE TABLE entries (value TEXT)")
                    seed.execute("INSERT INTO entries VALUES (?)", (name,))
                    seed.commit()
        with closing(sqlite3.connect(path)) as conn:
            expected = wal._read_journal_mode_uncached(conn)
            actual = wal._on_disk_journal_mode(conn)
            assert actual == expected
            assert wal._on_disk_journal_mode(conn) == expected


@pytest.mark.platforms("posix")
def test_verified_wal_is_reused_across_short_lived_connections(tmp_path, monkeypatch):
    path = tmp_path / "hot%_雪.db"
    with closing(sqlite3.connect(path)) as seed:
        assert seed.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        seed.execute("CREATE TABLE entries (value TEXT)")
        seed.commit()
        original = wal._read_journal_mode_uncached
        calls = []

        def counted(conn):
            calls.append(1)
            return original(conn)

        monkeypatch.setattr(wal, "_read_journal_mode_uncached", counted)
        monkeypatch.setattr(wal, "_JOURNAL_MODE_CACHE_TTL_SECONDS", 60.0)
        for _ in range(6):
            with closing(sqlite3.connect(path)) as short_lived:
                assert wal._on_disk_journal_mode(short_lived) == "wal"
        assert len(calls) == 1


@pytest.mark.platforms("posix")
def test_replaced_database_inode_invalidates_wal_cache(tmp_path):
    path = tmp_path / "replaced.db"
    replacement = tmp_path / "other.db"
    with closing(sqlite3.connect(path)) as seed:
        assert seed.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        seed.execute("CREATE TABLE old_data (x INTEGER)")
        seed.commit()
    with closing(sqlite3.connect(path)) as conn:
        assert wal._on_disk_journal_mode(conn) == "wal"
    before = path.stat().st_ino

    with closing(sqlite3.connect(replacement)) as other:
        other.execute("CREATE TABLE new_data (x INTEGER)")
        other.commit()
        assert other.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    replacement_inode = replacement.stat().st_ino
    assert before != replacement_inode
    os.replace(replacement, path)
    assert path.stat().st_ino == replacement_inode

    with closing(sqlite3.connect(path)) as conn:
        assert wal._on_disk_journal_mode(conn) == "delete"
        assert wal._on_disk_journal_mode(conn) == wal._read_journal_mode_uncached(conn)
    assert all(entry[1] == "wal" for entry in wal._journal_mode_cache.values())


@pytest.mark.parametrize("vulnerable", [False, True])
def test_fresh_db_open_db_matches_uncached(tmp_path, monkeypatch, vulnerable):
    monkeypatch.setattr(wal, "is_sqlite_wal_reset_vulnerable", lambda: vulnerable)
    real_key = wal._journal_mode_file_key

    def setup(conn):
        conn.execute("CREATE TABLE items (name TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO items VALUES (?)", ("café%_\\json",))
        conn.commit()

    results = []
    for cached in (False, True):
        path = tmp_path / ("cached.db" if cached else "reference.db")
        monkeypatch.setattr(wal, "_journal_mode_file_key", real_key if cached else lambda _conn: None)
        with closing(open_db(path, db_label="DSA open-db test", initialize=setup)) as conn:
            results.append((
                conn.execute("PRAGMA journal_mode").fetchone()[0],
                [tuple(row) for row in conn.execute("SELECT name FROM items")],
            ))
    assert results[0] == results[1]


def test_external_mode_change_does_not_leave_stale_wal(tmp_path):
    path = tmp_path / "mode-change.db"
    with closing(sqlite3.connect(path)) as seed:
        assert seed.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        seed.execute("CREATE TABLE entries (v TEXT)")
        seed.commit()
    with closing(sqlite3.connect(path)) as conn:
        assert wal._on_disk_journal_mode(conn) == "wal"
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"
    with closing(sqlite3.connect(path)) as conn:
        assert wal._on_disk_journal_mode(conn) == "delete"
        assert wal._on_disk_journal_mode(conn) == wal._read_journal_mode_uncached(conn)


@pytest.mark.parametrize("failures,expected_attempts", [(2, 3), (4, 4)])
def test_uncached_transient_disk_io_retries_and_unknown_fail_closed(
    tmp_path, monkeypatch, failures, expected_attempts
):
    monkeypatch.setattr(wal.time, "sleep", lambda _seconds: None)

    class FlakyConnection(sqlite3.Connection):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.probes = 0

        def execute(self, sql, *args, **kwargs):
            if str(sql).strip().lower() == "pragma journal_mode":
                self.probes += 1
                if self.probes <= failures:
                    raise sqlite3.OperationalError("disk I/O error")
            return super().execute(sql, *args, **kwargs)

    outcomes = []
    for label, probe in (("old", wal._read_journal_mode_uncached),
                         ("new", wal._on_disk_journal_mode)):
        with closing(sqlite3.connect(tmp_path / (label + ".db"), factory=FlakyConnection)) as conn:
            outcomes.append(probe(conn))
            assert conn.probes == expected_attempts
    assert outcomes == (["delete", "delete"] if failures == 2 else [None, None])
