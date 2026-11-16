"""Regression for #132953 / #155888: Email publishes its own lifecycle state."""

import asyncio

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.email.adapter import EmailAdapter


@pytest.mark.asyncio
async def test_email_adapter_publishes_profile_status_on_connect_and_disconnect(monkeypatch):
    for name, value in {
        "EMAIL_ADDRESS": "bot@example.test",
        "EMAIL_PASSWORD": "test-password",
        "EMAIL_IMAP_HOST": "imap.example.test",
        "EMAIL_SMTP_HOST": "smtp.example.test",
        "EMAIL_AUTHSERV_ID": "mx.example.test",
    }.items():
        monkeypatch.setenv(name, value)

    adapter = EmailAdapter(PlatformConfig(enabled=True))
    adapter._runtime_status_platform_key = "work:email"

    # Keep the adapter's real connect/disconnect lifecycle, without network I/O.
    monkeypatch.setattr(adapter, "_probe_imap", lambda _reconnect: True)
    monkeypatch.setattr(adapter, "_probe_smtp", lambda: True)

    async def idle_poll():
        await asyncio.Event().wait()

    monkeypatch.setattr(adapter, "_poll_loop", idle_poll)
    monkeypatch.setattr(adapter, "_wire_plugin_handlers", lambda _handlers: None)

    from gateway import status

    published = []
    monkeypatch.setattr(status, "publish_runtime_status", lambda **kwargs: published.append(kwargs))

    assert await adapter.connect() is True
    assert published == [{
        "platform": "work:email",
        "platform_state": "connected",
        "error_code": None,
        "error_message": None,
    }]

    await adapter.disconnect()
    assert published[-1] == {
        "platform": "work:email",
        "platform_state": "disconnected",
        "error_code": None,
        "error_message": None,
    }
    assert adapter._running is False
