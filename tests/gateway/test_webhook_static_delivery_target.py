"""Static webhook routes reject targets that the gateway cannot dispatch.

Regression for #84171: static config uses startup validation, not dynamic route loading.
"""

import pytest

from gateway.config import PlatformConfig
from gateway.platforms.webhook import WebhookAdapter


def test_static_webhook_route_refuses_undeliverable_target():
    bad_route = {"prompt": "Alert", "deliver": "telegram/all"}
    adapter = WebhookAdapter(PlatformConfig(enabled=True, extra={
        "secret": "test-hmac-secret", "routes": {"alerts": bad_route},
    }))
    # connect() validates static routes through this seam before opening the listener.
    with pytest.raises(ValueError, match="unknown delivery target 'telegram/all'"):
        adapter._validate_route("alerts", adapter._static_routes["alerts"])
    # A real platform name remains valid.
    adapter._validate_route("valid", {"prompt": "Alert", "deliver": "telegram"})
