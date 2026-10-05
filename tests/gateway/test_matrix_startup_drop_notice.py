"""Startup grace drops must be visible without claiming clock skew or recovery (#133265)."""
import logging
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.matrix.adapter import MatrixAdapter


@pytest.mark.asyncio
async def test_initial_backfill_reports_first_drop_once_without_dispatching(caplog):
    adapter = MatrixAdapter(PlatformConfig(enabled=True, extra={
        "homeserver": "https://matrix.example.org", "user_id": "@bot:example.org",
        "allowed_rooms": "!fixture:example.org",
    }))
    adapter._startup_ts = time.time() - 1
    adapter._handle_text_message = AsyncMock()
    adapter._handle_media_message = AsyncMock()
    with caplog.at_level(logging.INFO, logger="plugins.platforms.matrix.adapter"):
        for index, age in enumerate((21, 300, 1200)):
            timestamp = int((adapter._startup_ts - age) * 1000)
            await adapter._on_room_message(SimpleNamespace(
                room_id="!fixture:example.org", sender="@alice:example.org",
                event_id=f"$private-event-{index}", timestamp=timestamp,
                server_timestamp=timestamp,
                content={"msgtype": "m.text", "body": "private message payload"},
            ))
    notices = [record.getMessage() for record in caplog.records
               if record.name == "plugins.platforms.matrix.adapter" and record.levelno == logging.INFO
               and "startup grace" in record.getMessage()]
    assert len(notices) == 1
    assert "21s before startup" in notices[0]
    assert "not processed" in notices[0]
    assert "private" not in notices[0]
    assert "@alice" not in notices[0] and "!fixture" not in notices[0]
    assert not adapter._clock_skew_warned
    adapter._handle_text_message.assert_not_awaited()
    adapter._handle_media_message.assert_not_awaited()
