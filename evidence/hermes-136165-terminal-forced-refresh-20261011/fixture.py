"""Supplemental PR #136165 evidence: forced recovery must rotate independent B.

The pool-only row is the established positive control. Synthetic JWT subjects
distinguish independent grants even though both expired at the same time.
Only the OAuth HTTP transport is substituted; stores, pool and locks are real.
"""

import base64
import json
from urllib.parse import parse_qs

import httpx
import pytest

from hermes_cli.auth import DEFAULT_CODEX_BASE_URL, resolve_codex_runtime_credentials
from hermes_cli import auth_codex


def _jwt(subject, expiry):
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": subject, "exp": expiry,
                    "https://api.openai.com/auth": {"chatgpt_account_id": subject}}).encode()
    ).decode().rstrip("=")
    return f"synthetic.{payload}.signature"


@pytest.mark.parametrize("terminal_singleton", [False, True], ids=["pool-only", "terminal-singleton"])
def test_force_refresh_rotates_independent_pool_grant(tmp_path, monkeypatch, terminal_singleton):
    home = tmp_path / "home"
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("CODEX_HOME", str(home / ".codex"))
    dead_a = _jwt("synthetic-A", 1000000000)
    expired_b = _jwt("synthetic-B", 1000000000)
    fresh_b = _jwt("synthetic-B", 4102444800)
    singleton = {"tokens": {"access_token": dead_a, "refresh_token": "synthetic-A-rejected"},
                 "auth_mode": "chatgpt", "last_refresh": "2026-01-01T00:00:00Z"}
    mirror = {"id": "mirror-A", "source": "device_code", "auth_type": "oauth",
              "access_token": dead_a, "refresh_token": "synthetic-A-rejected", "last_status": "ok"}
    independent = {"id": "independent-B", "source": "manual:device_code", "auth_type": "oauth",
                   "access_token": expired_b, "refresh_token": "synthetic-B-refresh", "last_status": "ok"}
    auth_file = hermes_home / "auth.json"
    auth_file.write_text(json.dumps({
        "version": 1, "active_provider": "openai-codex",
        "providers": {"openai-codex": singleton} if terminal_singleton else {},
        "credential_pool": {"openai-codex": [mirror, independent] if terminal_singleton else [independent]},
    }))
    refresh_targets = []

    def wire(request):
        assert str(request.url) == auth_codex.CODEX_OAUTH_TOKEN_URL
        assert request.method == "POST"
        fields = parse_qs(request.content.decode())
        assert fields["grant_type"] == ["refresh_token"]
        target = fields["refresh_token"][0]
        refresh_targets.append(target)
        if target == "synthetic-A-rejected":
            return httpx.Response(400, json={"error": "invalid_grant", "error_description": "Synthetic rejection"})
        assert target == "synthetic-B-refresh"
        return httpx.Response(200, json={"access_token": fresh_b, "refresh_token": "synthetic-B-rotated"})

    monkeypatch.setattr(auth_codex, "_codex_http_client", lambda **kwargs: httpx.Client(
        transport=httpx.MockTransport(wire), **kwargs))
    resolved = resolve_codex_runtime_credentials(force_refresh=True)
    persisted = json.loads(auth_file.read_text())
    rows = {row["id"]: row for row in persisted["credential_pool"]["openai-codex"]}
    expected_targets = ["synthetic-A-rejected", "synthetic-B-refresh"] if terminal_singleton else ["synthetic-B-refresh"]
    assert (resolved["api_key"], refresh_targets, rows["independent-B"]["access_token"],
            rows["independent-B"]["refresh_token"]) == (
                fresh_b, expected_targets, fresh_b, "synthetic-B-rotated")
    assert resolved["source"] == "credential_pool"
    assert resolved["base_url"] == DEFAULT_CODEX_BASE_URL
    assert rows["independent-B"]["source"] == "manual:device_code"
    assert rows["independent-B"]["last_status"] == "ok"
    assert persisted["active_provider"] == "openai-codex"
    if terminal_singleton:
        assert persisted["providers"]["openai-codex"] == singleton
        assert rows["mirror-A"]["access_token"] == dead_a
        assert rows["mirror-A"]["refresh_token"] == "synthetic-A-rejected"
    else:
        assert persisted["providers"] == {}
