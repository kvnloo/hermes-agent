"""CLI plugin activation through the dashboard auth gate, regression for #847."""
import io
import urllib.error
import urllib.request

import pytest
from fastapi.testclient import TestClient
from rich.console import Console

from gateway import host_rendezvous as hr
from hermes_cli import plugins_activation
from hermes_cli.dashboard_auth import clear_providers
from hermes_cli.dashboard_auth import token_auth


ROUTE = "/api/dashboard/agent-plugins/activate"
TOKEN = "synthetic-rendezvous-token"
_REAL_GO_LIVE = plugins_activation.load_and_go_live


@pytest.fixture
def backend(tmp_path, monkeypatch):
    from hermes_cli import web_server
    from hermes_constants import get_hermes_home

    clear_providers()
    token_auth.clear_token_routes()
    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text("plugins:\n  enabled: [rendezvous-probe]\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_GATEWAY_LOCK_DIR", str(tmp_path / "locks"))
    monkeypatch.delenv("HERMES_DASHBOARD_SESSION_TOKEN", raising=False)
    monkeypatch.delenv("HERMES_DESKTOP", raising=False)
    monkeypatch.setattr(web_server, "_SESSION_TOKEN", TOKEN)
    for key, value in (("auth_required", True), ("bound_host", "localhost"),
                       ("trusted_public_hosts", frozenset()), ("host_role", None)):
        monkeypatch.setattr(web_server.app.state, key, value, raising=False)
    monkeypatch.setattr(hr, "cleanup_on_exit", lambda role: None)
    monkeypatch.setattr(hr, "served_profiles", lambda: ("default",))
    calls = []

    def activate(name):
        calls.append((name, get_hermes_home()))
        return {"name": name, "key": name, "activated_now": {}, "deferred": {}}

    monkeypatch.setattr(plugins_activation, "load_and_go_live", activate)
    web_server._publish_host_rendezvous("localhost", 9231)
    client = TestClient(web_server.app, base_url="http://localhost:9231")
    try:
        yield client, home, calls
    finally:
        client.close()
        hr.clear_record(hr.ROLE_SERVE)
        hr.release_host_lock(hr.ROLE_SERVE)
        clear_providers()
        token_auth.clear_token_routes()


def test_rendezvous_token_crosses_the_cookie_gate(backend):
    client, home, calls = backend
    response = client.post(ROUTE, headers={"Authorization": f"Bearer {TOKEN}"},
                           json={"name": "rendezvous-probe", "home": str(home)})
    assert response.status_code == 200, response.text
    assert response.json()["activation"]["name"] == "rendezvous-probe"
    assert calls == [("rendezvous-probe", home)]


@pytest.mark.parametrize("token", ["", "wrong-token", "foreign-backend-token"])
def test_activation_rejects_missing_or_wrong_tokens(backend, token):
    client, home, calls = backend
    response = client.post(ROUTE, headers={"Authorization": f"Bearer {token}"},
                           json={"name": "rendezvous-probe", "home": str(home)})
    assert response.status_code == 401, response.text
    assert calls == []


def test_rendezvous_token_does_not_open_other_dashboard_routes(backend):
    client, _, calls = backend
    response = client.get("/api/config", headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 401, response.text
    assert calls == []


def test_rendezvous_token_cannot_authorize_a_different_token_route(backend):
    client, _, calls = backend
    token_auth.register_token_route("/api/gateway/drain")
    response = client.post("/api/gateway/drain", headers={"Authorization": f"Bearer {TOKEN}"},
                           json={"action": "invalid-probe"})
    assert response.status_code == 401, response.text
    assert calls == []


def _http_transport(client, monkeypatch, *, status=None):
    """Keep the CLI request construction and the real ASGI auth/router stack."""
    def urlopen(request, timeout):
        assert timeout == 60
        response = client.request(request.method, request.full_url,
                                  headers=dict(request.header_items()), content=request.data)
        code = status or response.status_code
        if code >= 400:
            raise urllib.error.HTTPError(request.full_url, code, "activation refused", {}, None)
        return io.BytesIO(response.content)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)


def test_cli_request_reaches_the_gated_backend(backend, monkeypatch):
    client, home, calls = backend
    _http_transport(client, monkeypatch)
    result = plugins_activation.notify_serve_backend("rendezvous-probe", home)
    assert result is not None
    assert result["activation"]["name"] == "rendezvous-probe"
    assert calls == [("rendezvous-probe", home)]


@pytest.mark.parametrize("failure", [401, 503, "connection", "not-loaded"])
def test_cli_reports_failed_gui_activation_even_if_gateway_reloads(backend, monkeypatch, failure):
    client, _, _ = backend
    if failure == "connection":
        def refused(*args, **kwargs):
            raise urllib.error.URLError("connection refused")
        monkeypatch.setattr(urllib.request, "urlopen", refused)
    else:
        _http_transport(client, monkeypatch, status=failure if isinstance(failure, int) else None)
        if failure == "not-loaded":
            monkeypatch.setattr(plugins_activation, "load_and_go_live", lambda name: None)
    monkeypatch.setattr(plugins_activation, "reload_running_gateway", lambda: {
        "reloaded": True, "activations": [{"name": "rendezvous-probe", "key": "rendezvous-probe",
                                           "activated_now": {}, "deferred": {}}]})
    output = io.StringIO()
    plugins_activation.report_activation(Console(file=output, width=200, color_system=None), "rendezvous-probe")
    assert "not live in GUI" in output.getvalue(), output.getvalue()


def test_activation_rejects_a_home_outside_the_served_profiles(backend, tmp_path):
    client, _, calls = backend
    response = client.post(ROUTE, headers={"Authorization": f"Bearer {TOKEN}"},
                           json={"name": "rendezvous-probe", "home": str(tmp_path / "foreign-home")})
    assert response.status_code == 400, response.text
    assert calls == []


def test_cli_activation_loads_a_real_plugin_skill_in_the_backend(backend, monkeypatch):
    from hermes_cli import plugins

    client, home, _ = backend
    plugin = home / "plugins" / "rendezvous-probe"
    plugin.mkdir(parents=True)
    (plugin / "plugin.yaml").write_text("name: rendezvous-probe\nversion: '1.0'\n", encoding="utf-8")
    (plugin / "SKILL.md").write_text("---\nname: probe\ndescription: Local probe\n---\nProbe content.\n", encoding="utf-8")
    (plugin / "__init__.py").write_text(
        "from pathlib import Path\n\ndef register(ctx):\n"
        "    ctx.register_skill('probe', Path(__file__).with_name('SKILL.md'), 'Local probe')\n",
        encoding="utf-8")
    empty_bundled = home / "empty-bundled"
    empty_bundled.mkdir()
    monkeypatch.setenv("HERMES_BUNDLED_PLUGINS", str(empty_bundled))
    monkeypatch.setattr(plugins_activation, "load_and_go_live", _REAL_GO_LIVE)
    monkeypatch.setattr(plugins_activation, "reload_running_gateway", lambda: None)
    _http_transport(client, monkeypatch)

    result = plugins_activation.activate_plugin_now("rendezvous-probe", in_process=False)

    assert result["activation"] is not None, result
    skill = result["activation"]["live_now"]["skills"][0]
    assert skill["name"].endswith(":probe"), skill
    entry = plugins.get_plugin_manager()._plugin_skills[skill["name"]]
    assert entry["plugin_key"] == result["activation"]["key"]
    hint = plugins_activation.activation_hint(result)
    assert "1 skills" in hint and "not live in GUI" not in hint, hint


def test_no_discoverable_backend_is_not_reported_as_a_failed_activation(backend, monkeypatch):
    monkeypatch.setattr(plugins_activation, "_serve_backend_record", lambda: None)
    monkeypatch.setattr(plugins_activation, "reload_running_gateway", lambda: None)
    monkeypatch.setattr(plugins_activation, "_gateway_present", lambda: False)
    result = plugins_activation.activate_plugin_now("rendezvous-probe", in_process=False)
    assert plugins_activation.activation_hint(result) == ""
