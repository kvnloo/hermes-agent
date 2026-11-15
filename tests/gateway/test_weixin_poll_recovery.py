"""Weixin receive poll must surface repeated transport timeouts (#155978, #23523)."""

import asyncio

import pytest

from gateway.config import Platform
from plugins.platforms.weixin import adapter as weixin


@pytest.mark.asyncio
async def test_repeated_getupdates_timeouts_recycle_poll_session(monkeypatch, tmp_path, caplog):
    """Normal empty responses reset the streak; three real client timeouts recycle."""
    adapter = object.__new__(weixin.WeixinAdapter)
    adapter.platform = Platform.WEIXIN
    adapter._running = True
    adapter._poll_session = object()
    adapter._hermes_home = str(tmp_path)
    adapter._account_id = "test-bot"
    adapter._base_url = weixin.ILINK_BASE_URL
    adapter._token = "fake-token"

    limit = weixin.MAX_CONSECUTIVE_FAILURES
    polls = 0
    recycled_at = []

    async def api_post(*args, **kwargs):
        nonlocal polls
        polls += 1
        if polls < limit or limit < polls <= 2 * limit:
            raise TimeoutError("iLink transport stopped responding")
        if polls == 2 * limit + 1:
            adapter._running = False
        return {"ret": 0, "msgs": [], "get_updates_buf": ""}

    async def recycle():
        recycled_at.append(polls)

    monkeypatch.setattr(weixin, "_api_post", api_post)
    adapter._recycle_poll_session = recycle

    with caplog.at_level("WARNING", logger=weixin.__name__):
        await asyncio.wait_for(adapter._poll_loop(), timeout=3)

    assert polls == 2 * limit + 1
    assert recycled_at == [2 * limit]
    assert "getUpdates timed out" in caplog.text
