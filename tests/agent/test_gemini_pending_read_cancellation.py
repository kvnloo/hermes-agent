"""Characterize cancellation ownership while Gemini's synchronous read is in flight."""

import asyncio
import json
import threading

import httpx
import pytest

from agent.auxiliary_client import _aggregate_chat_stream_async
from agent.gemini_native_adapter import AsyncGeminiNativeClient, GeminiNativeClient


def event_bytes(text):
    return ("data: " + json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}) + "\n\n").encode()


@pytest.mark.asyncio
async def test_cancelled_consumer_returns_before_finite_read_releases_response():
    entered = threading.Event()
    release = threading.Event()
    closed = threading.Event()

    class FiniteBody(httpx.SyncByteStream):
        reading = False
        closed_while_reading = False
        close_count = 0

        def __iter__(self):
            yield event_bytes("first")
            self.reading = True
            entered.set()
            try:
                assert release.wait(5), "test read was never released"
            finally:
                self.reading = False
            yield event_bytes("second")

        def close(self):
            self.closed_while_reading |= self.reading
            self.close_count += 1
            closed.set()

    body = FiniteBody()
    def respond(request):
        if "streamGenerateContent" in request.url.path:
            return httpx.Response(200, stream=body, headers={"Content-Type": "text/event-stream"})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "reused"}]}}]})

    http_client = httpx.Client(transport=httpx.MockTransport(respond))
    client = AsyncGeminiNativeClient(GeminiNativeClient(
        api_key="synthetic-test-key", base_url="https://gemini.invalid/v1beta", http_client=http_client))
    stream = await client.chat.completions.create(
        model="gemini-test", messages=[{"role": "user", "content": "fixture"}], stream=True)
    task = asyncio.create_task(_aggregate_chat_stream_async(stream))
    try:
        assert await asyncio.to_thread(entered.wait, 2), "worker never entered the second read"
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 2)
        assert task.cancelled()
        # Owner cancellation does not interrupt the finite synchronous read or
        # close a response while that read still owns it.
        assert body.reading and body.close_count == 0
        assert not http_client.is_closed
        release.set()
        assert await asyncio.to_thread(closed.wait, 2), "response not released after read completed"
        assert body.close_count == 1 and not body.closed_while_reading
        response = await client.chat.completions.create(
            model="gemini-test", messages=[{"role": "user", "content": "later"}])
        assert response.choices[0].message.content == "reused"
    finally:
        release.set()
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await asyncio.to_thread(closed.wait, 2)
        await stream.aclose()
        await client.close()
