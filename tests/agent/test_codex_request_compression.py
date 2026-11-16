"""Codex Responses bodies go out zstd-compressed to the official backend only (official-client parity)."""

import asyncio
import json
import sys
from types import ModuleType

import pytest

from agent.process_bootstrap import build_keepalive_http_client

try:
    from compression import zstd
except ImportError:
    zstd = None

requires_zstd = pytest.mark.skipif(zstd is None, reason="stdlib zstd requires Python 3.14+")

OFFICIAL = "https://chatgpt.com/backend-api/codex"


def _send_through_hooks(client, url: str, payload: dict):
    request = client.build_request("POST", url, json=payload)
    for hook in client.event_hooks["request"]:
        hook(request)
    return request


@requires_zstd
def test_official_codex_responses_body_is_zstd_and_lossless():
    payload = {"model": "gpt-6.1-sol", "input": [{"role": "user", "content": "hi " * 500}]}
    client = build_keepalive_http_client(OFFICIAL)
    try:
        request = _send_through_hooks(client, f"{OFFICIAL}/responses", payload)
    finally:
        client.close()
    assert request.headers["Content-Encoding"] == "zstd"
    assert int(request.headers["Content-Length"]) == len(request.content)
    assert json.loads(zstd.decompress(request.content)) == payload


@pytest.mark.parametrize("base_url, path", [
    ("https://my-proxy.example.com/backend-api/codex", "/responses"),  # custom proxy: never compressed
    ("https://api.openai.com/v1", "/responses"),
    (OFFICIAL, "/models"),  # official host, non-Responses endpoint
])
def test_other_destinations_stay_raw_json(base_url, path):
    payload = {"model": "x", "input": "hello"}
    client = build_keepalive_http_client(base_url)
    try:
        request = _send_through_hooks(client, f"{base_url}{path}", payload)
    finally:
        client.close()
    assert "Content-Encoding" not in request.headers
    assert json.loads(request.content) == payload


@requires_zstd
@pytest.mark.parametrize("async_mode", [False, True], ids=["sync", "async"])
def test_codex_profile_can_disable_request_compression(tmp_path, monkeypatch, async_mode):
    """#148898: the official backend can reject zstd bytes for otherwise valid JSON."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "config.yaml").write_text(
        "agent:\n  codex_request_compression: false\n", encoding="utf-8"
    )
    client = build_keepalive_http_client(OFFICIAL, async_mode=async_mode)
    assert client is not None
    try:
        payload = {"model": "gpt-6.1-sol", "input": "hello"}
        request = client.build_request("POST", f"{OFFICIAL}/responses", json=payload)
        for hook in client.event_hooks["request"]:
            if async_mode:
                asyncio.run(hook(request))
            else:
                hook(request)
        assert "Content-Encoding" not in request.headers
        assert json.loads(request.content) == payload
    finally:
        if async_mode:
            asyncio.run(client.aclose())
        else:
            client.close()


@requires_zstd
@pytest.mark.parametrize("enabled", [False, True], ids=["disabled", "enabled"])
@pytest.mark.parametrize("async_mode", [False, True], ids=["sync", "async"])
def test_profile_setting_controls_httpx_wire_body(tmp_path, monkeypatch, enabled, async_mode):
    """Exercise config loading, client hook wiring, and HTTP dispatch without network I/O."""
    import httpx
    from agent import process_bootstrap

    monkeypatch.setattr(process_bootstrap, "_SHARED_TRANSPORTS", {})
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "config.yaml").write_text(
        f"agent:\n  codex_request_compression: {str(enabled).lower()}\n", encoding="utf-8"
    )
    payload = {"model": "test-model", "input": "hello"}
    seen = []

    def receive(request):
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    # Replace only the network transport. Keep the builder's real hooks and dispatch.
    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kwargs: httpx.MockTransport(receive))
    monkeypatch.setattr(httpx, "AsyncHTTPTransport", lambda **kwargs: httpx.MockTransport(receive))
    client = build_keepalive_http_client(OFFICIAL, async_mode=async_mode)
    assert client is not None
    if async_mode:
        async def send():
            async with client:
                return await client.post(f"{OFFICIAL}/responses", json=payload)
        response = asyncio.run(send())
    else:
        with client:
            response = client.post(f"{OFFICIAL}/responses", json=payload)
    assert response.status_code == 200
    assert len(seen) == 1
    request = seen[0]
    if enabled:
        assert request.headers["Content-Encoding"] == "zstd"
        assert int(request.headers["Content-Length"]) == len(request.content)
        assert json.loads(zstd.decompress(request.content)) == payload
    else:
        assert "Content-Encoding" not in request.headers
        assert json.loads(request.content) == payload


@pytest.mark.parametrize("async_mode", [False, True], ids=["sync", "async"])
def test_disabled_profile_installs_no_compression_hook(tmp_path, monkeypatch, async_mode):
    """The opt-out must prevent hook installation even on older Python runtimes."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "config.yaml").write_text(
        "agent:\n  codex_request_compression: false\n", encoding="utf-8"
    )
    # Expose codec availability without executing a replacement codec.
    compression = ModuleType("compression")
    compression.zstd = object()
    monkeypatch.setitem(sys.modules, "compression", compression)
    client = build_keepalive_http_client(OFFICIAL, async_mode=async_mode)
    assert client is not None
    try:
        assert client.event_hooks["request"] == []
    finally:
        if async_mode:
            asyncio.run(client.aclose())
        else:
            client.close()
