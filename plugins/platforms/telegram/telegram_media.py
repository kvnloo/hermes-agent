"""Telegram attachment classification shared by inbound media paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gateway.platforms.event import MessageType

if TYPE_CHECKING:
    from telegram import Message


def media_message_type(msg: Message) -> MessageType:
    """Classify a Telegram media message into a MessageType (first present attachment wins)."""
    for attr, mtype in (
        ("sticker", MessageType.STICKER), ("photo", MessageType.PHOTO), ("video", MessageType.VIDEO),
        ("audio", MessageType.AUDIO), ("voice", MessageType.VOICE)):
        if getattr(msg, attr):
            return mtype
    return MessageType.DOCUMENT
