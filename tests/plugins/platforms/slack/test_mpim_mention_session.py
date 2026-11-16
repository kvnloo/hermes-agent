"""A Slack MPIM app_mention shares a session with its paired message (#156521)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.slack.adapter import SlackAdapter


@pytest.mark.asyncio
@pytest.mark.parametrize("channel_id", ["C_MPIM", "G_MPIM"])
@pytest.mark.parametrize("first_type", ["app_mention", "message"])
async def test_mpim_mention_and_message_share_dm_session(channel_id, first_type):
    adapter = SlackAdapter(PlatformConfig(enabled=True, token="xoxb-fake-token"))
    adapter._app = MagicMock()
    adapter._app.client = AsyncMock()
    adapter._app.client.conversations_info.return_value = {
        "ok": True, "channel": {"id": channel_id, "is_mpim": True, "name": "group-dm"}}
    adapter._app.client.users_info.return_value = {
        "ok": True, "user": {"is_bot": False, "real_name": "Alice"}}
    adapter._bot_user_id = "U_BOT"
    adapter._running = True
    adapter.handle_message = AsyncMock()

    common = {
        "channel": channel_id, "user": "U_ALICE", "text": "<@U_BOT> remember",
        "ts": "1700000000.000002", "thread_ts": "1700000000.000001",
    }
    message = {**common, "type": "message", "channel_type": "mpim", "client_msg_id": "client-1"}
    mention = {**common, "type": "app_mention"}  # Slack omits channel_type.
    events = (mention, message) if first_type == "app_mention" else (message, mention)
    for event in events:
        await adapter._handle_slack_message(event, {"team_id": "T1"})

    assert adapter.handle_message.await_count == 1
    source = adapter.handle_message.await_args.args[0].source
    assert source.chat_type == "dm"
    assert source.chat_id == channel_id
    assert source.thread_id == common["thread_ts"]
