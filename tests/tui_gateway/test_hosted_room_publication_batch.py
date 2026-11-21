"""Published hosted-room outcomes are read once per poll, not once per old task."""

import sqlite3
import threading
from types import SimpleNamespace

from gateway import hosted_rooms
from tui_gateway.hosted_room_service import HostedRoomService


def test_terminal_publication_snapshot_preserves_receipts_without_per_task_connections(
    tmp_path, monkeypatch
):
    db = tmp_path / "state.db"
    members = [
        {"member_id": name, "profile": name, "handle": name}
        for name in ("default", "reviewer")
    ]
    for room_id in ("room", "other"):
        hosted_rooms.create_room(
            db, room_id=room_id, name=room_id, authority_gateway_id="home", members=members
        )
    server = SimpleNamespace(_methods={}, _sessions={}, _sessions_lock=threading.Lock())
    service = HostedRoomService(server, db_path=db)
    service.local_profiles = lambda: ("default", "reviewer")
    receipts = [
        ("room", "deferred", "turn.deferred", 2, 1),
        ("room", "settled", "turn.settled", 9, 2),
        ("room", "failed", "turn.failed", 0, 3),
        ("room", "cancelled", "turn.cancelled", 0, 4),
        ("other", "foreign", "turn.settled", 0, 1),
    ]
    with sqlite3.connect(db) as conn:
        conn.executemany(
            """INSERT INTO hosted_room_policy_publications
               (room_id, task_id, kind, execution_generation, seq)
               VALUES (?, ?, ?, ?, ?)""",
            receipts,
        )

    published = service.policy_checkpoint.published_outcomes(room_id="room")
    assert published == {(task_id, kind, generation) for room_id, task_id, kind, generation, _
                         in receipts if room_id == "room"}
    completed = {task_id for task_id, kind, _ in published
                 if kind in ("turn.settled", "turn.failed", "turn.cancelled")}
    checks = [
        ("deferred", "deferred", 2, True),
        ("deferred", "deferred", 3, False),
        ("settled", "failed", 50, True),
        ("failed", "settled", 50, True),
        ("cancelled", "cancelled", 50, True),
        ("foreign", "settled", 0, False),
    ]
    for task_id, status, generation, expected in checks:
        old_lookup = service.policy_checkpoint.publication_exists(
            room_id="room", task_id=task_id, status=status, execution_generation=generation
        )
        batched_lookup = (
            (task_id, "turn.deferred", generation) in published
            if status == "deferred" else task_id in completed
        )
        assert old_lookup is expected
        assert batched_lookup is old_lookup

    tasks = [
        {"identity": SimpleNamespace(task_id=task_id), "status": status,
         "execution_generation": generation}
        for task_id, status, generation in [
            ("deferred", "deferred", 2),
            ("settled", "settled", 43),
            ("failed", "failed", 21),
            ("cancelled", "cancelled", 55),
        ]
    ]
    monkeypatch.setattr(service, "_list_tasks", lambda room_id, statuses: iter(tasks))
    connects = []
    real_connect = service.policy_checkpoint._connect

    def counted_connect():
        connects.append(1)
        return real_connect()

    monkeypatch.setattr(service.policy_checkpoint, "_connect", counted_connect)
    assert service._publish_terminal_tasks(service._room("room")) is False
    assert len(connects) == 1
