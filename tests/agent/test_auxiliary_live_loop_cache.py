"""A live auxiliary request must survive a foreign worker-loop cache miss.

Regression for NousResearch/hermes-agent#137365. Uses a real AsyncOpenAI transport
with an offline httpx response so it exercises the SDK's closed-client behavior.
"""

import asyncio
import threading
from unittest.mock import patch

import httpx
from openai import AsyncOpenAI

from agent import auxiliary_client as aux


def test_inflight_auxiliary_request_survives_foreign_loop_cache_miss():
    owner_ready = threading.Event()
    other_done = threading.Event()
    responses = []
    errors = []
    observed_requests = []

    def _http_response(request):
        observed_requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": "m1",
                "choices": [{
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "alive"},
                }],
            },
        )

    def _resolve(_provider, model, async_mode, **_kwargs):
        assert async_mode
        transport = httpx.MockTransport(_http_response)
        client = AsyncOpenAI(
            api_key="sk-test",
            base_url="http://localhost:8081/v1",
            http_client=httpx.AsyncClient(transport=transport),
        )
        return client, model or "m1"

    def _get():
        return aux._get_cached_client(
            "custom", "m1", async_mode=True,
            base_url="http://localhost:8081/v1", is_vision=True,
        )[0]

    async def _owner_request():
        client = _get()
        owner_ready.set()
        try:
            await asyncio.to_thread(other_done.wait)
            completion = await client.chat.completions.create(
                model="m1", messages=[{"role": "user", "content": "ping"}],
            )
            responses.append(completion.choices[0].message.content)
        finally:
            await client.close()

    def _run_owner():
        try:
            asyncio.run(_owner_request())
        except Exception as exc:
            errors.append(exc)

    async def _other_lookup():
        client = _get()
        await client.close()

    with aux._client_cache_lock:
        original_cache = dict(aux._client_cache)
        aux._client_cache.clear()
    owner = threading.Thread(target=_run_owner)
    try:
        with patch.object(aux, "resolve_provider_client", side_effect=_resolve):
            owner.start()
            try:
                assert owner_ready.wait(10), "owner never obtained its client"
                asyncio.run(_other_lookup())
            finally:
                other_done.set()
                owner.join(10)
        assert not owner.is_alive(), "owner loop did not exit"
        assert not errors, f"owner request failed: {errors!r}"
        assert responses == ["alive"]
        assert len(observed_requests) == 1
    finally:
        other_done.set()
        if owner.is_alive():
            owner.join(10)
        with aux._client_cache_lock:
            aux._client_cache.clear()
            aux._client_cache.update(original_cache)
