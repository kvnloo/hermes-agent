"""Regression: opt-in agent-authored Slack blocks reach the real adapter send seam.

Companion to ilya-bogin-keenable's NousResearch/hermes-agent#156034.  Pure
extractor tests alone cannot catch the adapter silently sending plain text.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.slack.adapter import SlackAdapter


@pytest.mark.asyncio
async def test_agent_blocks_send_payload_and_fence_free_fallback():
    header = {
        "type": "header",
        "text": {"type": "plain_text", "text": "Weekly metrics"},
    }
    content = "Weekly report.\n\n```slack-blocks\n" + json.dumps([header]) + "\n```"
    adapter = SlackAdapter(PlatformConfig(
        enabled=True, token="xoxb-fake", extra={"agent_blocks": True},
    ))
    adapter._app = MagicMock()
    client = AsyncMock()
    client.chat_postMessage = AsyncMock(return_value={"ts": "111.222"})
    adapter._get_client = MagicMock(return_value=client)
    adapter.stop_typing = AsyncMock()
    adapter._running = True

    result = await adapter.send("C1", content)

    assert result.success is True
    client.chat_postMessage.assert_awaited_once()
    payload = client.chat_postMessage.await_args.kwargs
    assert payload["blocks"] == [header]
    assert payload["text"] == "Weekly report."
    assert "slack-blocks" not in payload["text"]
