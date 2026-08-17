"""Telegram gateway commands execute only from current-message text."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from gateway.config import PlatformConfig
from gateway.platforms.base import MessageEvent, MessageType
from plugins.platforms.telegram.adapter import TelegramAdapter


def _message(
    text: str = "/chat brainstorm",
    *,
    chat_id: int = 123,
    chat_type: str = "private",
    thread_id: int | None = None,
    forward_origin=None,
    forward_date=None,
    is_automatic_forward: bool = False,
    reply_text: str | None = None,
    quote_text: str | None = None,
):
    reply = None
    if reply_text is not None:
        reply = SimpleNamespace(
            message_id=8,
            text=reply_text,
            caption=None,
            api_kwargs={},
        )
    quote = SimpleNamespace(text=quote_text) if quote_text is not None else None
    return SimpleNamespace(
        message_id=9,
        text=text,
        caption=None,
        date=datetime.now(timezone.utc),
        chat=SimpleNamespace(
            id=chat_id,
            type=chat_type,
            title="Room" if chat_type != "private" else None,
            full_name="Direct User",
            is_forum=False,
        ),
        from_user=SimpleNamespace(id=77, full_name="Alice", is_bot=False),
        message_thread_id=thread_id,
        is_topic_message=thread_id is not None,
        forum_topic_created=None,
        reply_to_message=reply,
        quote=quote,
        forward_origin=forward_origin,
        forward_date=forward_date,
        is_automatic_forward=is_automatic_forward,
    )


def _event(message) -> MessageEvent:
    adapter = TelegramAdapter(PlatformConfig(enabled=True, token="fake-token"))
    return adapter._build_message_event(message, MessageType.TEXT, update_id=42)


@pytest.mark.parametrize(
    "forward_fields",
    [
        {"forward_origin": SimpleNamespace(type="user")},
        {"forward_date": datetime.now(timezone.utc)},
        {"is_automatic_forward": True},
    ],
)
def test_forwarded_slash_text_cannot_execute_gateway_command(forward_fields):
    event = _event(_message(**forward_fields))

    assert event.text == "/chat brainstorm"
    assert event.metadata["gateway_control_text_origin"] == "forwarded_message"
    assert event.is_command() is False
    assert event.get_command() is None


def test_forwarded_caption_remains_non_command_when_media_handler_sets_text():
    event = _event(_message(text="", forward_origin=SimpleNamespace(type="channel")))
    event.text = "/chat brainstorm"  # mirrors caption assignment after normalization

    assert event.is_command() is False


@pytest.mark.parametrize(
    ("chat_id", "chat_type", "thread_id"),
    [(123, "private", None), (-1001, "group", None), (-1001, "supergroup", 17)],
)
def test_current_slash_executes_in_dm_group_and_thread(chat_id, chat_type, thread_id):
    event = _event(_message(chat_id=chat_id, chat_type=chat_type, thread_id=thread_id))

    assert event.metadata["gateway_control_text_origin"] == "current_message"
    assert event.is_command() is True
    assert event.get_command() == "chat"


def test_current_slash_reply_executes_but_reply_preview_slash_does_not():
    current = _event(_message(reply_text="/stop", quote_text="/new"))
    preview_only = _event(_message(text="looks good", reply_text="/chat brainstorm"))

    assert current.is_command() is True
    assert current.get_command() == "chat"
    assert preview_only.is_command() is False


def test_inline_prose_and_malformed_provenance_do_not_execute():
    inline = _event(_message(text="please run /chat brainstorm"))
    malformed = MessageEvent(
        text="/chat brainstorm",
        metadata={"gateway_control_text_origin": {"unexpected": True}},
    )

    assert inline.is_command() is False
    assert malformed.is_command() is False