"""Tests that /new (and its /reset alias) clears session-scoped overrides."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.platforms.event import MessageEvent
from gateway.session import SessionEntry, SessionSource, build_session_key


def _make_source() -> SessionSource:
    return SessionSource(
        platform=Platform.TELEGRAM,
        user_id="u1",
        chat_id="c1",
        user_name="tester",
        chat_type="dm",
    )


def _make_event(text: str) -> MessageEvent:
    return MessageEvent(text=text, source=_make_source(), message_id="m1")


def _make_runner():
    from gateway.run import GatewayRunner

    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(
        platforms={Platform.TELEGRAM: PlatformConfig(enabled=True, token="***")}
    )
    adapter = MagicMock()
    adapter.send = AsyncMock()
    runner.adapters = {Platform.TELEGRAM: adapter}
    runner._voice_mode = {}
    runner.hooks = SimpleNamespace(emit=AsyncMock(), loaded_hooks=False)
    runner._session_model_overrides = {}
    runner._pending_model_notes = {}
    runner._background_tasks = set()

    session_key = build_session_key(_make_source())
    session_entry = SessionEntry(
        session_key=session_key,
        session_id="sess-1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        platform=Platform.TELEGRAM,
        chat_type="dm",
    )
    runner.session_store = MagicMock()
    runner.session_store.get_or_create_session.return_value = session_entry
    runner.session_store.reset_session.return_value = session_entry
    runner.session_store._entries = {session_key: session_entry}
    runner.session_store._generate_session_key.return_value = session_key
    runner._running_agents = {}
    runner._pending_messages = {}
    runner._session_db = None
    runner._agent_cache_lock = None  # disables _evict_cached_agent lock path
    runner._is_user_authorized = lambda _source: True
    runner._format_session_info = lambda: ""

    return runner


@pytest.mark.asyncio
async def test_new_command_only_clears_own_session():
    """/new must only clear the override for the session that triggered it."""
    runner = _make_runner()
    session_key = build_session_key(_make_source())
    other_key = "other_session_key"

    runner._session_model_overrides[session_key] = {
        "model": "gpt-4o",
        "provider": "openai",
        "api_key": "sk-test",
        "base_url": "",
        "api_mode": "openai",
    }
    runner._session_model_overrides[other_key] = {
        "model": "claude-sonnet-4-6",
        "provider": "anthropic",
        "api_key": "***",
        "base_url": "",
        "api_mode": "anthropic",
    }
    runner._session_state(session_key).conversation.reasoning_override = {"enabled": True, "effort": "high"}
    runner._session_state(other_key).conversation.reasoning_override = {"enabled": True, "effort": "low"}
    runner._pending_model_notes[session_key] = "[Note: switched to gpt-4o.]"
    runner._pending_model_notes[other_key] = "[Note: switched to claude-sonnet-4-6.]"

    await runner._handle_reset_command(_make_event("/new"))

    assert session_key not in runner._session_model_overrides
    assert other_key in runner._session_model_overrides
    assert runner._session_state(session_key).conversation.reasoning_override is None
    assert runner._session_state(other_key).conversation.reasoning_override is not None
    assert session_key not in runner._pending_model_notes
    assert other_key in runner._pending_model_notes


@pytest.mark.asyncio
async def test_new_reports_only_held_finished_results_for_the_old_chat(tmp_path, monkeypatch):
    """A transport-held completion must be disclosed at /new, never silently lost."""
    import time
    from tools import async_delegation as delegation

    runner = _make_runner()
    runner._session_db = MagicMock()
    runner.session_store._profile_home_for_key.return_value = tmp_path
    monkeypatch.setattr(delegation, "get_hermes_home", lambda: tmp_path)
    key = build_session_key(_make_source())

    def record(name, *, route=key, parent="sess-1", delivery="pending", finished=True):
        event = {"type": "async_delegation", "delegation_id": name,
                 "session_key": route, "parent_session_id": parent,
                 "dispatched_at": time.time(), "status": "completed"}
        delegation._persist_dispatch(event)
        if finished:
            delegation._persist_completion(
                event, {"status": "completed", "summary": name}, delivery=delivery)

    record("held-one")
    record("held-two")
    record("acknowledged-uuid", delivery="delivered")
    record("foreign-parent-uuid", parent="another-session")
    record("foreign-chat-uuid", route="agent:main:telegram:dm:foreign")
    record("running-uuid", finished=False)

    reply = str(await runner._handle_reset_command(_make_event("/new")))
    assert "2 completed background result(s)" in reply
    assert "`held-one`" in reply and "`held-two`" in reply
    assert all(f"`{name}`" not in reply for name in
               ("acknowledged-uuid", "foreign-parent-uuid", "foreign-chat-uuid", "running-uuid"))
    assert "SELECT result_json FROM async_delegations" in reply
    assert delegation.get_durable_delegation("held-one")["delivery_state"] == "pending"
