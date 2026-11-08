"""Regression for NousResearch/hermes-agent#151356: inbound mail survives SMTP outages."""

import asyncio
from unittest.mock import patch

from gateway.config import PlatformConfig
from plugins.platforms.email.adapter import EmailAdapter


def test_imap_polls_and_dispatches_while_smtp_probe_times_out(monkeypatch):
    for name, value in {
        "EMAIL_ADDRESS": "hermes@example.test",
        "EMAIL_PASSWORD": "secret",
        "EMAIL_IMAP_HOST": "imap.example.test",
        "EMAIL_SMTP_HOST": "smtp.example.test",
    }.items():
        monkeypatch.setenv(name, value)
    adapter = EmailAdapter(PlatformConfig(enabled=True))
    message = {"uid": b"101"}
    received = asyncio.Event()

    async def dispatch(incoming):
        assert incoming == message
        received.set()

    async def exercise():
        with (patch.object(adapter, "_probe_imap", return_value=True),
              patch.object(adapter, "_connect_smtp", side_effect=TimeoutError("SMTP filtered")),
              patch.object(adapter, "_fetch_new_messages", return_value=[message]),
              patch.object(adapter, "_dispatch_message", side_effect=dispatch),
              patch.object(adapter, "_wire_plugin_handlers")):
            assert await adapter.connect()
            try:
                await asyncio.wait_for(received.wait(), timeout=2)
                assert adapter._running
                assert not adapter.has_fatal_error
                assert "SMTP filtered" in adapter._smtp_probe_error
                result = await adapter.send("person@example.test", "reply")
                assert not result.success
                assert "SMTP filtered" in result.error
            finally:
                await adapter.disconnect()

    asyncio.run(exercise())
