import concurrent.futures
import hashlib
import json
import multiprocessing
import random
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import yaml
import pytest

from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest
from hermes_state import SessionDB
from gateway.config import Platform
from gateway.notification_owner import GatewayNotificationOwnerService
from gateway.session import SessionSource
from session_notifications import (
    MIGRATION_MARKER, NotificationOutcome, SessionNotificationStore, canonicalize_metadata,
)


SESSION_KEY = "agent:main:telegram:dm:42"
KEY = "opaque-notification-key-0001"
METADATA = {
    "event": "taildrop_received",
    "sender": "captain",
    "device": "groot",
    "sha256": "a" * 64,
    "bytes": 42,
    "generation": 7,
    "status_label": "received",
}


def _db(tmp_path: Path) -> tuple[SessionDB, SessionNotificationStore]:
    path = tmp_path / "state.db"
    db = SessionDB(path)
    db.create_session(
        "session-1", source="telegram", session_key=SESSION_KEY, profile_name="default"
    )
    return db, SessionNotificationStore(path)


def _append(store: SessionNotificationStore, **overrides):
    params = dict(
        idempotency_key=KEY,
        profile_name="default",
        plugin_id="taildrop",
        session_key=SESSION_KEY,
        destination="captain:telegram:42",
        generation=7,
        metadata=METADATA,
    )
    params.update(overrides)
    return store.append_once(**params)


def _process_append(path: str, queue) -> None:
    queue.put(_append(SessionNotificationStore(Path(path), timeout=10)).outcome.value)


def test_atomic_accept_replay_conflict_and_transcript_is_untouched(tmp_path):
    db, store = _db(tmp_path)
    db.append_message("session-1", "user", "ordinary in-flight user row")
    before = db.get_messages("session-1")

    first = _append(store)
    replay = _append(store)
    conflict = _append(store, destination="captain:telegram:other")

    assert first.outcome is NotificationOutcome.ACCEPTED
    assert replay.outcome is NotificationOutcome.ALREADY_ACCEPTED
    assert replay.notification_id == first.notification_id
    assert conflict.outcome is NotificationOutcome.CONFLICT
    after = db.get_messages("session-1")
    assert [(m["id"], m["role"], m["content"]) for m in after] == [
        (m["id"], m["role"], m["content"]) for m in before
    ]
    db.close()


def test_concurrent_accept_has_one_winner(tmp_path):
    db, store = _db(tmp_path)
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda _: _append(store).outcome, range(40)))
    assert results.count(NotificationOutcome.ACCEPTED) == 1
    assert results.count(NotificationOutcome.ALREADY_ACCEPTED) == 39
    db.close()


def test_multiprocess_accept_has_one_winner(tmp_path):
    db, store = _db(tmp_path)
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    processes = [context.Process(target=_process_append, args=(str(store.db_path), queue))
                 for _ in range(8)]
    for process in processes:
        process.start()
    results = [queue.get(timeout=20) for _ in processes]
    for process in processes:
        process.join(20)
        assert process.exitcode == 0
    assert results.count(NotificationOutcome.ACCEPTED.value) == 1
    assert results.count(NotificationOutcome.ALREADY_ACCEPTED.value) == 7
    db.close()


def test_metadata_is_allowlisted_and_content_paths_commands_secrets_are_rejected(tmp_path):
    db, store = _db(tmp_path)
    for field in ("content", "path", "command", "secret", "token", "unknown"):
        result = _append(store, idempotency_key=f"{KEY}-{field}", metadata={**METADATA, field: "x"})
        assert result.outcome is NotificationOutcome.REJECTED
    assert _append(store, metadata={**METADATA, "sha256": "BAD"}).outcome is NotificationOutcome.REJECTED
    db.close()


def test_owner_scope_generation_ack_and_receipt_backed_retention(tmp_path):
    now = [1000.0]
    db, _ = _db(tmp_path)
    store = SessionNotificationStore(db.db_path, clock=lambda: now[0])
    receipt = _append(store)
    live = {"allowed": True, "generation": 7}
    config = SimpleNamespace(platforms={
        Platform.TELEGRAM: SimpleNamespace(extra={"allow_admin_from": ["42"]})
    })
    service = GatewayNotificationOwnerService(
        db_path=db.db_path, gateway_config=config,
        authorize=lambda source: live["allowed"] and source.user_id == "42",
        session_key_for_source=lambda source: SESSION_KEY,
        current_generation=lambda session_key: live["generation"],
    )
    owner = SessionSource(Platform.TELEGRAM, "42", user_id="42")
    assert len(service.list_pending(owner)) == 1
    assert service.list_pending(SessionSource(Platform.DISCORD, "42", user_id="42")) is None
    assert service.list_pending(SessionSource(Platform.TELEGRAM, "42", user_id="99")) is None
    live["allowed"] = False
    assert not service.acknowledge(owner, receipt.notification_id)
    live["allowed"] = True
    live["generation"] = 6
    assert service.list_pending(owner) == []
    assert service.fetch(owner, receipt.notification_id) is None
    assert not service.acknowledge(owner, receipt.notification_id)
    live["generation"] = 7
    assert service.acknowledge(owner, receipt.notification_id)
    assert not service.acknowledge(owner, receipt.notification_id)
    assert service.list_pending(owner) == []
    assert store.compact_acknowledged()[1] == 0
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM session_notification_owner_audit WHERE notification_id=?",
            (receipt.notification_id,),
        ).fetchone()[0] == 1
    db.close()


def test_sqlite_busy_is_retryable_and_restart_persists(tmp_path):
    db, store = _db(tmp_path)
    lock = sqlite3.connect(db.db_path)
    lock.execute("BEGIN IMMEDIATE")
    busy_store = SessionNotificationStore(db.db_path, timeout=0.01)
    assert _append(busy_store).outcome is NotificationOutcome.RETRYABLE_FAILURE
    lock.rollback()
    lock.close()
    accepted = _append(store)
    restarted = SessionNotificationStore(db.db_path)
    assert _append(restarted).outcome is NotificationOutcome.ALREADY_ACCEPTED
    assert restarted._fetch(
        accepted.notification_id, profile_name="default",
        session_key=SESSION_KEY, generation=7,
    )
    db.close()


def test_ambiguous_legacy_rows_quarantine_without_touching_transcript(tmp_path):
    db, store = _db(tmp_path)
    db.append_message("session-1", "user", "preserved real transcript")
    before = db.get_messages("session-1")
    with sqlite3.connect(db.db_path) as conn:
        conn.executescript("""
            CREATE TABLE gateway_inbox(inbox_id TEXT PRIMARY KEY,idempotency_key TEXT);
            CREATE TABLE gateway_turns(
                turn_id TEXT PRIMARY KEY,inbox_id TEXT,source_id TEXT,session_key TEXT,
                session_id TEXT,generation INTEGER,created_at REAL
            );
            INSERT INTO gateway_inbox VALUES('inbox-1','legacy-global-key');
            INSERT INTO gateway_turns VALUES(
                'turn-1','inbox-1','taildrop','agent:main:telegram:dm:42',
                'session-1',7,100.0
            );
        """)
    assert store.migrate_legacy_gateway_notifications() == 1
    assert store.migrate_legacy_gateway_notifications() == 0
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute(
            "SELECT status FROM session_notifications WHERE notification_id='turn-1'"
        ).fetchone()[0] == "quarantined"
        assert conn.execute("SELECT COUNT(*) FROM gateway_turns").fetchone()[0] == 1
    assert [(m["id"], m["role"], m["content"]) for m in db.get_messages("session-1")] == [
        (m["id"], m["role"], m["content"]) for m in before
    ]
    db.close()


@pytest.mark.parametrize("row_count", [2, 10, 100])
@pytest.mark.parametrize("vary_source", [False, True])
def test_shared_binding_and_metadata_are_not_migration_collisions(
    tmp_path, row_count, vary_source,
):
    db, store = _db(tmp_path)
    order = list(range(row_count))
    random.Random(row_count * 17 + int(vary_source)).shuffle(order)
    with sqlite3.connect(db.db_path) as conn:
        conn.executescript("""
            CREATE TABLE gateway_inbox(inbox_id TEXT PRIMARY KEY,idempotency_key TEXT);
            CREATE TABLE gateway_turns(turn_id TEXT PRIMARY KEY,inbox_id TEXT,source_id TEXT,
                session_key TEXT,session_id TEXT,generation INTEGER,created_at REAL);
        """)
        for value in order:
            conn.execute("INSERT INTO gateway_inbox VALUES(?,?)", (f"inbox-{value}", f"key-{value}"))
            conn.execute(
                "INSERT INTO gateway_turns VALUES(?,?,?,?,?,?,?)",
                (f"turn-{value}", f"inbox-{value}",
                 f"taildrop-{value}" if vary_source else "taildrop",
                 SESSION_KEY, "session-1", 7, 100.0),
            )
    assert store.migrate_legacy_gateway_notifications() == row_count
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM session_notifications").fetchone()[0] == row_count
        assert conn.execute(
            "SELECT COUNT(*) FROM session_notification_migration_classifications "
            "WHERE migration_version=4 AND classification='inserted'"
        ).fetchone()[0] == row_count
        assert conn.execute("SELECT COUNT(*) FROM session_notification_migration_conflicts").fetchone()[0] == 0
    db.close()


def test_v4_preserves_v3_receipt_and_repairs_false_conflict(tmp_path):
    db, store = _db(tmp_path)
    source_identity = hashlib.sha256(
        b'["gateway_turns","turn-2","inbox-2"]'
    ).hexdigest()
    with sqlite3.connect(db.db_path) as conn:
        conn.executescript("""
            CREATE TABLE gateway_inbox(inbox_id TEXT PRIMARY KEY,idempotency_key TEXT);
            CREATE TABLE gateway_turns(turn_id TEXT PRIMARY KEY,inbox_id TEXT,source_id TEXT,
                session_key TEXT,session_id TEXT,generation INTEGER,created_at REAL);
            INSERT INTO gateway_inbox VALUES('inbox-1','key-1');
            INSERT INTO gateway_inbox VALUES('inbox-2','key-2');
            INSERT INTO gateway_turns VALUES('turn-1','inbox-1','taildrop',
                'agent:main:telegram:dm:42','session-1',7,100.0);
            INSERT INTO gateway_turns VALUES('turn-2','inbox-2','taildrop',
                'agent:main:telegram:dm:42','session-1',7,100.0);
            INSERT INTO state_meta VALUES(
                'session_notifications_legacy_migrated_v3','sealed-v3-receipt');
        """)
        conn.execute(
            "INSERT INTO session_notification_migration_classifications VALUES"
            "(3,'gateway_turns',?,'old-source-digest','migration_conflict',NULL,'old-conflict',100)",
            (source_identity,),
        )
        conn.execute(
            "INSERT INTO session_notification_migration_conflicts VALUES"
            "('gateway_turns',?,'old-source-digest','binding+digest',100,100)",
            (source_identity,),
        )
    assert store.migrate_legacy_gateway_notifications() == 2
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute(
            "SELECT value FROM state_meta WHERE key='session_notifications_legacy_migrated_v3'"
        ).fetchone()[0] == "sealed-v3-receipt"
        assert conn.execute("SELECT COUNT(*) FROM session_notifications").fetchone()[0] == 2
        assert conn.execute(
            "SELECT COUNT(*) FROM session_notification_migration_classifications "
            "WHERE migration_version=3"
        ).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM session_notification_migration_conflicts").fetchone()[0] == 0
    db.close()


@pytest.mark.parametrize("conflict_class", ["key", "ambiguous_source"])
def test_v4_preserves_v3_true_and_ambiguous_conflict_evidence(tmp_path, conflict_class):
    db, store = _db(tmp_path)
    source_identity = hashlib.sha256(
        b'["gateway_turns","turn-1","inbox-1"]'
    ).hexdigest()
    with sqlite3.connect(db.db_path) as conn:
        conn.executescript("""
            CREATE TABLE gateway_inbox(inbox_id TEXT PRIMARY KEY,idempotency_key TEXT);
            CREATE TABLE gateway_turns(turn_id TEXT PRIMARY KEY,inbox_id TEXT,source_id TEXT,
                session_key TEXT,session_id TEXT,generation INTEGER,created_at REAL);
            INSERT INTO gateway_inbox VALUES('inbox-1','key-1');
            INSERT INTO gateway_turns VALUES('turn-1','inbox-1','taildrop',
                'agent:main:telegram:dm:42','session-1',7,100);
            INSERT INTO state_meta VALUES(
                'session_notifications_legacy_migrated_v3','sealed-v3-receipt');
        """)
        conn.execute(
            "INSERT INTO session_notification_migration_classifications VALUES"
            "(3,'gateway_turns',?,'old-source-digest','migration_conflict',NULL,'old-conflict',100)",
            (source_identity,),
        )
        conn.execute(
            "INSERT INTO session_notification_migration_conflicts VALUES"
            "('gateway_turns',?,'old-source-digest',?,100,100)",
            (source_identity, conflict_class),
        )
    assert store.migrate_legacy_gateway_notifications() == 1
    assert store.migrate_legacy_gateway_notifications() == 0
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute(
            "SELECT conflict_class FROM session_notification_migration_conflicts "
            "WHERE source_identity=?", (source_identity,),
        ).fetchone()[0] == conflict_class
        assert conn.execute(
            "SELECT COUNT(*) FROM session_notification_migration_classifications "
            "WHERE migration_version=3 AND source_row_identity=?", (source_identity,),
        ).fetchone()[0] == 1
    db.close()


def test_legacy_identity_collision_is_preserved_as_conflict(tmp_path):
    db, store = _db(tmp_path)
    with sqlite3.connect(db.db_path) as conn:
        conn.executescript("""
            CREATE TABLE gateway_inbox(inbox_id TEXT PRIMARY KEY,idempotency_key TEXT);
            CREATE TABLE gateway_turns(turn_id TEXT PRIMARY KEY,inbox_id TEXT,source_id TEXT,
                session_key TEXT,session_id TEXT,generation INTEGER,created_at REAL);
            INSERT INTO gateway_inbox VALUES('inbox-1','legacy-global-key');
            INSERT INTO gateway_turns VALUES('turn-1','inbox-1','taildrop',
                'agent:main:telegram:dm:42','session-1',7,100.0);
            INSERT INTO session_notifications VALUES(
                'other-key','turn-1','default','other','session-1',
                'agent:main:telegram:dm:42','other',7,'{"event":"x"}','digest',
                'quarantined',1,1,NULL,NULL,NULL);
        """)
    assert store.migrate_legacy_gateway_notifications() == 1
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute(
            "SELECT conflict_class FROM session_notification_migration_conflicts"
        ).fetchone()[0] == "notification_id"
        receipt = conn.execute(
            "SELECT value FROM state_meta WHERE key=?", (MIGRATION_MARKER,)
        ).fetchone()[0]
        assert '"source_count":1' in receipt and '"version":4' in receipt
    assert store.migrate_legacy_gateway_notifications() == 0
    db.close()


def test_migration_transaction_failpoints_leave_every_source_retryable(tmp_path):
    failpoints = (
        "before_notification_insert", "after_notification_insert",
        "before_classification_insert", "after_classification_insert",
        "before_marker", "after_marker", "before_commit",
    )
    for failpoint in failpoints:
        case = tmp_path / failpoint
        case.mkdir()
        db, _ = _db(case)
        with sqlite3.connect(db.db_path) as conn:
            conn.executescript("""
                CREATE TABLE gateway_inbox(inbox_id TEXT PRIMARY KEY,idempotency_key TEXT);
                CREATE TABLE gateway_turns(turn_id TEXT PRIMARY KEY,inbox_id TEXT,source_id TEXT,
                    session_key TEXT,session_id TEXT,generation INTEGER,created_at REAL);
                INSERT INTO gateway_inbox VALUES('inbox-1','legacy-global-key');
                INSERT INTO gateway_turns VALUES('turn-1','inbox-1','taildrop',
                    'agent:main:telegram:dm:42','session-1',7,100.0);
            """)

        def fail(name, expected=failpoint):
            if name == expected:
                raise RuntimeError(expected)

        with pytest.raises(RuntimeError, match=failpoint):
            SessionNotificationStore(db.db_path, failure_hook=fail).migrate_legacy_gateway_notifications()
        with sqlite3.connect(db.db_path) as conn:
            assert conn.execute("SELECT 1 FROM state_meta WHERE key=?", (MIGRATION_MARKER,)).fetchone() is None
            assert conn.execute("SELECT COUNT(*) FROM session_notification_migration_classifications").fetchone()[0] == 0
        assert SessionNotificationStore(db.db_path).migrate_legacy_gateway_notifications() == 1
        db.close()


def test_real_plugin_context_boundary_and_compatibility_trap(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    (home / "config.yaml").write_text(yaml.safe_dump({
        "plugins": {"entries": {"taildrop": {"allow_session_notifications": True}}}
    }))
    ctx = PluginContext(PluginManifest(name="taildrop", key="taildrop", source="user"), PluginManager())
    db = SessionDB(home / "state.db")
    db.create_session("session-1", source="telegram", session_key=SESSION_KEY, profile_name=ctx.profile_name)
    db.append_message("session-1", "user", "active turn")
    before = db.get_messages("session-1")
    forbidden = MagicMock(side_effect=AssertionError("conversation path called"))
    with patch.object(ctx, "_session_notifications_allowed", return_value=True), \
         patch.object(ctx, "_session_notification_store", return_value=SessionNotificationStore(db.db_path)), \
         patch.object(SessionDB, "append_message", forbidden), \
         patch.object(SessionDB, "append_messages_batch", forbidden):
        receipt = ctx.append_notification_once(
            idempotency_key=KEY,
            session_key=SESSION_KEY,
            destination="captain:telegram:42",
            generation=7,
            metadata=METADATA,
        )
    assert receipt.outcome is NotificationOutcome.ACCEPTED
    assert ctx.inject_message_once().outcome is NotificationOutcome.REJECTED
    with patch.object(ctx, "_session_notifications_allowed", return_value=True), \
         patch.object(ctx, "_session_notification_store", return_value=SessionNotificationStore(db.db_path)):
        assert not hasattr(ctx, "list_pending_notifications")
    assert [(m["id"], m["role"]) for m in db.get_messages("session-1")] == [(m["id"], m["role"]) for m in before]
    db.close()


@pytest.mark.parametrize("failpoint", [
    "before_notification_insert", "before_classification_insert",
    "before_conflict_insert", "before_marker",
])
def test_sqlite_full_during_migration_rolls_back_all_evidence(tmp_path, failpoint):
    db, _ = _db(tmp_path)
    with sqlite3.connect(db.db_path) as conn:
        conn.executescript("""
            CREATE TABLE gateway_inbox(inbox_id TEXT PRIMARY KEY,idempotency_key TEXT);
            CREATE TABLE gateway_turns(turn_id TEXT PRIMARY KEY,inbox_id TEXT,source_id TEXT,
                session_key TEXT,session_id TEXT,generation INTEGER,created_at REAL);
            INSERT INTO gateway_inbox VALUES('inbox-1','legacy-key');
            INSERT INTO gateway_turns VALUES('turn-1','inbox-1','taildrop',
                'agent:main:telegram:dm:42','session-1',7,100);
        """)
        if failpoint == "before_conflict_insert":
            conn.execute(
                "INSERT INTO session_notifications VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("other", "turn-1", "default", "other", "session-1", SESSION_KEY,
                 "other", 7, '{"event":"x"}', "digest", "quarantined", 1, 1,
                 None, None, None),
            )

    def full(name):
        if name == failpoint:
            raise sqlite3.OperationalError("database or disk is full")

    with pytest.raises(sqlite3.OperationalError, match="disk is full"):
        SessionNotificationStore(db.db_path, failure_hook=full).migrate_legacy_gateway_notifications()
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute("SELECT 1 FROM state_meta WHERE key=?", (MIGRATION_MARKER,)).fetchone() is None
        assert conn.execute("SELECT COUNT(*) FROM session_notification_migration_classifications").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM session_notification_migration_conflicts").fetchone()[0] == 0
    db.close()


def test_corrupt_partial_schema_and_busy_migration_fail_closed(tmp_path):
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not-a-sqlite-database")
    with pytest.raises(sqlite3.DatabaseError):
        SessionNotificationStore(corrupt).migrate_legacy_gateway_notifications()

    case = tmp_path / "partial"
    case.mkdir()
    db, store = _db(case)
    with sqlite3.connect(db.db_path) as conn:
        conn.execute("CREATE TABLE gateway_inbox(inbox_id TEXT PRIMARY KEY)")
    assert store.migrate_legacy_gateway_notifications() == 0
    lock = sqlite3.connect(db.db_path)
    lock.execute("BEGIN IMMEDIATE")
    with pytest.raises(sqlite3.OperationalError, match="locked"):
        SessionNotificationStore(db.db_path, timeout=0.01).migrate_legacy_gateway_notifications()
    lock.rollback()
    lock.close()
    db.close()


def _ledger_state_for_compaction(path):
    with sqlite3.connect(path) as conn:
        return (
            conn.execute("SELECT notification_id,status FROM session_notifications ORDER BY notification_id").fetchall(),
            conn.execute("SELECT receipt_id,row_count FROM session_notification_compaction_receipts").fetchall(),
            conn.execute("SELECT notification_id,action FROM session_notification_owner_audit").fetchall(),
        )


@pytest.mark.parametrize("failpoint", [
    "before_compaction_receipt", "after_compaction_receipt", "before_compaction_commit",
])
def test_compaction_full_rolls_back_receipt_and_preserves_all_rows(tmp_path, failpoint):
    db, _ = _db(tmp_path)
    store = SessionNotificationStore(db.db_path, clock=lambda: 1000.0)
    first = _append(store)
    _append(store, idempotency_key=KEY + "-pending")
    assert store._acknowledge(
        first.notification_id, profile_name="default", session_key=SESSION_KEY,
        generation=7, identity_binding="captain-binding", retention_seconds=0,
    )
    before = _ledger_state_for_compaction(db.db_path)

    def full(name):
        if name == failpoint:
            raise sqlite3.OperationalError("database or disk is full")

    with pytest.raises(sqlite3.OperationalError, match="disk is full"):
        SessionNotificationStore(db.db_path, clock=lambda: 1000.0, failure_hook=full).compact_acknowledged()
    assert _ledger_state_for_compaction(db.db_path) == before
    db.close()


def test_crash_after_commit_preserves_complete_marker_and_rerun_reconciles(tmp_path):
    db, _ = _db(tmp_path)
    with sqlite3.connect(db.db_path) as conn:
        conn.executescript("""
            CREATE TABLE gateway_inbox(inbox_id TEXT PRIMARY KEY,idempotency_key TEXT);
            CREATE TABLE gateway_turns(turn_id TEXT PRIMARY KEY,inbox_id TEXT,source_id TEXT,
                session_key TEXT,session_id TEXT,generation INTEGER,created_at REAL);
            INSERT INTO gateway_inbox VALUES('inbox-1','legacy-key');
            INSERT INTO gateway_turns VALUES('turn-1','inbox-1','taildrop',
                'agent:main:telegram:dm:42','session-1',7,100);
        """)

    def crash(name):
        if name == "after_commit":
            raise RuntimeError("simulated process death")

    with pytest.raises(RuntimeError, match="process death"):
        SessionNotificationStore(db.db_path, failure_hook=crash).migrate_legacy_gateway_notifications()
    with sqlite3.connect(db.db_path) as conn:
        marker = json.loads(conn.execute("SELECT value FROM state_meta WHERE key=?", (MIGRATION_MARKER,)).fetchone()[0])
        assert marker["source_count"] == 1 and marker["inserted_count"] == 1
        assert conn.execute("SELECT COUNT(*) FROM session_notifications").fetchone()[0] == 1
    assert SessionNotificationStore(db.db_path).migrate_legacy_gateway_notifications() == 0
    db.close()


@pytest.mark.parametrize("case,expected_class,conflict_class", [
    ("key_only", "migration_conflict", "key"),
    ("id_only", "migration_conflict", "notification_id"),
    ("simultaneous", "migration_conflict", "key+notification_id"),
    ("exact", "represented_existing", None),
    ("binding", "migration_conflict", "key+notification_id"),
    ("digest", "migration_conflict", "key+notification_id"),
    ("binding_and_digest", "migration_conflict", "key+notification_id"),
])
def test_complete_legacy_collision_matrix_reconciles_idempotently(
    tmp_path, case, expected_class, conflict_class,
):
    db, store = _db(tmp_path)
    legacy_key = "legacy-global-key"
    key = "legacy:" + hashlib.sha256(legacy_key.encode()).hexdigest()
    metadata_json, digest = canonicalize_metadata({
        "event": "legacy_gateway_notification", "generation": 7,
        "status_label": "ambiguous_quarantined",
    }, 7)
    expected = dict(
        idempotency_key=key, notification_id="turn-1", profile_name="legacy-unknown",
        plugin_id="taildrop", session_id="session-1", session_key=SESSION_KEY,
        destination=SESSION_KEY, generation=7, metadata_json=metadata_json,
        metadata_digest=digest,
    )
    with sqlite3.connect(db.db_path) as conn:
        conn.executescript("""
            CREATE TABLE gateway_inbox(inbox_id TEXT PRIMARY KEY,idempotency_key TEXT);
            CREATE TABLE gateway_turns(turn_id TEXT PRIMARY KEY,inbox_id TEXT,source_id TEXT,
                session_key TEXT,session_id TEXT,generation INTEGER,created_at REAL);
        """)
        conn.execute("INSERT INTO gateway_inbox VALUES('inbox-1',?)", (legacy_key,))
        conn.execute("INSERT INTO gateway_turns VALUES('turn-1','inbox-1','taildrop',?,?,7,100)",
                     (SESSION_KEY, "session-1"))

        rows = []
        if case == "simultaneous":
            rows = [
                {**expected, "notification_id": "other-id"},
                {**expected, "idempotency_key": "other-key"},
            ]
        else:
            row = dict(expected)
            if case == "key_only": row["notification_id"] = "other-id"
            if case == "id_only": row["idempotency_key"] = "other-key"
            if case in {"binding", "binding_and_digest"}: row["destination"] = "other"
            if case in {"digest", "binding_and_digest"}: row["metadata_digest"] = "different"
            rows = [row]
        for row in rows:
            conn.execute(
                "INSERT INTO session_notifications VALUES(?,?,?,?,?,?,?,?,?,?,?,100,100,NULL,NULL,NULL)",
                (row["idempotency_key"], row["notification_id"], row["profile_name"],
                 row["plugin_id"], row["session_id"], row["session_key"], row["destination"],
                 row["generation"], row["metadata_json"], row["metadata_digest"], "quarantined"),
            )

    assert store.migrate_legacy_gateway_notifications() == 1
    with sqlite3.connect(db.db_path) as conn:
        classification = conn.execute(
            "SELECT classification FROM session_notification_migration_classifications "
            "WHERE migration_version=4"
        ).fetchone()[0]
        assert classification == expected_class
        if conflict_class:
            assert conn.execute(
                "SELECT conflict_class FROM session_notification_migration_conflicts"
            ).fetchone()[0] == conflict_class
        marker = json.loads(conn.execute(
            "SELECT value FROM state_meta WHERE key=?", (MIGRATION_MARKER,)
        ).fetchone()[0])
        assert marker[expected_class + "_count"] == 1
        assert sum(marker[name + "_count"] for name in (
            "inserted", "represented_existing", "migration_conflict"
        )) == marker["source_count"] == 1
        sealed = json.dumps(marker, sort_keys=True)
    assert store.migrate_legacy_gateway_notifications() == 0
    with sqlite3.connect(db.db_path) as conn:
        assert json.dumps(json.loads(conn.execute(
            "SELECT value FROM state_meta WHERE key=?", (MIGRATION_MARKER,)
        ).fetchone()[0]), sort_keys=True) == sealed
    db.close()
