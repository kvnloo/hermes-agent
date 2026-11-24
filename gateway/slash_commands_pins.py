"""/pin, /pins and /unpin: the user's own pins in the session's decision ledger (agent/pins.py).

One handler serves messaging chats and, through ``slash.exec`` (gateway/session_commands.py), the classic CLI,
the TUI and Desktop. A slash command is typed by the user, so these handlers are the only writers that pass
``origin="user"``; nothing the model, a tool or a plugin emits reaches them.
"""

from __future__ import annotations

import asyncio
import contextlib

from gateway.platforms.event import MessageEvent

_USAGE = "Usage: /pin <text> | /pin (pins your last message) | /pin patch <n> <text> | /pins | /unpin <n>"


def _number(word: str):
    try:
        return int(word)
    except (TypeError, ValueError):
        return None


def _last_user_message(store, session_id: str):
    from agent.context_compressor import _content_text_for_contains, is_user_originated_turn
    for message in reversed(store.messages.read_conversation(session_id)):
        row = message.as_openai_message()
        if row.get("role") == "user" and is_user_originated_turn(row):
            text = _content_text_for_contains(row.get("content")).strip()
            if text and not text.startswith("/"):
                return text
    return None


class GatewayPinCommandsMixin:
    """/pin, /pins, /unpin."""

    async def _pin_session(self, event: MessageEvent):
        """``(store, session_id)`` for the event's session, creating its row when only the session store has it."""
        source = event.source
        session_entry = await self.async_session_store.get_or_create_session(source)
        store = getattr(self, "persistence", None)
        if store is None:
            return None, session_entry.session_id
        from persistence.conversation.sessions import NewSession
        if await store.aio.sessions.get(session_entry.session_id) is None:
            with contextlib.suppress(Exception):  # may already exist
                await store.aio.sessions.create(NewSession(
                    session_id=session_entry.session_id,
                    source=source.platform.value if source.platform else "unknown",
                    user_id=source.user_id, chat_id=source.chat_id, chat_type=source.chat_type,
                    thread_id=source.thread_id))
        return store, session_entry.session_id

    async def _handle_pin_command(self, event: MessageEvent) -> str:
        from agent import pins
        store, session_id = await self._pin_session(event)
        if store is None:
            return self._session_db_unavailable_reply()
        arg = event.get_command_args().strip()
        try:
            words = arg.split(None, 2)
            if words and words[0].lower() == "patch":
                number = _number(words[1]) if len(words) > 1 else None
                if number is None or len(words) < 3:
                    return _USAGE
                await asyncio.to_thread(pins.patch_pin, store.sessions, session_id, number, words[2],
                                        origin=pins.USER_ORIGIN)
                return f"Pin {number} updated."
            text = arg or await asyncio.to_thread(_last_user_message, store, session_id)
            if not text:
                return "Nothing to pin: send a message first, or use /pin <text>."
            number = await asyncio.to_thread(pins.add_pin, store.sessions, session_id, text, origin=pins.USER_ORIGIN)
        except pins.PinRefused as refused:
            return str(refused)
        return f"Pinned as #{number}. Every compaction summary will carry it verbatim. /pins lists them."

    async def _handle_pins_command(self, event: MessageEvent) -> str:
        from agent import pins
        store, session_id = await self._pin_session(event)
        if store is None:
            return self._session_db_unavailable_reply()
        current = await asyncio.to_thread(pins.list_pins, store.sessions, session_id)
        if not current:
            return "No pins. /pin <text> adds one."
        lines = [f"{index}. {text}" for index, text in enumerate(current, 1)]
        return f"Pins ({len(current)}/{pins.MAX_PINS}):\n" + "\n".join(lines)

    async def _handle_unpin_command(self, event: MessageEvent) -> str:
        from agent import pins
        store, session_id = await self._pin_session(event)
        if store is None:
            return self._session_db_unavailable_reply()
        number = _number(event.get_command_args().strip())
        if number is None:
            return "Usage: /unpin <n> (see /pins for the numbers)."
        try:
            removed = await asyncio.to_thread(pins.remove_pin, store.sessions, session_id, number,
                                              origin=pins.USER_ORIGIN)
        except pins.PinRefused as refused:
            return str(refused)
        return f"Removed pin {number}: {removed}"
