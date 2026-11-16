"""Local metadata probes bypass inherited proxies. Hosted probes keep proxy support.

Regression for NousResearch/hermes-agent#148849, reported by YusenZhang0601.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import httpx
import pytest

from agent import model_metadata, model_metadata_http


@pytest.fixture
def servers():
    active = []

    def start(handler):
        server = ThreadingHTTPServer(("localhost", 0), handler)
        server.daemon_threads = True
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        active.append((server, thread))
        return f"http://{server.server_address[0]}:{server.server_port}"

    yield start
    for server, thread in reversed(active):
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize(
    "base_url,expected",
    [
        (f"http://{model_metadata._TAILSCALE_CGNAT.network_address + 1}:8080/v1", False),
        (f"http://{model_metadata._TAILSCALE_CGNAT.broadcast_address}:8080/v1", False),
        ("http://host.docker.internal:8080/v1", False),
        ("http://ollama:11434", False),
        ("http://engine.local:8080/v1", False),
        ("http://localhost:8080/v1", False),
        ("http://ollama-box.local:11434", False),  # mDNS
        ("https://api.openai.com/v1", True),  # hosted: keep the environment proxy
        ("https://openrouter.ai/api/v1", True),
        ("", True),  # unknown target: leave the caller's default behaviour alone
    ],
)
def test_probe_trust_env_policy(base_url, expected):
    assert model_metadata._probe_trust_env(base_url) is expected


@pytest.fixture
def dead_proxy(monkeypatch):
    """Reserve a port without listening so no other process can claim the proxy port."""
    import socket

    with socket.socket() as probe:
        probe.bind(("localhost", 0))
        proxy_url = f"http://localhost:{probe.getsockname()[1]}"
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
            monkeypatch.setenv(name, proxy_url)
            monkeypatch.setenv(name.lower(), proxy_url)
        monkeypatch.setenv("NO_PROXY", "")
        monkeypatch.setenv("no_proxy", "")
        yield


@pytest.mark.parametrize("engine", ["openai", "ollama"])
def test_local_probe_succeeds_while_http_proxy_is_set_to_a_dead_port(
    servers, monkeypatch, dead_proxy, engine
):
    """Exercise detection, generic context lookup, and Ollama show through real sockets."""
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(self.path)
            assert engine == "ollama" and self.path == "/api/show"
            body = b'{"model_info":{"llama.context_length":262144}}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            requests.append(self.path)
            if engine == "ollama" and self.path == "/api/tags":
                body = b'{"models":[]}'
            elif engine == "openai" and self.path == "/v1/models":
                body = b'{"data":[{"id":"qwen-local","meta":{"n_ctx":262144}}]}'
            else:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # signature required by BaseHTTPRequestHandler
            pass

    base_url = servers(Handler)
    monkeypatch.setattr(model_metadata, "_endpoint_probe_path_cache", {})
    monkeypatch.setattr(model_metadata, "_endpoint_blackhole_cache", {})
    monkeypatch.setattr(model_metadata, "_LOCAL_CTX_PROBE_CACHE", {})
    monkeypatch.setattr(model_metadata, "_local_probe_disk_get", lambda *a, **k: None)
    monkeypatch.setattr(model_metadata, "_local_probe_disk_put", lambda *a, **k: None)

    expected_type = "ollama" if engine == "ollama" else None
    assert model_metadata.detect_local_server_type(base_url) == expected_type
    assert model_metadata._query_local_context_length("qwen-local", base_url) == 262144
    if engine == "ollama":
        assert model_metadata.query_ollama_num_ctx("qwen-local", base_url) == 262144
    assert ("/api/show" if engine == "ollama" else "/v1/models") in requests


def test_hosted_probe_still_trusts_the_environment(monkeypatch):
    seen = []

    class RecordingClient:
        def __init__(self, **kwargs):
            seen.append(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, *a, **k):
            raise httpx.ConnectTimeout("stop after the kwargs assertion")

    monkeypatch.setattr(httpx, "Client", RecordingClient)
    monkeypatch.setattr(model_metadata, "_endpoint_probe_path_cache", {})
    monkeypatch.setattr(model_metadata, "_endpoint_blackholed", lambda url: False)
    monkeypatch.setattr(model_metadata, "_local_probe_disk_get", lambda *a, **k: None)

    # A non-registry domain is not skipped as a hosted provider, so the waterfall
    # actually builds a client and the kwarg is observable.
    model_metadata.detect_local_server_type("https://engine.example.invalid/v1")
    assert seen and seen[-1]["trust_env"] is True

    seen.clear()
    model_metadata.detect_local_server_type("http://engine.local:8080/v1")
    assert seen and seen[-1]["trust_env"] is False


def test_metadata_http_layer_applies_the_same_policy(servers, dead_proxy):
    """``model_metadata_http.get`` is how llama.cpp ``/props`` is read; same rule, same bug.

    ``NO_PROXY`` is left empty here to isolate the mechanism: on the reporting machine the list is
    full of CIDR ranges httpx cannot match, which is the equivalent of no usable bypass entry.
    """
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/v1/props"):
                body = b'{"default_generation_settings":{"n_ctx":262144}}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, format, *args):  # signature required by BaseHTTPRequestHandler
            pass

    base_url = servers(Handler)

    assert model_metadata_http.get(f"{base_url}/v1/props", timeout=5).status_code == 200
    # A hosted destination must still be routed through the configured proxy: the fix is about
    # local engines, not about switching proxy support off.
    with pytest.raises(httpx.TransportError):
        model_metadata_http.get("http://probe.invalid/models", timeout=2)
