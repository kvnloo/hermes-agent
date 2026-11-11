"""/resume across topic lanes of ONE Telegram private chat (maintainer ruling on #57821).

The same person's own DM may move a conversation between its topics; every other chat keeps the
strict thread scoping of the /resume IDOR guard (other private chat, group/forum topics).
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import Platform
from gateway.platforms.event import MessageEvent
from gateway.session import SessionSource, build_session_key
from hermes_state import AsyncSessionDB, SessionDB


def _src(chat_id="67890", user_id="12345", thread_id="topic-b", chat_type="dm"):
    return SessionSource(platform=Platform.TELEGRAM, chat_id=chat_id, user_id=user_id,
                         chat_type=chat_type, thread_id=thread_id, user_name="tester")


def _runner(db, source):
    from gateway.run import GatewayRunner
    runner = object.__new__(GatewayRunner)
    runner.adapters = {}
    runner.config = SimpleNamespace(platforms={})
    runner._voice_mode = {}
    runner._session_db = AsyncSessionDB(db)
    runner._running_agents = {}
    runner._is_user_authorized = lambda _source: True
    entry = MagicMock(session_id="current", session_key=build_session_key(source))
    runner.session_store = MagicMock()
    runner._async_session_store = SimpleNamespace(
        _store=runner.session_store, get_or_create_session=AsyncMock(return_value=entry),
        load_transcript=AsyncMock(return_value=[]), switch_session=AsyncMock(return_value=entry),
        set_model_override=AsyncMock())
    runner._gateway_session_origin_for_id = lambda _sid: None
    return runner


def _row(db, sid, title, **origin):
    src = _src(**origin)
    db.create_session(sid, "telegram", user_id=src.user_id, chat_id=src.chat_id,
                      chat_type=src.chat_type, thread_id=src.thread_id, session_key=build_session_key(src))
    db.set_session_title(sid, title)


@pytest.mark.asyncio
async def test_resume_from_another_topic_of_the_same_private_chat_switches(tmp_path):
    db = SessionDB(db_path=tmp_path / "state.db")
    _row(db, "topic_a_work", "Topic A Work", thread_id="topic-a")
    caller = _src(thread_id="topic-b")
    runner = _runner(db, caller)

    reply = await runner._handle_resume_command(MessageEvent(text="/resume Topic A Work", source=caller))

    assert "Topic A Work" in reply and "Resumed" in reply
    runner.async_session_store.switch_session.assert_awaited_once()
    assert runner.async_session_store.switch_session.await_args.args[1] == "topic_a_work"
    # A live target (its origin in the store) is judged the same way as the persisted row.
    assert runner._same_origin_chat(caller, _src(thread_id="topic-a")) is True
    db.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("origin", [
    {"chat_id": "99999", "user_id": "99999", "thread_id": "topic-a"},           # another private chat
    {"chat_id": "-1001", "chat_type": "group", "thread_id": "topic-a"},         # forum topic, same user
])
async def test_resume_across_threads_stays_refused_outside_the_callers_own_dm(tmp_path, origin):
    db = SessionDB(db_path=tmp_path / "state.db")
    _row(db, "foreign", "Foreign Work", **origin)
    caller_kind = {"chat_id": origin["chat_id"], "chat_type": "group"} if origin.get("chat_type") else {}
    caller = _src(thread_id="topic-b", **caller_kind)
    runner = _runner(db, caller)

    await runner._handle_resume_command(MessageEvent(text="/resume Foreign Work", source=caller))

    runner.async_session_store.switch_session.assert_not_awaited()
    assert runner._same_origin_chat(caller, _src(**origin)) is False  # live-origin path agrees
    db.close()

@pytest.mark.asyncio
async def test_resume_dm_topic_does_not_cross_telegram_bots_sharing_a_runtime(tmp_path):
    """One Telegram user has the same private chat ID with two different bot credentials."""
    from gateway.session_identity import RoutingIdentity, transport_profile_of

    home = tmp_path / "shared-runtime"
    db = SessionDB(db_path=tmp_path / "state.db")
    original = _src(thread_id="topic-a")
    caller = _src(thread_id="topic-b")
    for source, bot in ((original, "alpha"), (caller, "beta")):
        source._identity = RoutingIdentity(
            transport_profile=bot, runtime_profile="shared",
            authorization_home=home, runtime_home=home, multiplexed=True)

    db.create_session(
        "alpha_work", "telegram", user_id=original.user_id, chat_id=original.chat_id,
        chat_type=original.chat_type, thread_id=original.thread_id,
        transport_profile="alpha", session_key=build_session_key(original, profile="shared"))
    db.set_session_title("alpha_work", "Alpha Work")
    runner = _runner(db, caller)
    runner._recover_telegram_topic_thread_id = lambda _source: "topic-b"

    # Lobby-topic normalization must not erase the authenticated receiving bot.
    normalized = runner._normalize_source_for_session_key(caller)
    assert normalized is not caller
    assert transport_profile_of(normalized) == "beta"

    # Both ownership paths must refuse a different bot despite identical chat/user ids.
    row = db.get_session("alpha_work")
    assert runner._same_origin_chat(caller, original) is False
    assert runner._persisted_row_proves_owner(caller, row) is False
    reply = await runner._handle_resume_command(
        MessageEvent(text="/resume Alpha Work", source=caller))
    assert "belongs to a different user or chat" in reply
    runner.async_session_store.switch_session.assert_not_awaited()

    # A different topic in the SAME receiving bot remains resumable.
    caller._identity = RoutingIdentity(
        transport_profile="alpha", runtime_profile="shared",
        authorization_home=home, runtime_home=home, multiplexed=True)
    assert runner._same_origin_chat(caller, original) is True
    assert runner._persisted_row_proves_owner(caller, row) is True
    db.close()
