"""The main-model compression retry must not reach the failed auxiliary endpoint (#113322, #130895).

Headline case: ``auxiliary.compression`` pins a ``base_url`` while its provider is blank or equal to
the main provider. The main runtime has no ``base_url`` of its own, so a retry that inherits the
task's endpoint sends the MAIN credential to the auxiliary host. Config is a real ``config.yaml``
in the sandboxed ``HERMES_HOME`` and the retry route comes from the real compressor fallback, so
nothing here depends on how the fix marks the route.
"""

from __future__ import annotations

import json
from typing import NamedTuple
from unittest.mock import patch

import hermes_yaml as yaml
import httpx
import pytest

from agent.auxiliary_client import (
    _reset_aux_unhealthy_cache,
    _resolve_task_provider_model,
    shutdown_cached_clients,
)
from agent.context_compressor import ContextCompressor

AUX_HOST = "aux.invalid"
AUX_BASE_URL = f"https://{AUX_HOST}/v1"
MAIN_PROVIDER = "openrouter"


class _Sent(NamedTuple):
    host: str
    authorization: str
    model: str


def _write_compression_config(home, *, provider: str, api_key: str) -> None:
    compression = {"provider": provider, "model": "aux-model", "base_url": AUX_BASE_URL}
    if api_key:
        compression["api_key"] = api_key
    (home / "config.yaml").write_text(
        yaml.safe_dump({"auxiliary": {"compression": compression}}), encoding="utf-8",
    )


def _compressor() -> ContextCompressor:
    with patch("agent.context_compressor.get_model_context_length", return_value=100_000):
        return ContextCompressor(
            model="main-model",
            provider=MAIN_PROVIDER,
            api_key="main-key",
            quiet_mode=True,
            summary_model_override="aux-model",
        )


@pytest.fixture
def hermes_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def sent_requests():
    """Every HTTP request the auxiliary clients would put on the wire, answered in-process.

    The auxiliary host truncates its summary (``finish_reason=length``), which is what sends the
    compressor to the main model; any other host returns a complete summary.
    """
    sent: list[_Sent] = []

    def _answer(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        sent.append(_Sent(request.url.host, request.headers.get("authorization", ""), payload.get("model", "")))
        from_aux = request.url.host == AUX_HOST
        choice = {
            "index": 0,
            "message": {"role": "assistant", "content": "partial" if from_aux else "complete summary via main"},
            "finish_reason": "length" if from_aux else "stop",
        }
        body = {
            "id": "chatcmpl-test", "created": 1, "model": payload.get("model"), "object": "chat.completion",
            "choices": [choice], "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        if not payload.get("stream"):
            return httpx.Response(200, json=body)
        body["object"] = "chat.completion.chunk"
        choice["delta"] = choice.pop("message")
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"},
            content=f"data: {json.dumps(body)}\n\ndata: [DONE]\n\n".encode(),
        )

    def _http_client(*_args, **_kwargs) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(_answer))

    shutdown_cached_clients()
    _reset_aux_unhealthy_cache()
    with patch("agent.process_bootstrap.build_keepalive_http_client", side_effect=_http_client):
        yield sent
    shutdown_cached_clients()


@pytest.mark.parametrize("aux_provider", ["", MAIN_PROVIDER], ids=["blank-provider", "main-provider"])
@pytest.mark.parametrize("aux_api_key", ["aux-key", ""], ids=["aux-key", "keyless"])
def test_main_fallback_route_does_not_resolve_to_the_auxiliary_endpoint(hermes_home, aux_provider, aux_api_key):
    _write_compression_config(hermes_home, provider=aux_provider, api_key=aux_api_key)
    compressor = _compressor()
    compressor._fallback_to_main_for_compression(RuntimeError("truncated"), "returned a truncated summary")
    route = {"task": "compression"}
    compressor._apply_summary_route(route)

    provider, model, base_url, api_key, _api_mode = _resolve_task_provider_model(
        route["task"], route.get("provider"), route.get("model"), route.get("base_url"), route.get("api_key"),
    )

    assert (provider, model, api_key) == (MAIN_PROVIDER, "main-model", "main-key")
    assert base_url is None


@pytest.mark.parametrize("aux_provider", ["", MAIN_PROVIDER], ids=["blank-provider", "main-provider"])
def test_truncated_auxiliary_summary_retries_on_the_main_endpoint_with_the_main_key(
    hermes_home, sent_requests, aux_provider,
):
    _write_compression_config(hermes_home, provider=aux_provider, api_key="aux-key")

    summary = _compressor()._generate_summary([
        {"role": "user", "content": "preserve this task"},
        {"role": "assistant", "content": "working on it"},
    ])

    assert [request for request in sent_requests if request.host == AUX_HOST and "main-key" in request.authorization] == []
    assert sent_requests[0] == _Sent(AUX_HOST, "Bearer aux-key", "aux-model")
    main_attempts = [request for request in sent_requests if request.model == "main-model"]
    assert len(main_attempts) == 1
    assert main_attempts[0].authorization == "Bearer main-key"
    assert main_attempts[0].host != AUX_HOST
    assert summary is not None and "complete summary via main" in summary
