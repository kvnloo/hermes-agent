"""Command-level regression for idle Anthropic OAuth usage reads (#152270)."""

import argparse
import json
from types import SimpleNamespace

import httpx

from agent import account_usage
from hermes_cli.subcommands.usage import cmd_usage


def test_usage_json_refreshes_idle_anthropic_oauth_on_401(monkeypatch, capsys):
    """A standalone usage poll recovers without an intervening model request."""
    stale = "sk-ant-oat01-expired"
    fresh = "sk-ant-oat01-refreshed"
    attempted = []
    refresh_hints = []

    monkeypatch.setattr(
        "hermes_cli.runtime_provider.resolve_requested_provider",
        lambda requested: requested,
    )
    monkeypatch.setattr(account_usage, "resolve_anthropic_token", lambda: stale)

    def get_json(url, headers, *, timeout):
        token = headers["Authorization"].removeprefix("Bearer ")
        attempted.append(token)
        if token == stale:
            request = httpx.Request("GET", url)
            response = httpx.Response(401, request=request)
            raise httpx.HTTPStatusError("401", request=request, response=response)
        assert token == fresh
        return {"five_hour": {"utilization": 0.42, "resets_at": "2026-11-10T01:00:00Z"}}

    class Pool:
        def try_refresh_matching(self, api_key_hint=None, credential_id=None):
            refresh_hints.append(api_key_hint)
            return SimpleNamespace(runtime_api_key=fresh)

    def load_pool(provider):
        assert provider == "anthropic"
        return Pool()

    monkeypatch.setattr(account_usage, "_get_json", get_json)
    monkeypatch.setattr("agent.credential_pool.load_pool", load_pool)

    assert cmd_usage(argparse.Namespace(provider="anthropic", json=True)) == 0
    document = json.loads(capsys.readouterr().out)

    assert document["provider"] == "anthropic"
    assert document["windows"][0]["used_percent"] == 42.0
    assert attempted == [stale, fresh]
    assert refresh_hints == [stale]
