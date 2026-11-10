"""Regression for NousResearch/hermes-agent#152609: whoami auth failure classification."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.matrix.adapter import MatrixAdapter


class WhoamiError(Exception):
    def __init__(self, status: int, errcode: str):
        self.http_status = status
        self.errcode = errcode
        super().__init__("Unable to introspect the access token")


def _setup(password: str = ""):
    adapter = MatrixAdapter(PlatformConfig(
        enabled=True, token="valid-token",
        extra={"homeserver": "https://matrix.example.org",
               "user_id": "@bot:example.org", "password": password},
    ))
    client = MagicMock()
    client.mxid = "@bot:example.org"
    client.device_id = None
    client.login = AsyncMock(return_value=SimpleNamespace(device_id="LOGIN-DEV"))
    api = MagicMock()
    api.token = ""
    api.session.close = AsyncMock()
    return adapter, client, api


@pytest.mark.asyncio
async def test_transient_whoami_recovers_with_valid_token():
    adapter, client, api = _setup()
    client.whoami = AsyncMock(side_effect=[
        WhoamiError(503, "M_UNKNOWN"),
        SimpleNamespace(user_id="@bot:example.org", device_id="TOKEN-DEV"),
    ])
    with patch("plugins.platforms.matrix.adapter.asyncio.sleep", new_callable=AsyncMock) as sleep:
        assert await adapter._connect_authenticate(client, api) is True
    assert client.whoami.await_count == 2
    sleep.assert_awaited_once_with(2)
    client.login.assert_not_awaited()
    assert client.device_id == "TOKEN-DEV"
    assert api.token == "valid-token"
    api.session.close.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "errcode", "attempts"),
    [(503, "M_UNKNOWN", 3), (401, "M_UNKNOWN_TOKEN", 1)],
)
async def test_whoami_failure_uses_password_fallback(status, errcode, attempts):
    adapter, client, api = _setup(password="secret")
    client.whoami = AsyncMock(side_effect=WhoamiError(status, errcode))
    with patch("plugins.platforms.matrix.adapter.asyncio.sleep", new_callable=AsyncMock) as sleep:
        assert await adapter._connect_authenticate(client, api) is True
    assert client.whoami.await_count == attempts
    assert sleep.await_count == attempts - 1
    client.login.assert_awaited_once_with(
        identifier="@bot:example.org", password="secret",
        device_name="Hermes Agent", device_id=None,
    )
    assert api.token == ""
    assert client.device_id == "LOGIN-DEV"
    api.session.close.assert_not_awaited()
