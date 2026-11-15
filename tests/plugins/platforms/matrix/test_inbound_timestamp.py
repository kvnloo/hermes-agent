"""A Matrix event keeps its server send time across text, media, and voice claiming.

Regression for NousResearch/hermes-agent#156119 and #92400.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.matrix.adapter import MatrixAdapter


@pytest.mark.asyncio
async def test_matrix_message_event_uses_its_own_server_send_time():
    room, sender = "!room:example.org", "@peer:example.org"
    adapter = MatrixAdapter(PlatformConfig(
        enabled=True, token="syt_test_token",
        extra={"homeserver": "https://matrix.example.org", "user_id": "@bot:example.org"},
    ))
    adapter._require_mention = True
    adapter._is_dm_room = AsyncMock(return_value=False)
    adapter._resolve_room_identity = AsyncMock(return_value=SimpleNamespace(
        display_name="Room", room_topic=None, server_name="example.org"))
    adapter._get_display_name = AsyncMock(return_value="Peer")
    adapter._threads = SimpleNamespace(mark_async=AsyncMock())
    adapter._background_read_receipt = lambda *_: None

    received = []

    async def capture(event):
        received.append(event)

    adapter.handle_message = capture
    # Capture batched text at enqueue without changing the real batch delay.
    adapter._enqueue_text_event = received.append
    adapter._free_rooms.add(room)

    sent_at = 1_700_000_000.0
    await adapter._handle_text_message(
        room, sender, "$text", sent_at, {"msgtype": "m.text", "body": "hello"}, {})
    await adapter._handle_media_message(
        room, sender, "$image", sent_at, {"msgtype": "m.image", "body": "picture.png"}, {}, "m.image")
    expected = datetime.fromtimestamp(sent_at, tz=UTC)
    assert [message.timestamp for message in received] == [expected, expected]

    for bad_ts in (0.0, float("nan"), float("inf")):
        before = datetime.now(UTC)
        await adapter._handle_text_message(
            room, sender, "$missing", bad_ts, {"msgtype": "m.text", "body": "fallback"}, {})
        after = datetime.now(UTC)
        assert before <= received[-1].timestamp <= after

    # Element X sends an unmentioned voice and then a separate bare mention.
    adapter._free_rooms.remove(room)
    voice_at = sent_at + 30
    gate = adapter._parked_voices.begin(room, sender, voice_at)
    adapter._parked_voices.park(
        room, sender, gate, "$voice",
        {"msgtype": "m.audio", "body": "voice.ogg", "org.matrix.msc3245.voice": {}}, {})
    adapter._parked_voices.release(room, sender, gate)
    await adapter._handle_text_message(
        room, sender, "$mention", voice_at + 60,
        {"msgtype": "m.text", "body": "@bot:example.org",
         "m.mentions": {"user_ids": ["@bot:example.org"]}}, {})

    assert received[-1].message_id == "$voice"
    assert received[-1].timestamp == datetime.fromtimestamp(voice_at, tz=UTC)
