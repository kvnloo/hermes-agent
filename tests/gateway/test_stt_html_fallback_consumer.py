"""Literal STT fallback preservation requested by liyangbing on PR #98419."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.error import BadRequest

from gateway.config import PlatformConfig
from gateway.stt_echo import format_stt_transcript_echo, stt_echo_metadata
from plugins.platforms.telegram.adapter import TelegramAdapter


@pytest.mark.asyncio
async def test_stt_html_rejection_preserves_literal_transcript():
    transcript = (
        'Say <tag> & "quoted" words.\n'
        'Read <blockquote expandable>literally</blockquote>, then &lt;tag&gt; and 🎵.'
    )
    formatted = format_stt_transcript_echo(transcript, "telegram")
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="synthetic-token"))
    sent = []

    async def send_message(**kwargs):
        sent.append(dict(kwargs))
        if len(sent) == 1:
            raise BadRequest("Can't parse entities: synthetic HTML rejection")
        return SimpleNamespace(message_id=42)

    adapter._bot = SimpleNamespace(send_message=AsyncMock(side_effect=send_message))
    result = await adapter.send(
        "123", formatted, metadata=stt_echo_metadata("telegram", {"notify": True}))

    assert result.success is True
    assert result.message_id == "42"
    assert len(sent) == 2
    assert sent[0]["parse_mode"] == "HTML"
    assert sent[0]["text"] == formatted
    assert sent[1]["parse_mode"] is None
    assert sent[1]["text"] == "🎙️\n" + transcript
