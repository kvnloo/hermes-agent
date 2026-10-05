"""Partial diagnostic for #133348; does not reproduce the reported topic drop."""

import asyncio
import logging
from types import SimpleNamespace

from plugins.platforms.telegram.adapter import TelegramAdapter


def test_media_update_without_message_logs_reason(caplog):
    with caplog.at_level(logging.DEBUG, logger="plugins.platforms.telegram.adapter"):
        result = asyncio.run(
            TelegramAdapter._handle_media_message(object(), SimpleNamespace(message=None), None)
        )

    assert result is None
    assert [record.getMessage() for record in caplog.records] == [
        "[Telegram] Ignoring media update: no message attached"
    ]
