import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gateway.config import Platform
from gateway.platforms.base import MessageEvent
from gateway.run import GatewayRunner
from gateway.session import SessionSource
from hermes_state import SessionDB
from session_notifications import NotificationOutcome, SessionNotificationStore


SESSION_KEY = "agent:main:telegram:dm:42"
METADATA = {"event": "taildrop_received", "generation": 7, "sender": "captain"}


def _source(*, user="42", chat="42", platform=Platform.TELEGRAM, profile="default"):
    return SessionSource(platform, chat, user_id=user, profile=profile)


def _event(text, **source):
    return MessageEvent(text=text, source=_source(**source))


def _runner(db_path, live):
    runner = object.__new__(GatewayRunner)
    runner.config = SimpleNamespace(platforms={
        Platform.TELEGRAM: SimpleNamespace(extra={"allow_admin_from": ["42"]})
    })
    runner._is_user_authorized = lambda source: live["authorized"] and source.user_id == "42"
    runner._session_key_for_source = lambda source: SESSION_KEY if source.chat_id == "42" else f"other:{source.chat_id}"
    runner._peek_session_state = lambda key: SimpleNamespace(
        persistent=SimpleNamespace(run_generation=live["generation"])
    )
    runner._running_agents = {}
    runner._pending_messages = {}
    return runner


def _seed(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    db = SessionDB(home / "state.db")
    db.create_session("session-1", source="telegram", session_key=SESSION_KEY, profile_name="default")
    db.append_message("session-1", "user", "transcript sentinel")
    receipt = SessionNotificationStore(db.db_path).append_once(
        idempotency_key="route-key", profile_name="default", plugin_id="taildrop",
        session_key=SESSION_KEY, destination="captain:telegram:42", generation=7,
        metadata=METADATA,
    )
    assert receipt.outcome is NotificationOutcome.ACCEPTED
    return db, receipt.notification_id


def _ledger_state(path):
    with sqlite3.connect(path) as conn:
        return tuple(conn.execute(
            "SELECT (SELECT COUNT(*) FROM session_notifications),"
            "(SELECT COUNT(*) FROM session_notification_owner_audit),"
            "(SELECT COUNT(*) FROM session_notification_migration_classifications),"
            "(SELECT COUNT(*) FROM session_notification_migration_conflicts)"
        ).fetchone())


@pytest.mark.asyncio
async def test_real_gateway_notification_route_authorized_scope_and_single_use(tmp_path, monkeypatch):
    db, notification_id = _seed(tmp_path, monkeypatch)
    live = {"authorized": True, "generation": 7}
    runner = _runner(db.db_path, live)
    listed = await runner._handle_notifications_command(_event("/notifications list"))
    assert notification_id in listed and "taildrop_received" in listed and "gen=7" in listed
    fetched = json.loads(await runner._handle_notifications_command(
        _event(f"/notifications fetch {notification_id}")))
    assert fetched == {
        "generation": 7, "metadata": METADATA, "notification_id": notification_id,
        "plugin_id": "taildrop", "status": "pending",
    }
    assert await runner._handle_notifications_command(
        _event(f"/notifications ack {notification_id}")) == f"Acknowledged {notification_id}."
    replay = await runner._handle_notifications_command(_event(f"/notifications ack {notification_id}"))
    assert "already resolved" in replay
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM session_notification_owner_audit").fetchone()[0] == 1
        assert conn.execute("SELECT role,content FROM messages").fetchall() == [("user", "transcript sentinel")]
    assert runner._pending_messages == {}
    db.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("event", [
    _event("/notifications list", user="99"),
    _event("/notifications list", chat="99"),
    _event("/notifications list", platform=Platform.DISCORD),
    _event("/notifications list", profile="other"),
])
async def test_real_gateway_route_wrong_scope_refuses_without_leak_or_mutation(tmp_path, monkeypatch, event):
    db, notification_id = _seed(tmp_path, monkeypatch)
    runner = _runner(db.db_path, {"authorized": True, "generation": 7})
    before_bytes = db.db_path.read_bytes()
    before_state = _ledger_state(db.db_path)
    response = await runner._handle_notifications_command(event)
    assert response in {"⛔ Owner notification access denied.", "No pending notifications."}
    assert notification_id not in response and "taildrop" not in response and "received" not in response
    assert _ledger_state(db.db_path) == before_state
    assert db.db_path.read_bytes() == before_bytes
    db.close()


@pytest.mark.asyncio
async def test_route_stale_revoked_malformed_and_authorization_read_race_fail_closed(tmp_path, monkeypatch):
    db, notification_id = _seed(tmp_path, monkeypatch)
    live = {"authorized": True, "generation": 6}
    runner = _runner(db.db_path, live)
    baseline = _ledger_state(db.db_path)
    for command in ("/notifications list copied", "/notifications fetch", "/notifications ack", "/notifications nope"):
        response = await runner._handle_notifications_command(_event(command))
        assert notification_id not in response and "taildrop" not in response
    for command in ("/notifications list", f"/notifications fetch {notification_id}", f"/notifications ack {notification_id}"):
        response = await runner._handle_notifications_command(_event(command))
        assert notification_id not in response
    live["generation"] = 7
    live["authorized"] = False
    assert "denied" in (await runner._handle_notifications_command(_event("/notifications list"))).lower()
    assert _ledger_state(db.db_path) == baseline

    live["authorized"] = True
    original_fetch = SessionNotificationStore._fetch
    def revoke_after_read(store, *args, **kwargs):
        row = original_fetch(store, *args, **kwargs)
        live["authorized"] = False
        return row
    with patch.object(SessionNotificationStore, "_fetch", revoke_after_read):
        response = await runner._handle_notifications_command(_event(f"/notifications fetch {notification_id}"))
    assert notification_id not in response and _ledger_state(db.db_path) == baseline
    db.close()
