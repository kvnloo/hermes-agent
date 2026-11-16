from __future__ import annotations

import json

from hermes_cli import models


class _Response:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


def test_anthropic_picker_discovers_models_with_pool_api_key(monkeypatch):
    """A direct API key stored only in auth.json must reach /v1/models."""
    monkeypatch.setattr(models, "_get_model_config_dict", lambda: {"provider": "nous"})
    monkeypatch.setattr(
        "agent.anthropic_credentials.resolve_anthropic_token",
        lambda: None,
    )
    monkeypatch.setattr(
        "hermes_cli.auth.read_credential_pool",
        lambda provider: (
            [
                {
                    "auth_type": "api_key",
                    "access_token": "sk-ant-api03-pool-key",
                    "base_url": "https://api.anthropic.com",
                }
            ]
            if provider == "anthropic"
            else []
        ),
    )

    captured = {}

    def _open(request, *, timeout):
        captured["url"] = request.full_url
        captured["headers"] = {
            key.lower(): value for key, value in request.header_items()
        }
        captured["timeout"] = timeout
        return _Response({"data": [{"id": "claude-opus-5"}]})

    monkeypatch.setattr(models, "_urlopen_model_catalog_request", _open)

    result = models.provider_model_ids("anthropic")

    assert "claude-opus-5" in result
    assert captured["url"] == "https://api.anthropic.com/v1/models?limit=1000"
    assert captured["headers"]["x-api-key"] == "sk-ant-api03-pool-key"
    assert "authorization" not in captured["headers"]


def test_anthropic_pool_api_key_overrides_conflicting_active_endpoint(monkeypatch):
    """A pool-scoped key must never reach the active model's other endpoint."""
    active_endpoint = "https://active.example/anthropic/v1"
    pool_endpoint = "https://pool.example/anthropic/v1"
    monkeypatch.setattr(
        models,
        "_get_model_config_dict",
        lambda: {"provider": "anthropic", "base_url": active_endpoint},
    )
    monkeypatch.setattr(
        "agent.anthropic_credentials.resolve_anthropic_token",
        lambda: None,
    )
    monkeypatch.setattr(
        "hermes_cli.auth.read_credential_pool",
        lambda provider: (
            [
                {
                    "auth_type": "api_key",
                    "access_token": "proxy-key",
                    "base_url": pool_endpoint,
                }
            ]
            if provider == "anthropic"
            else []
        ),
    )

    requests = []

    def _open(request, *, timeout):
        requests.append((
            request.full_url,
            {key.lower(): value for key, value in request.header_items()},
        ))
        return _Response({"data": [{"id": "claude-proxy-model"}]})

    monkeypatch.setattr(models, "_urlopen_model_catalog_request", _open)

    assert models.provider_model_ids("anthropic") == ["claude-proxy-model"]
    assert requests == [
        (
            f"{pool_endpoint}/models?limit=1000",
            {
                "anthropic-version": "2023-06-01",
                "x-api-key": "proxy-key",
            },
        )
    ]
    assert all(not url.startswith(active_endpoint) for url, _headers in requests)

def test_anthropic_discovery_refreshes_expired_matching_pool_oauth(monkeypatch):
    """Regression for NousResearch/hermes-agent#156462: /models refreshes its own 401 bearer."""
    import io
    import urllib.error
    from types import SimpleNamespace

    expired = "sk-ant-oat01-" + "a" * 95
    fresh = "sk-ant-oat01-" + "b" * 95
    requests = []
    refresh_hints = []

    monkeypatch.setattr(models, "_get_model_config_dict", lambda: {"provider": "nous"})
    monkeypatch.setattr("agent.anthropic_credentials.resolve_anthropic_token", lambda: expired)

    class Pool:
        def try_refresh_matching(self, *, api_key_hint=None):
            refresh_hints.append(api_key_hint)
            return SimpleNamespace(runtime_api_key=fresh)

    def get_json(url, *, timeout, headers):
        assert url == "https://api.anthropic.com/v1/models?limit=1000"
        assert timeout == 5.0
        bearer = headers["Authorization"]
        requests.append(bearer)
        if bearer == f"Bearer {expired}":
            raise urllib.error.HTTPError(
                url, 401, "OAuth access token has expired", {},
                io.BytesIO(b'{"error":{"type":"authentication_error"}}'),
            )
        assert bearer == f"Bearer {fresh}"
        return {"data": [{"id": "claude-new-model"}], "has_more": False}

    monkeypatch.setattr("agent.credential_pool.load_pool", lambda provider: Pool() if provider == "anthropic" else None)
    monkeypatch.setattr(models, "_get_json", get_json)

    assert models._fetch_anthropic_models() == ["claude-new-model"]
    assert requests == [f"Bearer {expired}", f"Bearer {fresh}"]
    assert refresh_hints == [expired]
