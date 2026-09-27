"""Slack file downloads are capped by the inbound media limit (no OOM on huge files)."""
import asyncio
import socket
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest


if "slack_bolt" not in sys.modules:
    for name in (
        "slack_bolt", "slack_bolt.adapter", "slack_bolt.adapter.socket_mode",
        "slack_bolt.adapter.socket_mode.async_handler", "slack_bolt.async_app",
        "slack_sdk", "slack_sdk.web", "slack_sdk.web.async_client", "slack_sdk.errors",
    ):
        sys.modules.setdefault(name, MagicMock())
if "aiohttp" not in sys.modules:
    sys.modules.setdefault("aiohttp", MagicMock())

import gateway.platforms.base as platform_base  # noqa: E402
from gateway.config import PlatformConfig  # noqa: E402
from plugins.platforms.slack.adapter import SlackAdapter  # noqa: E402


START = "https://files.slack.com/files-pri/TSECOND-F123/image.png"
TOKEN = "xoxb-second-team-token"


@pytest.fixture
def adapter(monkeypatch):
    adapter = SlackAdapter.__new__(SlackAdapter)
    adapter.config = PlatformConfig(token="primary-test-token")
    adapter._team_clients = {"TSECOND": SimpleNamespace(token=TOKEN)}
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (
            "169.254.169.254" if host == "169.254.169.254" else "93.184.216.34", 443)),
    ])
    # Shrink the inbound media cap so the tests don't allocate megabytes.
    monkeypatch.setattr(platform_base, "get_inbound_media_max_bytes", lambda: 64)
    return adapter


@pytest.fixture
def install_transport(monkeypatch):
    def install(handler):
        def client(**kwargs):
            return httpx.AsyncClient(**kwargs, transport=httpx.MockTransport(handler), trust_env=False)
        monkeypatch.setattr("tools.url_safety.create_ssrf_safe_async_client", client)
    return install


def test_oversized_declared_content_length_rejected(adapter, install_transport):
    """A lying Content-Length above the cap fails before any body bytes are kept."""
    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "image/png", "content-length": "65"},
            content=b"\x89PNG\r\n\x1a\ntiny",
        )
    install_transport(handler)
    with pytest.raises(ValueError, match="too large"):
        asyncio.run(adapter._download_slack_file_bytes(START))


def test_oversized_body_without_content_length_rejected(adapter, install_transport):
    """No Content-Length header: the running total is re-checked per chunk."""
    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "image/png"},
            content=b"y" * 4096,
        )
    install_transport(handler)
    with pytest.raises(ValueError, match="too large"):
        asyncio.run(adapter._download_slack_file_bytes(START))


def test_small_file_still_downloads(adapter, install_transport):
    """Files under the cap keep working through the streamed path."""
    body = b"\x89PNG\r\n\x1a\nimage bytes"
    install_transport(lambda request: httpx.Response(
        200, headers={"content-type": "image/png"}, content=body))
    assert asyncio.run(adapter._download_slack_file_bytes(START)) == body
