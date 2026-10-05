"""Signal consumers must distinguish addressed messages after display-text cleanup (#133247)."""
from unittest.mock import AsyncMock

import pytest

from gateway.config import PlatformConfig
from gateway.platforms.signal import SignalAdapter


@pytest.mark.asyncio
async def test_dispatch_consumer_retains_mentions_after_bot_name_is_stripped(monkeypatch):
    account = "+15551234567"
    monkeypatch.setenv("SIGNAL_GROUP_ALLOWED_USERS", "fixture-group")
    config = PlatformConfig()
    config.extra = {"account": account, "require_mention": False}
    adapter = SignalAdapter(config)
    dispatched = AsyncMock()
    monkeypatch.setattr(adapter, "handle_message", dispatched)
    question = "where should we stay?"
    mentions = [{"start": 0, "length": 1, "number": account}]
    for content in (
        {"message": f"\ufffc {question}", "mentions": mentions},
        {"message": question},
    ):
        await adapter._handle_envelope({
            "envelope": {
                "sourceNumber": "+15550000001",
                "timestamp": 1777600696000,
                "dataMessage": {
                    "groupInfo": {"groupId": "fixture-group"},
                    **content,
                },
            },
        })

    addressed, ordinary = [call.args[0] for call in dispatched.await_args_list]
    assert addressed.text == ordinary.text == question
    # A dispatch consumer cannot recover this distinction from cleaned text.
    assert [
        any(mention.get("number") == account for mention in event.raw_message.get("mentions", []))
        for event in (addressed, ordinary)
    ] == [True, False]
    assert addressed.raw_message["mentions"] == mentions
    assert ordinary.raw_message["mentions"] == []
