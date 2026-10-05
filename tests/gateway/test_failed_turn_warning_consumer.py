"""Real policy and durable-state consumers of owner PR #129922 (issue #129917)."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from agent.turn_failure_copy import FAILED_TURN_DISPLAY_KIND, PARTIAL_FAILED_TURN_NOTICE
from gateway.config import GatewayConfig, Platform
from gateway.platforms.event import MessageEvent
from gateway.run import GatewayRunner
from gateway.session import SessionSource, SessionStore


@pytest.fixture(params=[False, True], ids=["visible", "suppressed"])
def warning_policy(request, tmp_path, monkeypatch):
    home = tmp_path / "profile"
    home.mkdir()
    (home / "config.yaml").write_text(
        "display:\n  platforms:\n    whatsapp:\n"
        f"      suppress_warning_notifications: {str(request.param).lower()}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "user")
    return request.param


@pytest.mark.asyncio
async def test_result_warning_policy_preserves_requested_answer(warning_policy):
    runner = object.__new__(GatewayRunner)
    runner._delivery_adapter_for = Mock(return_value=None)
    runner._should_send_voice_reply = Mock(return_value=False)
    runner._send_voice_reply = AsyncMock(side_effect=AssertionError("unexpected voice delivery"))
    source = SessionSource(platform=Platform.WHATSAPP, chat_id="synthetic", user_id="user")
    event = MessageEvent(text="compare alternatives", source=source)
    entry = SimpleNamespace(session_id="synthetic")

    async def deliver(result, text):
        return await runner._hmwa_deliver_turn_response(
            event, source, entry, "synthetic", None, result, [], text, None, False,
        )

    assert await deliver({"failed": False}, "requested answer") == "requested answer"
    warning = "automatic failed-turn guidance"
    assert await deliver({"failed": True}, warning) == (None if warning_policy else warning)
    runner._send_voice_reply.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("overflow", [False, True], ids=["exception", "overflow"])
async def test_exception_warning_policy_preserves_durable_contract(tmp_path, warning_policy, overflow):
    runner = object.__new__(GatewayRunner)
    store = SessionStore(tmp_path / "sessions", GatewayConfig())
    runner.session_store = store
    runner._hmwa_stop_typing_for_turn = AsyncMock()
    source = SessionSource(platform=Platform.WHATSAPP, chat_id="synthetic", user_id="user")
    entry = store.get_or_create_session(source)
    db = store._db_for_session_id(entry.session_id)
    owner = "synthetic-input"
    prepared = runner._PreparedTurn(
        [{"role": "user", "content": "prior"}] * 51 if overflow else [],
        "", "compare alternatives", "compare alternatives", None, None, entry.session_id, owner,
    )
    error = RuntimeError("synthetic failure")
    if overflow:
        error.status_code = 400
    event = MessageEvent(text="compare alternatives", source=source, message_id="message-1")
    try:
        reply = await runner._hmwa_agent_error_reply(
            error, event, source, entry, entry.session_key, prepared,
        )
        messages = db.get_messages(entry.session_id)
        if overflow:
            assert messages == []  # A rejected oversized input must not grow the session.
        else:
            assert [message["role"] for message in messages] == ["user", "assistant"]
            assert store.has_input_owner(entry.session_id, owner)
            assert messages[-1]["content"] == PARTIAL_FAILED_TURN_NOTICE
            assert messages[-1]["display_kind"] == FAILED_TURN_DISPLAY_KIND
        if warning_policy:
            assert reply is None
        elif overflow:
            assert "/compress" in reply and "/new" in reply
        else:
            assert PARTIAL_FAILED_TURN_NOTICE in reply
        runner._hmwa_stop_typing_for_turn.assert_awaited_once_with(event, source)
    finally:
        db.close()
