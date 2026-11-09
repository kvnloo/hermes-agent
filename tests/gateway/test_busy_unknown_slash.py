"""Unknown slash commands during a running gateway turn must be rejected, not queued.

Regression for NousResearch/hermes-agent#151455, reported by hampsterx.
"""

import pytest

from gateway.config import Platform
from gateway.platforms.event import MessageEvent, MessageType
from gateway.run import GatewayRunner
from gateway.session import SessionSource


@pytest.mark.asyncio
@pytest.mark.parametrize("has_authority", [False, True])
@pytest.mark.parametrize("has_adapter", [False, True])
async def test_unknown_slash_mid_turn_replies_before_busy_input(
    monkeypatch, has_authority, has_adapter
):
    runner = object.__new__(GatewayRunner)
    runner._hm_quick_commands = lambda: {}
    runner._session_key_for_source = lambda _source: "session"
    runner._route_stop_epoch = lambda _key: 0

    async def run_in_executor(callback):
        return callback()

    runner._run_in_executor_with_context = run_in_executor
    monkeypatch.setattr(
        "gateway.session_authorities.active_authority",
        lambda _runner: object() if has_authority else None,
    )
    monkeypatch.setattr("gateway.run._check_unavailable_skill", lambda _name: None)

    source = SessionSource(platform=Platform.TELEGRAM, chat_id="123", chat_type="dm")
    event = MessageEvent(
        text="/zz_not_a_command hello",
        message_type=MessageType.COMMAND,
        source=source,
    )
    assert event.get_command() == "zz_not_a_command"

    handled, reply = await runner._busy_skill_turn(
        event, source, "session", adapter=object() if has_adapter else None
    )

    assert handled is True
    assert reply is not None and "zz_not_a_command" in reply
    assert event.text == "/zz_not_a_command hello"
