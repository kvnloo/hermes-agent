import concurrent.futures
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest
from hermes_state import SessionDB
from session_notifications import (
    NotificationOutcome,
    SessionNotificationStore,
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
    assert len(store.list_pending(profile_name="default", plugin_id="taildrop", session_key=SESSION_KEY)) == 1
    assert store.fetch(receipt.notification_id, profile_name="default", plugin_id="other", session_key=SESSION_KEY) is None
    assert not store.acknowledge(receipt.notification_id, profile_name="default", plugin_id="taildrop", session_key=SESSION_KEY, generation=8, actor="captain")
    assert store.acknowledge(receipt.notification_id, profile_name="default", plugin_id="taildrop", session_key=SESSION_KEY, generation=7, actor="captain", retention_seconds=5)
    assert store.list_pending(profile_name="default", plugin_id="taildrop", session_key=SESSION_KEY) == []
    assert store.compact_acknowledged()[1] == 0
    now[0] += 6
    compaction_receipt, count = store.compact_acknowledged()
    assert count == 1 and compaction_receipt
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute("SELECT row_count FROM session_notification_compaction_receipts WHERE receipt_id=?", (compaction_receipt,)).fetchone()[0] == 1
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
    assert restarted.fetch(accepted.notification_id, profile_name="default", plugin_id="taildrop", session_key=SESSION_KEY)
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
        assert len(ctx.list_pending_notifications(session_key=SESSION_KEY)) == 1
    assert [(m["id"], m["role"]) for m in db.get_messages("session-1")] == [(m["id"], m["role"]) for m in before]
    db.close()
