"""ENOSPC cannot consume a pool-owned OAuth refresh token before auth.json can be staged (#151973)."""

from __future__ import annotations

import errno
import tempfile
from pathlib import Path

from agent import anthropic_credentials
from agent.credential_pool import AUTH_TYPE_OAUTH, CredentialPool, PooledCredential
from hermes_cli.auth import write_credential_pool


def test_full_auth_store_blocks_single_use_refresh(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))

    entry = PooledCredential(
        provider="anthropic",
        id="pool-oauth",
        label="pooled OAuth login",
        auth_type=AUTH_TYPE_OAUTH,
        priority=0,
        source="manual:dashboard_pkce",
        access_token="old-access",
        refresh_token="old-refresh",
        expires_at_ms=1000,
    )
    write_credential_pool("anthropic", [entry.to_dict()])
    original_store = (home / "auth.json").read_bytes()
    pool = CredentialPool("anthropic", [entry])
    refresh_posts = []

    def rotate(refresh_token, *, use_json=False):
        refresh_posts.append(refresh_token)
        return {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_at_ms": 99_999_999_999_999,
        }

    monkeypatch.setattr(anthropic_credentials, "refresh_anthropic_oauth_pure", rotate)
    actual_mkstemp = tempfile.mkstemp

    def disk_full(*args, **kwargs):
        if Path(kwargs.get("dir") or ".").resolve() == home.resolve():
            raise OSError(errno.ENOSPC, "No space left on device")
        return actual_mkstemp(*args, **kwargs)

    monkeypatch.setattr(tempfile, "mkstemp", disk_full)

    assert pool._refresh_entry(entry, force=True) is None
    assert refresh_posts == [], "the provider must never consume the only refresh token"
    assert pool.entries()[0].refresh_token == "old-refresh"
    assert (home / "auth.json").read_bytes() == original_store
