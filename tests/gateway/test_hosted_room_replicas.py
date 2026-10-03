"""Tests for gateway/hosted_room_replicas.py — replica ingest, promotion, and
stale-authority demotion for hosted Group Chat rooms."""

import json
import sqlite3

import pytest

import gateway.hosted_room_replicas as replicas
import gateway.hosted_rooms as rooms

USER = {"kind": "user", "id": "tek"}
MEMBERS = [{"kind": "bot", "id": "planner"}, {"kind": "bot", "id": "coder"}]

AUTH_A = "install:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
AUTH_B = "install:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def _authority_db(tmp_path, name="authority.db"):
    return tmp_path / name


def _replica_db(tmp_path, name="replica.db"):
    return tmp_path / name


def _gateway_event_bytes(db) -> int:
    with sqlite3.connect(db) as conn:
        return int(
            conn.execute(
                "SELECT COALESCE(SUM(event_bytes), 0) FROM hosted_rooms"
            ).fetchone()[0]
        )


def _room_event_bytes(db, room_id) -> int:
    with sqlite3.connect(db) as conn:
        return int(
            conn.execute(
                "SELECT event_bytes FROM hosted_rooms WHERE room_id=?", (room_id,)
            ).fetchone()[0]
        )


def _seed_room(db, *, gateway_id=AUTH_A, n_events=3, room_id="room-1"):
    rooms.create_room(
        db,
        room_id=room_id,
        name="Field Room",
        members=MEMBERS,
        authority_gateway_id=gateway_id,
    )
    for index in range(n_events):
        rooms.append_event(
            db,
            room_id=room_id,
            event_id=f"e{index}",
            kind="message.user",
            actor=USER,
            payload={"text": f"msg {index} 😀"},
            authority_gateway_id=gateway_id,
            authority_epoch=1,
        )
    return rooms.read_events(db, room_id=room_id, since_seq=0, limit=100)


def test_ingest_page_persists_events_and_lineage(tmp_path):
    page = _seed_room(_authority_db(tmp_path))
    rdb = _replica_db(tmp_path)
    result = replicas.ingest_page(
        rdb, room_id="room-1", room_name="Field Room", members=MEMBERS, page=page
    )
    assert result["ingested"] == 3
    assert result["stored_seq"] == 3
    assert result["caught_up"] is True
    state = replicas.replica_state(rdb, room_id="room-1")
    assert state["last_seq"] == 3
    assert state["authority"] == page["authority"]
    assert state["members"] == MEMBERS


def test_ingest_page_is_idempotent(tmp_path):
    page = _seed_room(_authority_db(tmp_path))
    rdb = _replica_db(tmp_path)
    replicas.ingest_page(
        rdb, room_id="room-1", room_name="Field Room", members=MEMBERS, page=page
    )
    again = replicas.ingest_page(
        rdb, room_id="room-1", room_name="Field Room", members=MEMBERS, page=page
    )
    assert again["ingested"] == 0
    assert again["stored_seq"] == 3


def test_ingest_rejects_sequence_gap(tmp_path):
    adb = _authority_db(tmp_path)
    _seed_room(adb, n_events=5)
    later = rooms.read_events(adb, room_id="room-1", since_seq=2, limit=100)
    rdb = _replica_db(tmp_path)
    with pytest.raises(replicas.ReplicaGapError):
        replicas.ingest_page(
            rdb,
            room_id="room-1",
            room_name="Field Room",
            members=MEMBERS,
            page=later,
        )


def test_ingest_rejects_epoch_regression(tmp_path):
    page = _seed_room(_authority_db(tmp_path))
    rdb = _replica_db(tmp_path)
    newer = json.loads(json.dumps(page))
    newer["authority"]["epoch"] = 3
    replicas.ingest_page(
        rdb, room_id="room-1", room_name="Field Room", members=MEMBERS, page=newer
    )
    stale = json.loads(json.dumps(page))
    stale["authority"]["epoch"] = 2
    with pytest.raises(replicas.ReplicaEpochRegressionError):
        replicas.ingest_page(
            rdb,
            room_id="room-1",
            room_name="Field Room",
            members=MEMBERS,
            page=stale,
        )


def test_ingest_requires_authority_stamp(tmp_path):
    page = _seed_room(_authority_db(tmp_path))
    page.pop("authority")
    with pytest.raises(replicas.ReplicaError):
        replicas.ingest_page(
            _replica_db(tmp_path),
            room_id="room-1",
            room_name="Field Room",
            members=MEMBERS,
            page=page,
        )


def test_promote_replica_continues_room_at_next_epoch(tmp_path, monkeypatch):
    page = _seed_room(_authority_db(tmp_path))
    rdb = _replica_db(tmp_path)
    replicas.ingest_page(
        rdb, room_id="room-1", room_name="Field Room", members=MEMBERS, page=page
    )
    monkeypatch.setattr(replicas, "local_authority_gateway_id", lambda: AUTH_B)

    promoted = replicas.promote_replica(rdb, room_id="room-1")
    assert promoted["authority_gateway_id"] == AUTH_B
    assert promoted["authority_epoch"] == 2
    assert promoted["previous_gateway_id"] == AUTH_A
    assert promoted["claim_seq"] == 4

    # The room is now locally authoritative with the full history + claim.
    replay = rooms.read_events(rdb, room_id="room-1", since_seq=0, limit=100)
    assert [e["seq"] for e in replay["events"]] == [1, 2, 3, 4]
    claim = replay["events"][-1]
    assert claim["kind"] == "authority.claimed"
    assert claim["payload"]["previous_gateway_id"] == AUTH_A
    assert claim["payload"]["authority_epoch"] == 2
    assert replay["authority"] == {"gateway_id": AUTH_B, "epoch": 2}

    # New work continues under the new epoch.
    rooms.append_event(
        rdb,
        room_id="room-1",
        event_id="post-takeover",
        kind="message.user",
        actor=USER,
        payload={"text": "continuing"},
        authority_gateway_id=AUTH_B,
        authority_epoch=2,
    )

    # The old authority's identity/epoch is fenced out.
    with pytest.raises(rooms.HostedRoomError):
        rooms.append_event(
            rdb,
            room_id="room-1",
            event_id="stale-write",
            kind="message.user",
            actor=USER,
            payload={"text": "stale"},
            authority_gateway_id=AUTH_A,
            authority_epoch=1,
        )

    # Replica bookkeeping is consumed by promotion.
    with pytest.raises(replicas.ReplicaError):
        replicas.replica_state(rdb, room_id="room-1")


def test_promote_refuses_when_room_exists_locally(tmp_path, monkeypatch):
    db = _authority_db(tmp_path)
    page = _seed_room(db)
    # Same DB also holds a replica row for the same id — conflict must win.
    replicas.ingest_page(
        db, room_id="room-1", room_name="Field Room", members=MEMBERS, page=page
    )
    monkeypatch.setattr(replicas, "local_authority_gateway_id", lambda: AUTH_B)
    with pytest.raises(rooms.RoomConflictError):
        replicas.promote_replica(db, room_id="room-1")


def test_promote_refuses_when_already_authority(tmp_path, monkeypatch):
    page = _seed_room(_authority_db(tmp_path))
    rdb = _replica_db(tmp_path)
    replicas.ingest_page(
        rdb, room_id="room-1", room_name="Field Room", members=MEMBERS, page=page
    )
    monkeypatch.setattr(replicas, "local_authority_gateway_id", lambda: AUTH_A)
    with pytest.raises(replicas.ReplicaError):
        replicas.promote_replica(rdb, room_id="room-1")


def test_demote_fences_stale_local_authority(tmp_path, monkeypatch):
    adb = _authority_db(tmp_path)
    _seed_room(adb)
    monkeypatch.setattr(replicas, "local_authority_gateway_id", lambda: AUTH_A)

    result = replicas.demote_room(
        adb, room_id="room-1", observed_gateway_id=AUTH_B, observed_epoch=2
    )
    assert result["idempotent"] is False
    assert result["authority_gateway_id"] == AUTH_B
    assert result["authority_epoch"] == 2

    replay = rooms.read_events(adb, room_id="room-1", since_seq=0, limit=100)
    lost = replay["events"][-1]
    assert lost["kind"] == "authority.lost"
    assert lost["payload"]["authority_gateway_id"] == AUTH_B
    assert replay["authority"] == {"gateway_id": AUTH_B, "epoch": 2}

    # Local sends at the stale identity/epoch are now rejected.
    with pytest.raises(rooms.HostedRoomError):
        rooms.append_event(
            adb,
            room_id="room-1",
            event_id="after-demote",
            kind="message.user",
            actor=USER,
            payload={"text": "stale"},
            authority_gateway_id=AUTH_A,
            authority_epoch=1,
        )

    # Repeating the same observation is idempotent.
    again = replicas.demote_room(
        adb, room_id="room-1", observed_gateway_id=AUTH_B, observed_epoch=2
    )
    assert again["idempotent"] is True


def test_demote_rejects_non_superseding_epoch(tmp_path, monkeypatch):
    adb = _authority_db(tmp_path)
    _seed_room(adb)
    monkeypatch.setattr(replicas, "local_authority_gateway_id", lambda: AUTH_A)
    with pytest.raises(replicas.ReplicaEpochRegressionError):
        replicas.demote_room(
            adb, room_id="room-1", observed_gateway_id=AUTH_B, observed_epoch=1
        )


def test_full_failover_round_trip(tmp_path, monkeypatch):
    """Authority A hosts, replica B follows, A dies, B promotes, A returns
    and is fenced + demoted; the room's history survives intact throughout."""
    adb = _authority_db(tmp_path)
    rdb = _replica_db(tmp_path)
    page = _seed_room(adb, n_events=4)
    replicas.ingest_page(
        rdb, room_id="room-1", room_name="Field Room", members=MEMBERS, page=page
    )

    # A "dies"; B takes over.
    monkeypatch.setattr(replicas, "local_authority_gateway_id", lambda: AUTH_B)
    promoted = replicas.promote_replica(rdb, room_id="room-1")
    rooms.append_event(
        rdb,
        room_id="room-1",
        event_id="b-work",
        kind="message.user",
        actor=USER,
        payload={"text": "work continues on B"},
        authority_gateway_id=AUTH_B,
        authority_epoch=promoted["authority_epoch"],
    )

    # A comes back, observes B's claim, and fences itself.
    monkeypatch.setattr(replicas, "local_authority_gateway_id", lambda: AUTH_A)
    replicas.demote_room(
        adb,
        room_id="room-1",
        observed_gateway_id=AUTH_B,
        observed_epoch=promoted["authority_epoch"],
    )
    with pytest.raises(rooms.HostedRoomError):
        rooms.append_event(
            adb,
            room_id="room-1",
            event_id="a-stale",
            kind="message.user",
            actor=USER,
            payload={"text": "split brain attempt"},
            authority_gateway_id=AUTH_A,
            authority_epoch=1,
        )

    # B's room holds the complete history: 4 original + claim + new work.
    replay = rooms.read_events(rdb, room_id="room-1", since_seq=0, limit=100)
    kinds = [e["kind"] for e in replay["events"]]
    assert kinds == ["message.user"] * 4 + ["authority.claimed", "message.user"]
    assert replay["authority"]["gateway_id"] == AUTH_B


def test_promote_refuses_when_gateway_event_budget_exceeded(tmp_path, monkeypatch):
    """Takeover must not push the gateway-total event_bytes budget over the
    limit and permanently block every later write (including disband_room)."""
    adb = _authority_db(tmp_path)
    page = _seed_room(adb, n_events=4)
    rdb = _replica_db(tmp_path)
    replicas.ingest_page(
        rdb, room_id="room-1", room_name="Field Room", members=MEMBERS, page=page
    )
    # The survivor gateway already hosts a near-budget room of its own, the
    # normal state of a long-running gateway that is the designated survivor.
    rooms.create_room(
        rdb,
        room_id="filler",
        name="Filler",
        members=MEMBERS,
        authority_gateway_id=AUTH_B,
        now=20,
    )
    for index in range(4):
        rooms.append_event(
            rdb,
            room_id="filler",
            event_id=f"filler-{index}",
            kind="message.user",
            actor=USER,
            payload={"text": f"filler message {index}"},
            authority_gateway_id=AUTH_B,
            authority_epoch=1,
        )
    monkeypatch.setattr(replicas, "local_authority_gateway_id", lambda: AUTH_B)

    gateway_total = _gateway_event_bytes(rdb)
    replica_bytes = replicas.replica_state(rdb, room_id="room-1")["event_bytes"]
    # A budget that fits the filler OR the replica, but not both: the promote's
    # projected room bytes (replica log + authority.claimed) push the gateway
    # total over by the claim-event cost, so promote must fail closed.
    monkeypatch.setattr(
        replicas, "MAX_GATEWAY_EVENT_BYTES", gateway_total + replica_bytes
    )

    with pytest.raises(rooms.HostedRoomError, match="storage is full"):
        replicas.promote_replica(rdb, room_id="room-1")

    # The failed promote left the gateway store and the replica untouched.
    assert _gateway_event_bytes(rdb) == gateway_total
    with sqlite3.connect(rdb) as conn:
        assert (
            conn.execute(
                "SELECT 1 FROM hosted_rooms WHERE room_id='room-1'"
            ).fetchone()
            is None
        )
        assert (
            conn.execute(
                "SELECT 1 FROM hosted_room_events WHERE room_id='room-1'"
            ).fetchone()
            is None
        )
    assert (
        replicas.replica_state(rdb, room_id="room-1")["event_bytes"] == replica_bytes
    )

    # Raising the budget so both fit lets the same promote succeed, proving
    # the refusal was capacity-driven rather than a structural conflict.
    monkeypatch.setattr(
        replicas, "MAX_GATEWAY_EVENT_BYTES", gateway_total + replica_bytes + 4096
    )
    promoted = replicas.promote_replica(rdb, room_id="room-1")
    assert promoted["authority_epoch"] == 2
    promoted_bytes = _room_event_bytes(rdb, "room-1")
    # The authority.claimed claim event is charged to the promoted room.
    assert promoted_bytes > replica_bytes
    assert _gateway_event_bytes(rdb) == _room_event_bytes(rdb, "filler") + promoted_bytes
    replay = rooms.read_events(rdb, room_id="room-1", since_seq=0, limit=100)
    assert replay["events"][-1]["kind"] == "authority.claimed"


def test_promote_refuses_when_replica_exceeds_room_event_budget(
    tmp_path, monkeypatch
):
    """The per-room event_bytes ceiling applies to the projected promoted room."""
    adb = _authority_db(tmp_path)
    page = _seed_room(adb, n_events=4)
    rdb = _replica_db(tmp_path)
    replicas.ingest_page(
        rdb, room_id="room-1", room_name="Field Room", members=MEMBERS, page=page
    )
    monkeypatch.setattr(replicas, "local_authority_gateway_id", lambda: AUTH_B)

    replica_bytes = replicas.replica_state(rdb, room_id="room-1")["event_bytes"]
    # Per-room ceiling just below the projected room bytes (replica + claim),
    # but with a generous gateway total so only the per-room gate fires.
    monkeypatch.setattr(replicas, "MAX_ROOM_EVENT_BYTES", replica_bytes)
    monkeypatch.setattr(replicas, "MAX_GATEWAY_EVENT_BYTES", 256 * 1024 * 1024)

    with pytest.raises(rooms.HostedRoomError, match="storage limit"):
        replicas.promote_replica(rdb, room_id="room-1")

    assert _gateway_event_bytes(rdb) == 0
    with sqlite3.connect(rdb) as conn:
        assert (
            conn.execute(
                "SELECT 1 FROM hosted_rooms WHERE room_id='room-1'"
            ).fetchone()
            is None
        )
    assert (
        replicas.replica_state(rdb, room_id="room-1")["event_bytes"] == replica_bytes
    )


def test_promote_reclaims_disbanded_room_budget_then_succeeds(
    tmp_path, monkeypatch
):
    """A promote over budget prunes disbanded rooms first, mirroring
    _assert_event_capacity, and succeeds once reclaim frees enough space."""
    adb = _authority_db(tmp_path)
    page = _seed_room(adb, n_events=4)
    rdb = _replica_db(tmp_path)
    replicas.ingest_page(
        rdb, room_id="room-1", room_name="Field Room", members=MEMBERS, page=page
    )
    # A leftover disbanded room still counts against the gateway total until
    # pruned; the promote's prune-then-check must reclaim it.
    rooms.create_room(
        rdb,
        room_id="filler",
        name="Filler",
        members=MEMBERS,
        authority_gateway_id=AUTH_B,
        now=20,
    )
    for index in range(4):
        rooms.append_event(
            rdb,
            room_id="filler",
            event_id=f"filler-{index}",
            kind="message.user",
            actor=USER,
            payload={"text": f"filler message {index}"},
            authority_gateway_id=AUTH_B,
            authority_epoch=1,
        )
    rooms.disband_room(
        rdb, room_id="filler", expected_gateway_id=AUTH_B, expected_epoch=1, now=30
    )
    monkeypatch.setattr(replicas, "local_authority_gateway_id", lambda: AUTH_B)

    gateway_total = _gateway_event_bytes(rdb)
    replica_bytes = replicas.replica_state(rdb, room_id="room-1")["event_bytes"]
    # Same budget that fails for an *active* filler now succeeds because the
    # disbanded filler is pruned to make room for the replica.
    monkeypatch.setattr(
        replicas, "MAX_GATEWAY_EVENT_BYTES", gateway_total + replica_bytes
    )

    promoted = replicas.promote_replica(rdb, room_id="room-1")
    assert promoted["authority_epoch"] == 2
    assert promoted["authority_gateway_id"] == AUTH_B

    # The disbanded filler was reclaimed; the promoted room took its place.
    with sqlite3.connect(rdb) as conn:
        assert (
            conn.execute(
                "SELECT 1 FROM hosted_rooms WHERE room_id='room-1'"
            ).fetchone()
            is not None
        )
        assert (
            conn.execute(
                "SELECT 1 FROM hosted_rooms WHERE room_id='filler'"
            ).fetchone()
            is None
        )
        assert (
            conn.execute(
                "SELECT 1 FROM hosted_room_retired_ids WHERE room_id='filler'"
            ).fetchone()
            is not None
        )


def test_demote_records_authority_lost_event_bytes(tmp_path, monkeypatch):
    """demote_room must charge the authority.lost control event to the room's
    event_bytes so the gateway-total accounting stays accurate."""
    adb = _authority_db(tmp_path)
    _seed_room(adb, n_events=3)
    monkeypatch.setattr(replicas, "local_authority_gateway_id", lambda: AUTH_A)

    before = _room_event_bytes(adb, "room-1")
    replicas.demote_room(
        adb, room_id="room-1", observed_gateway_id=AUTH_B, observed_epoch=2
    )
    after = _room_event_bytes(adb, "room-1")

    with sqlite3.connect(adb) as conn:
        row = conn.execute(
            "SELECT event_id, kind, actor_json, payload_json "
            "FROM hosted_room_events "
            "WHERE room_id='room-1' AND kind='authority.lost'"
        ).fetchone()
    assert row is not None
    lost_bytes = sum(len(col.encode("utf-8")) for col in row)
    assert after == before + lost_bytes
    assert _gateway_event_bytes(adb) == after


def test_demote_refuses_when_gateway_event_budget_exceeded(
    tmp_path, monkeypatch
):
    """demote_room gates its authority.lost control event through the same
    _assert_event_capacity gate every other control emitter uses."""
    adb = _authority_db(tmp_path)
    _seed_room(adb, n_events=3)
    monkeypatch.setattr(replicas, "local_authority_gateway_id", lambda: AUTH_A)
    # Zero gateway budget and no control-event reserve: even the small
    # authority.lost control event must be rejected at the gate.
    monkeypatch.setattr(rooms, "MAX_GATEWAY_EVENT_BYTES", 0)
    monkeypatch.setattr(rooms, "CONTROL_EVENT_BYTE_RESERVE", 0)

    with pytest.raises(rooms.HostedRoomError, match="storage is full"):
        replicas.demote_room(
            adb, room_id="room-1", observed_gateway_id=AUTH_B, observed_epoch=2
        )

    # Nothing was appended and authority is unchanged.
    with sqlite3.connect(adb) as conn:
        lost = conn.execute(
            "SELECT COUNT(*) FROM hosted_room_events "
            "WHERE room_id='room-1' AND kind='authority.lost'"
        ).fetchone()[0]
        row = conn.execute(
            "SELECT authority_gateway_id, authority_epoch, event_bytes "
            "FROM hosted_rooms WHERE room_id='room-1'"
        ).fetchone()
    assert lost == 0
    assert row[0] == AUTH_A
    assert row[1] == 1

