"""Regression for alexcf's #31566: webhook clarifies must use native delivery UI.

A webhook-sourced session key is not a Discord session key. Rendering a text
question through the webhook adapter cannot be answered by a Discord button.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import SendResult
from gateway.platforms.webhook import WebhookAdapter, _INSECURE_NO_AUTH


@pytest.mark.asyncio
async def test_webhook_clarify_targets_native_delivery_chat():
    """#31565: an approval question must reach Discord's native button flow."""
    adapter = WebhookAdapter(PlatformConfig(enabled=True, extra={
        "routes": {
            "approval": {
                "secret": _INSECURE_NO_AUTH,
                "prompt": "Please approve the draft.",
                "deliver": "discord",
                "deliver_extra": {"chat_id": "channel-123", "thread_id": "thread-456"},
            },
        },
    }))
    adapter.handle_message = AsyncMock()

    discord = AsyncMock()
    discord.send_clarify.return_value = SendResult(success=True)
    discord.send.return_value = SendResult(success=True)
    runner = MagicMock()
    runner.adapters = {Platform.DISCORD: discord}
    adapter.gateway_runner = runner

    # Exercise the real webhook ingress: it stores delivery metadata under the
    # webhook session, not under the destination chat's session key.
    app = web.Application()
    app.router.add_post("/webhooks/{route_name}", adapter._handle_webhook)
    async with TestClient(TestServer(app)) as client:
        response = await client.post(
            "/webhooks/approval",
            json={"event": "approval"},
            headers={"X-GitHub-Delivery": "event-123"},
        )
        assert response.status == 202

    source_chat = "webhook:approval:event-123"
    assert source_chat in adapter._delivery_info
    choices = ["Send", "Discard"]
    result = await adapter.send_clarify(
        chat_id=source_chat,
        question="Send the draft?",
        choices=choices,
        clarify_id="clarify-789",
        session_key=source_chat,
        metadata={"origin": "webhook"},
    )

    # Without #31566 the inherited base text fallback never invokes the
    # destination adapter's send_clarify, so this fails on the PR merge base.
    discord.send_clarify.assert_awaited_once_with(
        chat_id="channel-123",
        question="Send the draft?",
        choices=choices,
        clarify_id="clarify-789",
        session_key=source_chat,
        metadata={"origin": "webhook", "thread_id": "thread-456"},
    )
    assert result.success
