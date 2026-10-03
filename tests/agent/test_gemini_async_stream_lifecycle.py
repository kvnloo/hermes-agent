"""Real HTTPX response cleanup through Gemini's async auxiliary consumer."""

import json

import httpx
import pytest

from agent.auxiliary_client import _aggregate_chat_stream_async
from agent.gemini_native_adapter import AsyncGeminiNativeClient, GeminiNativeClient


@pytest.mark.asyncio
@pytest.mark.parametrize("exit_mode", ["close", "deadline", "exhausted"])
async def test_async_gemini_consumer_releases_response_without_closing_client(exit_mode):
    class TrackedBody(httpx.SyncByteStream):
        def __init__(self):
            self.read_count = 0
            self.close_count = 0

        def __iter__(self):
            for text in ("first", "second"):
                self.read_count += 1
                payload = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
                yield ("data: " + json.dumps(payload) + "\n\n").encode()

        def close(self):
            self.close_count += 1

    bodies = []
    def respond(request):
        body = TrackedBody()
        bodies.append(body)
        return httpx.Response(200, stream=body, headers={"Content-Type": "text/event-stream"})

    http_client = httpx.Client(transport=httpx.MockTransport(respond))
    client = AsyncGeminiNativeClient(GeminiNativeClient(
        api_key="synthetic-test-key", base_url="https://gemini.invalid/v1beta", http_client=http_client))
    stream = await client.chat.completions.create(
        model="gemini-test", messages=[{"role": "user", "content": "fixture"}], stream=True)
    try:
        if exit_mode == "close":
            assert (await anext(stream)).choices[0].delta.content == "first"
            await stream.aclose()
        elif exit_mode == "deadline":
            with pytest.raises(TimeoutError, match="total ceiling"):
                await _aggregate_chat_stream_async(stream, total_ceiling=0)
        else:
            response = await _aggregate_chat_stream_async(stream)
            assert response.choices[0].message.content == "firstsecond"
        # Retain the async stream object: cleanup must not depend on dropping it.
        assert bodies[0].close_count == 1
        assert bodies[0].read_count == (2 if exit_mode == "exhausted" else 1)
        assert not http_client.is_closed
        later = await client.chat.completions.create(
            model="gemini-test", messages=[{"role": "user", "content": "later"}], stream=True)
        response = await _aggregate_chat_stream_async(later)
        assert response.choices[0].message.content == "firstsecond"
        assert bodies[1].close_count == 1
    finally:
        await stream.aclose()
        await client.close()
