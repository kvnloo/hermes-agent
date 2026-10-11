"""Regression for #135921 / #135922: public one-shot text survives its session.

Only iLink is substituted by a loopback HTTP service. Adapter connection,
public selection, aiohttp sessions, cross-thread hold, and inbound dispatch
are real. Observers delegate to the original session factory and hold method.
This covers in-memory one-shot text, not durable finals, media, or TTL policy.
"""

import asyncio
import threading

from aiohttp import web

from gateway.config import PlatformConfig
from gateway.platforms import weixin


class LoopbackILink:
    def __init__(self):
        self.window_open = False
        self.attempts = []
        self.delivered = []
        self.order = []
        self.release_poll = asyncio.Event()

    async def handle(self, request):
        payload = await request.json()
        if request.path == "/" + weixin.EP_GET_UPDATES:
            await self.release_poll.wait()
            return web.json_response({"ret": 0, "msgs": []})
        if request.path == "/" + weixin.EP_GET_CONFIG:
            return web.json_response({"ret": 0, "typing_ticket": "synthetic-ticket"})
        if request.path == "/" + weixin.EP_SEND_TYPING:
            return web.json_response({"ret": 0})
        assert request.path == "/" + weixin.EP_SEND_MESSAGE
        message = payload["msg"]
        assert request.headers["Authorization"] == "Bearer synthetic-hold-token"
        self.attempts.append(message)
        if not self.window_open:
            return web.json_response({"ret": -2, "errmsg": "prepare failed"})
        self.delivered.append(message)
        self.order.append("held-send")
        return web.json_response({"ret": 0})


def test_public_cross_loop_hold_survives_session_and_flushes_before_dispatch(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    asyncio.run(_exercise_cross_loop_hold(monkeypatch))


async def _exercise_cross_loop_hold(monkeypatch):
    owner_loop = asyncio.get_running_loop()
    owner_thread = threading.get_ident()
    bridge = LoopbackILink()
    app = web.Application()
    app.router.add_post("/{tail:.*}", bridge.handle)
    runner = web.AppRunner(app, shutdown_timeout=1)
    await runner.setup()
    live = None
    sessions = []
    real_new_session = weixin._new_session

    def observe_session(**kwargs):
        session = real_new_session(**kwargs)
        sessions.append((session, asyncio.get_running_loop(), threading.get_ident()))
        return session

    monkeypatch.setattr(weixin, "_new_session", observe_session)
    try:
        # A bind failure is a setup failure; it must never become a skip/pass.
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        peer = "synthetic-peer"
        text = "Synthetic scheduled report"
        extra = {
            "account_id": "synthetic-account",
            "base_url": url,
            "cdn_base_url": url,
            "dm_policy": "allowlist",
            "allow_from": [peer],
            "group_allow_from": [],
            "group_policy": "disabled",
            "send_chunk_retries": 0,
            "send_chunk_delay_seconds": 0,
            "text_batch_delay_seconds": 0,
            "text_batch_split_delay_seconds": 0,
        }
        live = weixin.WeixinAdapter(PlatformConfig(
            enabled=True, token="synthetic-hold-token", extra=extra,
        ))
        hold_ran = asyncio.Event()
        hold_locations = []
        real_hold = getattr(live, "_hold_outbound_text", None)

        def observe_hold(*args, **kwargs):
            hold_locations.append((asyncio.get_running_loop(), threading.get_ident()))
            depth = real_hold(*args, **kwargs)
            hold_ran.set()
            return depth

        # The same fixture can run on the pre-hold base: fail on behavior,
        # rather than requiring a method that did not yet exist.
        if real_hold is not None:
            monkeypatch.setattr(live, "_hold_outbound_text", observe_hold)
        dispatched = asyncio.Queue()

        async def inbound_handler(event):
            bridge.order.append("inbound-dispatch")
            await dispatched.put((event.text, list(bridge.delivered)))
            return None

        live.set_message_handler(inbound_handler)
        assert await live.connect()
        assert weixin._LIVE_ADAPTERS[live._token] is live
        assert live._send_session._loop is owner_loop
        await live._token_store.set(live._account_id, peer, "synthetic-old-context")

        def call_from_worker():
            async def send():
                assert asyncio.get_running_loop() is not owner_loop
                assert threading.get_ident() != owner_thread
                return await weixin.send_weixin_direct(
                    extra=extra, token="synthetic-hold-token", chat_id=peer, message=text,
                )
            return asyncio.run(send())

        result = await asyncio.wait_for(asyncio.to_thread(call_from_worker), 30)
        assert result.get("success") is True, result
        assert result.get("queued") is True, result
        await asyncio.wait_for(hold_ran.wait(), 10)
        assert hold_locations == [(owner_loop, owner_thread)]
        assert len(sessions) == 3  # live poll/send on A; disposable send on B
        temporary, worker_loop, worker_thread = sessions[-1]
        assert worker_loop is not owner_loop and worker_thread != owner_thread
        assert temporary._loop is worker_loop and temporary.closed
        assert worker_loop.is_closed()
        assert not live._send_session.closed
        assert [chunks for _, chunks in live._held_outbound[peer]] == [[text]]
        assert bridge.delivered == []
        assert [m.get("context_token") for m in bridge.attempts] == [
            "synthetic-old-context", None,
        ]

        bridge.window_open = True
        inbound = {
            "from_user_id": peer, "to_user_id": live._account_id,
            "message_id": "synthetic-inbound-1", "context_token": "synthetic-fresh-context",
            "item_list": [{"type": weixin.ITEM_TEXT, "text_item": {"text": "Resume please"}}],
        }
        assert live._is_dm_allowed(peer)
        await live._process_message(inbound)
        inbound_text, deliveries_at_dispatch = await asyncio.wait_for(dispatched.get(), 10)
        assert inbound_text == "Resume please"
        assert len(deliveries_at_dispatch) == 1
        sent = deliveries_at_dispatch[0]
        assert sent["to_user_id"] == peer
        assert sent["item_list"] == [{"type": weixin.ITEM_TEXT, "text_item": {"text": text}}]
        assert sent["context_token"] == "synthetic-fresh-context"
        assert bridge.order == ["held-send", "inbound-dispatch"]
        assert peer not in live._held_outbound

        # A distinct authorized inbound must not flush the held report again.
        await live._process_message({
            **inbound, "message_id": "synthetic-inbound-2",
            "context_token": "synthetic-next-context",
            "item_list": [{"type": weixin.ITEM_TEXT, "text_item": {"text": "Next question"}}],
        })
        next_text, next_deliveries = await asyncio.wait_for(dispatched.get(), 10)
        assert next_text == "Next question"
        assert next_deliveries == deliveries_at_dispatch
        assert len(bridge.attempts) == 3
        assert bridge.order == ["held-send", "inbound-dispatch", "inbound-dispatch"]
        # Handler observation precedes the base adapter's finally/typing cleanup.
        await asyncio.wait_for(asyncio.gather(*live._session_tasks.values()), 10)
    finally:
        if live is not None:
            await live.disconnect()
        bridge.release_poll.set()
        await runner.cleanup()
        assert all(session.closed for session, _, _ in sessions)
