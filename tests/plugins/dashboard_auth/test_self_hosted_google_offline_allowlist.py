"""Self-hosted OIDC: IdP-specific authorize params (Google offline access) and email allowlist."""

from __future__ import annotations

import urllib.parse
from unittest.mock import patch

import pytest

from hermes_cli.dashboard_auth import InvalidCodeError, RefreshExpiredError
from plugins.dashboard_auth import self_hosted as oidc_plugin
from tests.plugins.dashboard_auth.test_self_hosted_provider import (  # noqa: F401  (fixture)
    _make_provider, _mint_id_token, _mock_post, rsa_keypair)

_REDIRECT = "https://hermes.example/auth/callback"


def _with(provider, **attrs):
    for k, v in attrs.items():
        setattr(provider, k, v)
    return provider


def _query(url: str) -> dict[str, str]:
    return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))


def test_extra_authorize_params_reach_authorize_url(rsa_keypair):
    p = _with(_make_provider(rsa_keypair),
              _extra_authorize_params={"access_type": "offline", "prompt": "consent"})
    q = _query(p.start_login(redirect_uri=_REDIRECT).redirect_url)
    assert q["access_type"] == "offline" and q["prompt"] == "consent"
    assert q["code_challenge_method"] == "S256" and q["redirect_uri"] == _REDIRECT


def test_extra_params_cannot_override_standard_params(rsa_keypair):
    p = _with(_make_provider(rsa_keypair),
              _extra_authorize_params={"redirect_uri": "https://evil.example/cb", "state": "x"})
    q = _query(p.start_login(redirect_uri=_REDIRECT).redirect_url)
    assert q["redirect_uri"] == _REDIRECT and q["state"] != "x"


def _token_resp(rsa_keypair, **claims):
    return _mock_post(200, {"id_token": _mint_id_token(rsa_keypair, **claims), "token_type": "Bearer",
                            "refresh_token": "rt"})


def _login(p, resp):
    with patch("plugins.dashboard_auth.self_hosted.httpx.post", return_value=resp):
        return p.complete_login(code="c", state="s", code_verifier="v", redirect_uri=_REDIRECT)


def _allow(p, *emails):
    return _with(p, _allowed_emails=frozenset(e.lower() for e in emails))


def test_allowlisted_verified_email_logs_in(rsa_keypair):
    p = _allow(_make_provider(rsa_keypair), "Alice@Example.com")
    s = _login(p, _token_resp(rsa_keypair, extra_claims={"email_verified": True}))
    assert s.email == "alice@example.com" and s.refresh_token == "rt"


@pytest.mark.parametrize("claims", [
    {"email": "mallory@example.com", "extra_claims": {"email_verified": True}},
    {"extra_claims": {"email_verified": False}},
    {},  # email_verified absent
    {"email": None, "extra_claims": {"email_verified": True}},
])
def test_login_rejects_unlisted_or_unverified(rsa_keypair, claims):
    p = _allow(_make_provider(rsa_keypair), "alice@example.com")
    with pytest.raises(InvalidCodeError):
        _login(p, _token_resp(rsa_keypair, **claims))


def test_refresh_rejects_unlisted_as_expired(rsa_keypair):
    p = _allow(_make_provider(rsa_keypair), "alice@example.com")
    resp = _token_resp(rsa_keypair, email="mallory@example.com", extra_claims={"email_verified": True})
    with patch("plugins.dashboard_auth.self_hosted.httpx.post", return_value=resp):
        with pytest.raises(RefreshExpiredError):
            p.refresh_session(refresh_token="rt")


def test_verify_session_enforces_allowlist(rsa_keypair):
    p = _allow(_make_provider(rsa_keypair), "alice@example.com")
    good = _mint_id_token(rsa_keypair, extra_claims={"email_verified": True})
    bad = _mint_id_token(rsa_keypair, email="mallory@example.com", extra_claims={"email_verified": True})
    assert p.verify_session(access_token=good) is not None
    assert p.verify_session(access_token=bad) is None


def test_no_allowlist_keeps_previous_behaviour(rsa_keypair):
    p = _make_provider(rsa_keypair)
    assert _login(p, _token_resp(rsa_keypair, email="anyone@example.com")).email == "anyone@example.com"


def test_settings_parse_env(monkeypatch):
    monkeypatch.setenv("HERMES_DASHBOARD_OIDC_ISSUER", "https://accounts.google.com")
    monkeypatch.setenv("HERMES_DASHBOARD_OIDC_CLIENT_ID", "cid")
    monkeypatch.setenv("HERMES_DASHBOARD_OIDC_EXTRA_AUTHORIZE_PARAMS", "access_type=offline&prompt=consent")
    monkeypatch.setenv("HERMES_DASHBOARD_OIDC_ALLOWED_EMAILS", "a@x.com, b@y.com")
    with patch.object(oidc_plugin, "_load_config_oauth_section", return_value={}):
        kw = oidc_plugin._settings()
    assert kw["extra_authorize_params"] == {"access_type": "offline", "prompt": "consent"}
    assert kw["allowed_emails"] == ["a@x.com", "b@y.com"]
    oidc_plugin.SelfHostedOIDCProvider(**kw)  # constructor accepts every settings key
