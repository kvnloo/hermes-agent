"""Differential tests of hosted-room callers against the fresh-open SQLite contract."""
from __future__ import annotations

import json
import os
import random
import sqlite3
from contextlib import closing

import pytest

from gateway import hosted_room_connection_reuse as reuse
from gateway import hosted_room_driver as driver
from gateway import hosted_rooms as rooms
from gateway.hosted_room_policy_checkpoint import HostedRoomPolicyCheckpoint
from hermes_cli import sqlite_util

_USER = {"kind": "user", "id": "user-1", "display_name": "User"}


@pytest.fixture(autouse=True)
def _clean_pools():
    reuse.close_all()
    yield
    reuse.close_all()


def _inputs() -> list[str]:
    seeds = [
        "", "same", "same", "100%literal", "under_score", "back\\slash",
        "jalapeño", "路径/資料", "emoji-🧭",
        json.dumps({"path": "C:\\path\\with_100%\\file"}, ensure_ascii=True),
    ]
    rng = random.Random(1107)
    return seeds + [rng.choice(seeds) + str(rng.randrange(7)) for _ in range(37)]


def _callers(path, values):
    created = rooms.create_room(
        path, room_id="room-1", name="Storage test",
        members=[{"profile": "ops", "handle": "ops"}],
        authority_gateway_id="gateway-a", now=10)
    appended = []
    for index, value in enumerate(values):
        kwargs = dict(
            room_id="room-1", event_id=f"event-{index}", kind="message.user",
            actor=_USER, payload={"thread_id": "thread-1", "text": value},
            authority_gateway_id="gateway-a", authority_epoch=1, now=index + 11)
        appended.append(rooms.append_event(path, **kwargs))
        if index % 11 == 0:
            appended.append(rooms.append_event(path, **kwargs))
    checkpoint = HostedRoomPolicyCheckpoint(path)
    return {
        "created": created,
        "appended": appended,
        "events": rooms.read_events(path, room_id="room-1", limit=100),
        "state": rooms.room_state(path, room_id="room-1"),
        "links": rooms.list_room_link_records(path),
        "tasks": driver.list_tasks(path, room_id="room-1"),
        "publication": checkpoint.publication_exists(
            room_id="room-1", task_id="absent", status="settled", execution_generation=1),
    }


def test_real_callers_match_original_open_db(tmp_path, monkeypatch):
    values = _inputs()
    with monkeypatch.context() as patch:
        patch.setattr(reuse, "open_reused", sqlite_util.open_db)
        old = _callers(tmp_path / "old.db", values)
    new = _callers(tmp_path / "new.db", values)
    assert new == old


def test_reuse_restores_timeout_and_rolls_back_uncommitted_work(tmp_path, monkeypatch):
    path = tmp_path / "state.db"
    rooms.create_room(
        path, room_id="room-1", name="Storage test", members=[],
        authority_gateway_id="gateway-a", now=10)
    with closing(rooms._connect(path)) as conn:
        conn.execute("CREATE TABLE pool_probe(value TEXT)")
        conn.commit()
        conn.execute("INSERT INTO pool_probe(value) VALUES ('uncommitted')")
        conn.execute("PRAGMA busy_timeout=2")
    original = sqlite_util.open_db
    opens = 0

    def counted(*args, **kwargs):
        nonlocal opens
        opens += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(sqlite_util, "open_db", counted)
    for _ in range(12):
        with closing(rooms._connect(path)) as conn:
            assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 10_000
            assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert conn.execute("SELECT COUNT(*) FROM pool_probe").fetchone()[0] == 0
    assert opens == 0


@pytest.mark.platforms("posix")
def test_inode_replacement_reopens_database(tmp_path):
    path, replacement = tmp_path / "state.db", tmp_path / "replacement.db"
    rooms.create_room(
        path, room_id="room-1", name="Before", members=[],
        authority_gateway_id="gateway-a", now=10)
    with closing(sqlite3.connect(path)) as source, closing(sqlite3.connect(replacement)) as target:
        source.backup(target)
    with closing(sqlite3.connect(replacement)) as conn:
        with conn:
            conn.execute("UPDATE hosted_rooms SET name='After' WHERE room_id='room-1'")
    assert path.stat().st_ino != replacement.stat().st_ino
    os.replace(replacement, path)
    with closing(rooms._connect(path)) as conn:
        assert conn.execute("SELECT name FROM hosted_rooms WHERE room_id='room-1'").fetchone()[0] == "After"


@pytest.mark.platforms("posix")
def test_fork_child_cannot_borrow_parent_connection(tmp_path):
    path = tmp_path / "state.db"
    rooms.create_room(
        path, room_id="room-1", name="Before", members=[],
        authority_gateway_id="gateway-a", now=10)
    pid = os.fork()
    if pid == 0:
        try:
            with closing(rooms._connect(path)) as conn:
                assert conn.execute("SELECT COUNT(*) FROM hosted_rooms").fetchone()[0] == 1
        except BaseException:
            os._exit(1)
        os._exit(0)
    _, status = os.waitpid(pid, 0)
    assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0


def test_wal_fallback_failure_does_not_cache_connection(tmp_path, monkeypatch):
    import hermes_state_wal

    original = hermes_state_wal.apply_wal_with_fallback
    attempts = 0

    def fail_once(conn, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise sqlite3.OperationalError("configured journal mode refused")
        return original(conn, **kwargs)

    monkeypatch.setattr(hermes_state_wal, "apply_wal_with_fallback", fail_once)
    path = tmp_path / "fresh.db"
    with pytest.raises(sqlite3.OperationalError, match="configured journal mode refused"):
        rooms._connect(path)
    with closing(rooms._connect(path)) as conn:
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 10_000
    assert attempts >= 2

def test_reused_connection_still_checks_wal_fallback(tmp_path, monkeypatch):
    import hermes_state_wal

    path = tmp_path / "state.db"
    rooms.create_room(
        path, room_id="room-1", name="Before", members=[],
        authority_gateway_id="gateway-a", now=10)

    def journal_changed(_conn, **_kwargs):
        raise sqlite3.OperationalError("journal mode recheck failed")

    with monkeypatch.context() as patch:
        patch.setattr(hermes_state_wal, "apply_wal_with_fallback", journal_changed)
        with pytest.raises(sqlite3.OperationalError, match="journal mode recheck failed"):
            rooms._connect(path)

    # A failed recheck discards the idle handle; the next attempt must work.
    with closing(rooms._connect(path)) as conn:
        assert conn.execute("SELECT name FROM hosted_rooms WHERE room_id='room-1'").fetchone()[0] == "Before"
