#!/usr/bin/env python3
"""WebSocket-capable host-rewrite proxy for the isolated voice dashboard."""
import asyncio
from aiohttp import ClientSession, ClientTimeout, WSMsgType, web

UPSTREAM_HTTP = "http://127.0.0.1:9166"
UPSTREAM_WS = "ws://127.0.0.1:9166"
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"}

def headers(request):
    result = {k: v for k, v in request.headers.items() if k.lower() not in HOP | {"host", "origin", "content-length"}}
    result.update({"Host": "127.0.0.1:9166", "Origin": UPSTREAM_HTTP, "X-Forwarded-Host": request.host, "X-Forwarded-Proto": "https"})
    return result

async def proxy(request):
    session = request.app["client"]
    if request.headers.get("Upgrade", "").lower() == "websocket":
        downstream = web.WebSocketResponse(heartbeat=30)
        await downstream.prepare(request)
        async with session.ws_connect(f"{UPSTREAM_WS}{request.rel_url}", headers=headers(request), heartbeat=30) as upstream:
            async def relay(source, target):
                async for message in source:
                    if message.type == WSMsgType.TEXT: await target.send_str(message.data)
                    elif message.type == WSMsgType.BINARY: await target.send_bytes(message.data)
            tasks = [asyncio.create_task(relay(downstream, upstream)), asyncio.create_task(relay(upstream, downstream))]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending: task.cancel()
            await asyncio.gather(*done, *pending, return_exceptions=True)
        return downstream
    async with session.request(request.method, f"{UPSTREAM_HTTP}{request.rel_url}", headers=headers(request), data=await request.read() or None, allow_redirects=False) as response:
        return web.Response(status=response.status, body=await response.read(), headers={k: v for k, v in response.headers.items() if k.lower() not in HOP | {"content-length"}})

async def client(app):
    app["client"] = ClientSession(timeout=ClientTimeout(total=None, connect=10, sock_read=None))
    yield
    await app["client"].close()

app = web.Application(client_max_size=64 * 1024 * 1024)
app.cleanup_ctx.append(client)
app.router.add_route("*", "/{tail:.*}", proxy)
web.run_app(app, host="127.0.0.1", port=9167, access_log=None)
