"""Bare webhook scripts execute under the gateway default profile in multiplex mode.

Regression for #143233 / #143547 GW-45. An unscoped script with a registered
skill env passthrough was silently marked ignored before the child started.
"""

from types import SimpleNamespace

from agent.secret_scope import current_secret_scope, get_secret, set_multiplex_active
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
        'import json\nprint(json.dumps({"accepted": True}))\n', encoding="utf-8"
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("NOTION_TOKEN", "ambient-process-value")
    monkeypatch.setattr("hermes_cli.profiles.get_profile_dir", lambda name: home if name == "default" else None)

    adapter = WebhookAdapter(PlatformConfig(enabled=True, extra={"routes": {}}))
    adapter.gateway_runner = SimpleNamespace(config=SimpleNamespace(multiplex_profiles=True))
    allowed = _get_allowed()
    preexisting = "NOTION_TOKEN" in allowed
    register_env_passthrough(["NOTION_TOKEN"])
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
        set_multiplex_active(False)
        if not preexisting:
            allowed.discard("NOTION_TOKEN")
