"""Bare webhook scripts execute under the gateway default profile in multiplex mode.

Regression for #143233 / #143547 GW-45. An unscoped script with a registered
skill env passthrough was silently marked ignored before the child started.
"""

import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from agent.secret_scope import (
    current_secret_scope, get_secret, is_multiplex_active, set_multiplex_active,
)
from gateway.config import PlatformConfig
from gateway.platforms.webhook import WebhookAdapter
from gateway.platforms.webhook_filters import WebhookRouteProcessor
from tools.env_passthrough import _get_allowed, register_env_passthrough


def test_bare_webhook_script_has_default_profile_scope_under_multiplex(tmp_path, monkeypatch):
    home = tmp_path / "default"
    scripts = home / "scripts"
    scripts.mkdir(parents=True)
    (home / ".env").write_text("NOTION_TOKEN=route-scoped-test-value\n", encoding="utf-8")
    (scripts / "filter.py").write_text(
        'import json, os\n'
        'assert os.environ["NOTION_TOKEN"] == "route-scoped-test-value"\n'
        'print(json.dumps({"accepted": True}))\n', encoding="utf-8"
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("NOTION_TOKEN", "ambient-process-value")
    monkeypatch.setattr("hermes_cli.profiles.get_profile_dir", lambda name: home if name == "default" else None)

    adapter = WebhookAdapter(PlatformConfig(enabled=True, extra={"routes": {}}))
    adapter.gateway_runner = SimpleNamespace(config=SimpleNamespace(multiplex_profiles=True))
    allowed = _get_allowed()
    preexisting = "NOTION_TOKEN" in allowed
    register_env_passthrough(["NOTION_TOKEN"])
    previous = is_multiplex_active()
    set_multiplex_active(True)
    try:
        with adapter._profile_scope(None):
            assert current_secret_scope() is not None
            assert get_secret("NOTION_TOKEN") == "route-scoped-test-value"
            accepted, payload = WebhookRouteProcessor().run_route_script("filter.py", {"x": 1})
        assert accepted is True
        assert payload == {"accepted": True}
        assert current_secret_scope() is None
    finally:
        set_multiplex_active(previous)
        if not preexisting:
            allowed.discard("NOTION_TOKEN")


@pytest.mark.parametrize(("multiplex", "profile"), [(False, None), (True, "secondary")])
def test_webhook_scope_preserves_single_profile_and_named_routes(tmp_path, monkeypatch, multiplex, profile):
    home = tmp_path / (profile or "default")
    home.mkdir()
    (home / ".env").write_text("NOTION_TOKEN=owned-test-value\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "default"))
    monkeypatch.setenv("NOTION_TOKEN", "ambient-test-value")
    monkeypatch.setattr("hermes_cli.profiles.get_profile_dir", lambda name: home if name == profile else None)
    previous = is_multiplex_active()
    set_multiplex_active(multiplex)
    try:
        with WebhookAdapter._profile_scope(profile):
            assert (current_secret_scope() is not None) is multiplex
            assert get_secret("NOTION_TOKEN") == ("owned-test-value" if multiplex else "ambient-test-value")
        assert current_secret_scope() is None
    finally:
        set_multiplex_active(previous)


@pytest.mark.asyncio
async def test_signed_bare_script_webhook_commits_admission(tmp_path, monkeypatch):
    from tests.gateway.fixtures.webhook_route_authority import mount_authority

    home = tmp_path / "default"
    scripts = home / "scripts"
    scripts.mkdir(parents=True)
    (home / ".env").write_text("NOTION_TOKEN=route-scoped-test-value\n", encoding="utf-8")
    (scripts / "filter.py").write_text(
        'import json, os, sys\n'
        'assert os.environ["NOTION_TOKEN"] == "route-scoped-test-value"\n'
        'payload = json.load(sys.stdin)\n'
        'print(json.dumps({"message": "transformed " + payload["message"]}))\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("NOTION_TOKEN", "ambient-process-value")
    monkeypatch.setattr("hermes_cli.profiles.get_profile_dir", lambda name: home if name == "default" else None)
    secret = "webhook-test-signing-value"
    route = {"secret": secret, "script": "filter.py", "prompt": "{message}", "deliver": "log"}
    adapter = WebhookAdapter(PlatformConfig(enabled=True, extra={"routes": {"script": route}}))
    events = []

    async def capture(event):
        events.append(event)

    adapter.handle_message = capture
    app = web.Application()
    mount_authority(app, adapter)
    app.router.add_post("/webhooks/{route_name}", adapter._handle_webhook)
    allowed = _get_allowed()
    preexisting = "NOTION_TOKEN" in allowed
    previous = is_multiplex_active()
    register_env_passthrough(["NOTION_TOKEN"])
    try:
        async with TestClient(TestServer(app)) as client:
            set_multiplex_active(True)
            body = json.dumps({"message": "test event"}).encode()
            signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            response = await client.post("/webhooks/script", data=body, headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
                "X-GitHub-Delivery": "script-admission-test",
            })
            assert response.status == 202
            assert (await response.json())["status"] == "accepted"
            assert len(events) == 1
            assert events[0].text == "transformed test event"
            assert current_secret_scope() is None
    finally:
        set_multiplex_active(previous)
        if not preexisting:
            allowed.discard("NOTION_TOKEN")
