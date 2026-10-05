"""Same-provider recovery keeps the real async streaming/progress boundary (#92193)."""

import json

import httpx
import pytest
from openai import AsyncOpenAI

from agent import auxiliary_client as ac


@pytest.mark.asyncio
@pytest.mark.parametrize("force_stream", [False, True])
async def test_async_retry_dispatches_and_reports_stream_progress(tmp_path, monkeypatch, force_stream):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    (home / "config.yaml").write_text(
        "auxiliary:\n  stream_only_base_urls: " + ("[retry.invalid]" if force_stream else "[]") + "\n",
        encoding="utf-8",
    )
    requests, progress, dispatches = [], [], []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        if not body.get("stream"):
            return httpx.Response(200, json={
                "id": "reply", "object": "chat.completion", "created": 1, "model": "synthetic-model",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ready"}, "finish_reason": "stop"}],
            })
        chunks = [
            {"id": "reply", "object": "chat.completion.chunk", "created": 1, "model": "synthetic-model",
             "choices": [{"index": 0, "delta": {"content": "ready"}, "finish_reason": None}]},
            {"id": "reply", "object": "chat.completion.chunk", "created": 1, "model": "synthetic-model",
             "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
        ]
        data = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=data)

    client = AsyncOpenAI(api_key="synthetic-key", base_url="https://retry.invalid/v1", max_retries=0,
                         http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    monkeypatch.setattr(ac, "_get_cached_client", lambda *args, **kwargs: (client, "synthetic-model"))
    try:
        with ac.aux_progress_hook(None if force_stream else lambda: progress.append(True)), ac._aux_thread_local_hook(
            ac._aux_dispatch, lambda: dispatches.append(True),
        ):
            response = await ac._retry_same_provider_async(
                task="compression", resolved_provider="custom", resolved_model="synthetic-model",
                resolved_base_url="https://retry.invalid/v1", resolved_api_key="synthetic-key",
                resolved_api_mode="chat_completions", main_runtime=None, final_model="synthetic-model",
                messages=[{"role": "user", "content": "synthetic request"}], temperature=None,
                max_tokens=None, tools=None, effective_timeout=10.0, effective_extra_body={}, reasoning_config=None,
            )
        assert len(requests) == 1
        assert requests[0].get("stream") is True
        assert dispatches == [True]
        if not force_stream:
            assert progress
        assert response.choices[0].message.content == "ready"
    finally:
        await client.close()
