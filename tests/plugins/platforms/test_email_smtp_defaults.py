"""Regression for NousResearch/hermes-agent#150806: alternate SMTPS ports.

The live adapter and standalone sender must agree on SMTP TLS transport.
No mail server or network connection is used.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.email.adapter import EmailAdapter, _standalone_send


@pytest.mark.parametrize(
    ("port", "security", "expected"),
    [
        (465, None, "tls"),
        (10465, None, "tls"),
        (4465, None, "tls"),
        (587, None, "starttls"),
        (1025, None, "starttls"),
        (10465, "starttls", "starttls"),
        (587, "tls", "tls"),
        (10465, "plain", "plain"),
    ],
)
@pytest.mark.parametrize("standalone", [False, True])
def test_smtp_transport_default_and_override(monkeypatch, port, security, expected, standalone):
    monkeypatch.setenv("EMAIL_ADDRESS", "hermes@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")
    monkeypatch.setenv("EMAIL_IMAP_HOST", "imap.example.com")
    monkeypatch.setenv("EMAIL_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("EMAIL_SMTP_PORT", str(port))
    if security is None:
        monkeypatch.delenv("EMAIL_SMTP_SECURITY", raising=False)
    else:
        monkeypatch.setenv("EMAIL_SMTP_SECURITY", security)

    with patch("smtplib.SMTP") as plain_smtp, patch("smtplib.SMTP_SSL") as tls_smtp:
        if standalone:
            result = asyncio.run(_standalone_send(
                SimpleNamespace(extra={}), "recipient@example.com", "hello",
            ))
            assert result["success"] is True
        else:
            adapter = EmailAdapter(PlatformConfig(enabled=True))
            adapter._connect_smtp()

    if expected == "tls":
        tls_smtp.assert_called_once()
        plain_smtp.assert_not_called()
    else:
        plain_smtp.assert_called_once()
        tls_smtp.assert_not_called()
        if expected == "starttls":
            plain_smtp.return_value.starttls.assert_called_once()
        else:
            plain_smtp.return_value.starttls.assert_not_called()
