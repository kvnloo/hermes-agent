"""Regression for NousResearch/hermes-agent#155002: a held result cannot be silent forever."""

import asyncio
import contextlib
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

from gateway import warning_notifications
from gateway.config import GatewayConfig, Platform
from gateway.run import GatewayRunner
from gateway.session import SessionSource


def _runner(monkeypatch, *, home_profile="ops"):
    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(multiplex_profiles=True)
    runner._primary_profile_name = "default"
    runner.adapters = {}
    runner._build_process_event_source = lambda _evt: SessionSource(
        platform=Platform.TELEGRAM, chat_id="chat-secret", chat_type="dm", profile="ops")
    runner._resolve_injection_adapter = lambda _platform, _source: None
    runner._completion_event_scope = lambda _evt: contextlib.nullcontext()
    runner._served_home_channel_transports = lambda: iter([
        (home_profile, Platform.TELEGRAM, None, SimpleNamespace(chat_id="admin"), object())])
    runner._send_home_channel_message = AsyncMock(return_value=True)
    monkeypatch.setattr(warning_notifications, "effective_user_config", lambda: {})
    return runner


def _event(seconds_old):
    return {"type": "async_delegation", "delegation_id": "d1",
            "completed_at": time.time() - seconds_old, "goal": "PRIVATE GOAL"}


def test_held_completion_alerts_own_home_once_after_real_ten_minute_default(monkeypatch):
    runner = _runner(monkeypatch)
    evt = _event(590)
    assert asyncio.run(runner._completion_delivery_ready(evt)) is False
    runner._send_home_channel_message.assert_not_awaited()

    evt["completed_at"] = time.time() - 610
    for _ in range(3):
        assert asyncio.run(runner._completion_delivery_ready(evt)) is False
    runner._send_home_channel_message.assert_awaited_once()
    message = runner._send_home_channel_message.await_args.args[3]
    assert "10 minutes" in message and "pending" in message
    assert "PRIVATE GOAL" not in message and "chat-secret" not in message
    assert evt["_no_transport"] is True  # existing durable-delivery deferral remains intact


def test_held_completion_never_crosses_profiles_and_failed_notice_can_retry(monkeypatch):
    foreign = _runner(monkeypatch, home_profile="other")
    evt = _event(610)
    assert asyncio.run(foreign._completion_delivery_ready(evt)) is False
    foreign._send_home_channel_message.assert_not_awaited()

    owner = _runner(monkeypatch)
    owner._send_home_channel_message = AsyncMock(side_effect=[False, True])
    assert asyncio.run(owner._completion_delivery_ready(evt)) is False
    assert asyncio.run(owner._completion_delivery_ready(evt)) is False
    assert asyncio.run(owner._completion_delivery_ready(evt)) is False
    assert owner._send_home_channel_message.await_count == 2
