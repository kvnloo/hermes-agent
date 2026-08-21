import json
import sqlite3
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateway.config import GatewayConfig, Platform, PlatformConfig
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
    runner.config = GatewayConfig(platforms={Platform.TELEGRAM: PlatformConfig(
        enabled=True, token="test-token", extra={"allow_admin_from": ["42"]},
    )})
    adapter = MagicMock()
    adapter.send = AsyncMock(side_effect=AssertionError("out-of-band platform send"))
    adapter._pending_messages = {}
    runner.adapters = {Platform.TELEGRAM: adapter}
    runner.hooks = SimpleNamespace(
        emit=AsyncMock(), emit_collect=AsyncMock(return_value=[]), loaded_hooks=False,
    )
    runner.session_store = MagicMock()
    runner._voice_mode = {}
    runner._running_agents_ts = {}
    runner._session_run_generation = {}
    runner._pending_approvals = {}
    runner._session_sources = {}
    runner._session_db = MagicMock()
    runner._is_user_authorized = lambda source: live["authorized"] and source.user_id == "42"
    runner._session_key_for_source = lambda source: SESSION_KEY if source.chat_id == "42" else f"other:{source.chat_id}"
    runner._peek_session_state = lambda key: SimpleNamespace(
        persistent=SimpleNamespace(
            run_generation=live["generation"], update_prompt_pending=False,
        ),
        turn=SimpleNamespace(agent=runner._running_agents.get(key), started_ts=0),
    )
    runner._running_agents = {}
    runner._pending_messages = {}
    return runner


async def _dispatch(runner, text, **source):
    """Exercise the production pre-resolution gateway message entrypoint."""
    return await GatewayRunner._handle_message(runner, _event(text, **source))


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


@pytest.mark.asyncio
async def test_production_dispatch_authorized_parses_and_never_falls_through(tmp_path, monkeypatch):
    db, notification_id = _seed(tmp_path, monkeypatch)
    runner = _runner(db.db_path, {"authorized": True, "generation": 7})
    forbidden = MagicMock(side_effect=AssertionError("agent path reached"))
    runner._handle_message_with_agent = forbidden
    runner._run_agent = forbidden
    before_messages = db.get_messages("session-1")
    prohibited = [
        "append_message", "append_messages_batch", "update_session_meta",
        "update_system_prompt", "update_session_model", "update_token_counts",
        "set_latest_matching_message_display_kind", "set_message_reaction",
        "set_latest_user_api_content", "delete_session", "delete_sessions", "set_meta",
    ]
    with ExitStack() as stack:
        guards = [stack.enter_context(patch.object(
            SessionDB, name, side_effect=AssertionError(f"SessionDB.{name} called")
        )) for name in prohibited]
        tool_guard = stack.enter_context(patch(
            "model_tools.handle_function_call", side_effect=AssertionError("tool execution called")
        ))
        model_guard = stack.enter_context(patch(
            "run_agent.AIAgent.run_conversation", side_effect=AssertionError("model loop called")
        ))
        listed = await _dispatch(runner, "/notifications list")
        fetched = json.loads(await _dispatch(runner, f"/notifications fetch {notification_id}"))
        acked = await _dispatch(runner, f"/notifications ack {notification_id}")
    for guard in [*guards, tool_guard, model_guard]:
        guard.assert_not_called()
    assert notification_id in listed
    assert fetched["notification_id"] == notification_id
    assert acked == f"Acknowledged {notification_id}."
    assert db.get_messages("session-1") == before_messages
    forbidden.assert_not_called()
    assert runner._pending_messages == {}
    assert runner.adapters[Platform.TELEGRAM]._pending_messages == {}
    runner.adapters[Platform.TELEGRAM].send.assert_not_awaited()
    db.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("source", [
    {"user": "99"}, {"chat": "99"}, {"platform": Platform.DISCORD}, {"profile": "other"},
])
async def test_production_dispatch_wrong_scope_zero_leak_and_mutation(tmp_path, monkeypatch, source):
    db, notification_id = _seed(tmp_path, monkeypatch)
    runner = _runner(db.db_path, {"authorized": True, "generation": 7})
    before = (_ledger_state(db.db_path), db.get_messages("session-1"))
    response = await _dispatch(runner, "/notifications list", **source)
    assert response is None or (notification_id not in response and "taildrop" not in response)
    assert (_ledger_state(db.db_path), db.get_messages("session-1")) == before
    assert runner._pending_messages == {}
    db.close()


@pytest.mark.asyncio
async def test_production_dispatch_stale_revoked_malformed_replay_and_busy(tmp_path, monkeypatch):
    db, notification_id = _seed(tmp_path, monkeypatch)
    live = {"authorized": True, "generation": 6}
    runner = _runner(db.db_path, live)
    baseline = (_ledger_state(db.db_path), db.get_messages("session-1"))
    for text in ("/notifications list copied", "/notifications fetch", "/notifications ack",
                 "/notifications nope", "/notifications list"):
        response = await _dispatch(runner, text)
        assert notification_id not in response and "taildrop" not in response
    live["generation"] = 7
    live["authorized"] = False
    assert await _dispatch(runner, "/notifications list") is None
    live["authorized"] = True
    runner._running_agents[SESSION_KEY] = MagicMock()
    busy = await _dispatch(runner, "/notifications list")
    assert "running" in busy.lower() and notification_id not in busy
    assert (_ledger_state(db.db_path), db.get_messages("session-1")) == baseline
    assert runner._pending_messages == {}
    db.close()
