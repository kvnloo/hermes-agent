"""BlueBubbles recovery notice and first reply paragraph share one send (#154857)."""

from unittest.mock import AsyncMock

import pytest

from gateway.config import PlatformConfig
from gateway.delivery_ledger import FLOOD_MARKER, RECONNECTED_MARKER, RECOVERED_MARKER
from gateway.platforms.base import SendResult
from plugins.platforms.bluebubbles.adapter import BlueBubblesAdapter


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "marker",
    (RECOVERED_MARKER, RECONNECTED_MARKER, FLOOD_MARKER),
    ids=("restart", "reconnect", "rate-limit"),
)
async def test_recovered_notice_never_arrives_without_first_reply_paragraph(
    monkeypatch, marker,
):
    adapter = BlueBubblesAdapter(PlatformConfig(
        enabled=True, extra={"server_url": "http://localhost:1234", "password": "test"},
    ))
    posted = []

    async def post(_path, payload):
        posted.append(payload["message"])
        # The second request times out, as in the reported redelivery.
        return (SendResult(success=True) if len(posted) == 1
                else SendResult(success=False, error="ReadTimeout"))

    monkeypatch.setattr(adapter, "_resolve_chat_guid", AsyncMock(return_value="any;-;test"))
    monkeypatch.setattr(adapter, "_post_message", post)

    result = await adapter.send(
        "any;-;test", marker + "First reply paragraph.\n\nSecond reply paragraph.",
    )

    assert not result.success
    assert posted == [
        f"{marker.strip()}\nFirst reply paragraph.",
        "Second reply paragraph.",
    ]
