"""Native Anthropic model metadata uses the runtime OAuth token classifier.

A Claude login may use JWT (eyJ*) or cc-* tokens, not only sk-ant-oat*.
Both must receive bearer headers on Anthropic's host and never leave it.
"""

from types import SimpleNamespace

import pytest

from agent import model_metadata as metadata
from agent import model_metadata_http
from agent.anthropic_credentials import _is_oauth_token


@pytest.mark.parametrize("token", ("eyJ.test-jwt", "cc-test-oauth"))
def test_live_context_probe_handles_other_native_oauth_token_shapes(monkeypatch, token):
    assert _is_oauth_token(token)
    calls = []

    def fake_get(url, *, headers=None, timeout=None, verify=None):
        calls.append((url, dict(headers or {})))
        bearer = headers.get("Authorization") == f"Bearer {token}"
        beta = "oauth-2025-04-20" in headers.get("anthropic-beta", "").split(",")
        if not (bearer and beta):
            return SimpleNamespace(status_code=401)
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"data": [{"id": "claude-quasar-6-1", "max_input_tokens": 1_000_000}]},
        )

    monkeypatch.setattr(model_metadata_http, "get", fake_get)
    monkeypatch.setattr(metadata, "get_cached_context_length", lambda *_a, **_kw: None)

    assert metadata.get_model_context_length(
        "claude-quasar-6-1",
        base_url="https://api.anthropic.com",
        api_key=token,
        provider="anthropic",
    ) == 1_000_000
    assert len(calls) == 1
    assert calls[0][1]["Authorization"] == f"Bearer {token}"
    assert "x-api-key" not in calls[0][1]

    # Even an explicit foreign Anthropic-compatible endpoint must not see the OAuth token.
    assert metadata._query_anthropic_context_length(
        "claude-quasar-6-1", "https://relay.example", token
    ) is None
    assert len(calls) == 1
