"""Checkpoint cleanup must match the completed discussion, not a newer thread message."""

from pathlib import Path

import pytest

from gateway import hosted_room_discussion as discussion
from gateway import hosted_rooms
from gateway.hosted_room_policy_checkpoint import HostedRoomPolicyCheckpoint

ROOM = "room-activity"
GATEWAY = "gateway-local"
PROFILES = ("research", "review")


@pytest.fixture
def room_checkpoint(tmp_path: Path):
    db = tmp_path / "state.db"
    room = hosted_rooms.create_room(
        db,
        room_id=ROOM,
        name="Discussion cleanup",
        members=[
            {"member_id": profile, "profile": profile, "handle": profile, "display_name": profile}
            for profile in PROFILES
        ],
        authority_gateway_id=GATEWAY,
        now=1,
    )
    return db, room, HostedRoomPolicyCheckpoint(db)


def append(db, event_id, thread_id, *, completed=None):
    return hosted_rooms.append_event(
        db,
        room_id=ROOM,
        event_id=event_id,
        kind="room.activity" if completed else "message.user",
        actor={"kind": "gateway" if completed else "user", "id": GATEWAY if completed else "user"},
        payload={"thread_id": thread_id, **(
            {"status": "settled", "reason_code": "silent_round", "discussion_event_id": completed}
            if completed else {"text": event_id}
        )},
        authority_gateway_id=GATEWAY,
        authority_epoch=1,
        now=2,
    )


def projected_plan(room, checkpoint, latest):
    snapshot = checkpoint.snapshot(room_id=ROOM, latest_seq=latest["seq"])
    return discussion.plan_next_task(
        room, snapshot.events, local_profiles=PROFILES, initial_watermarks=snapshot.watermarks,
    )


def test_late_activity_preserves_newer_same_thread_discussion(room_checkpoint):
    db, room, checkpoint = room_checkpoint
    old = append(db, "old-user", "thread-a")
    assert projected_plan(room, checkpoint, old).task.discussion_event_id == old["event_id"]

    newer = append(db, "new-user", "thread-a")
    late = append(db, "old-finished", "thread-a", completed=old["event_id"])
    full_events = hosted_rooms.read_events(db, room_id=ROOM)["events"]
    replay = discussion.plan_next_task(room, full_events, local_profiles=PROFILES)
    projected = projected_plan(room, checkpoint, late)

    assert replay.task is not None
    assert replay.task.discussion_event_id == newer["event_id"]
    assert projected.task is not None, projected
    assert projected.task == replay.task


def test_matching_activity_cleans_up_only_its_thread(room_checkpoint):
    db, room, checkpoint = room_checkpoint
    old = append(db, "old-user", "thread-a")
    other = append(db, "other-user", "thread-b")
    assert projected_plan(room, checkpoint, other).task.discussion_event_id == old["event_id"]

    done = append(db, "old-finished", "thread-a", completed=old["event_id"])
    remaining = projected_plan(room, checkpoint, done)
    assert remaining.task is not None
    assert remaining.task.discussion_event_id == other["event_id"]
    assert remaining.task.identity.thread_id == "thread-b"

    all_done = append(db, "other-finished", "thread-b", completed=other["event_id"])
    assert projected_plan(room, checkpoint, all_done).status == "idle"
