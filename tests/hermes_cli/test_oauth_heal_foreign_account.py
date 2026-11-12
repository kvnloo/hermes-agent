"""Regression for #694: singleton healing must not destroy independent grants."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def oauth_homes(tmp_path, monkeypatch):
    from hermes_cli import auth

    root = tmp_path / "hermes-root"
    profile = root / "profiles" / "separate-account"
    profile.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    monkeypatch.setenv("HERMES_HOME", str(profile))
    monkeypatch.setattr(auth, "_global_auth_store_cache", None)
    monkeypatch.setattr(auth, "_oauth_heal_clean_marks", {})
    monkeypatch.setattr(auth, "_oauth_heal_notices", [])

    def seed(source, *, shared_token=None, root_singleton=False):
        root_row = {
            "id": "account-a", "label": "account-a", "auth_type": "oauth",
            "source": source, "priority": 0,
            "access_token": "sk-ant-oat01-fake-account-a",
            "refresh_token": "fake-refresh-account-a", "expires_at_ms": 4102444800000,
        }
        pair = {
            "accessToken": "sk-ant-oat01-fake-account-b",
            "refreshToken": "fake-refresh-account-b", "expiresAt": 4102444801000,
        }
        if shared_token:
            singleton_key = {"access_token": "accessToken", "refresh_token": "refreshToken"}[shared_token]
            pair[singleton_key] = root_row[shared_token]
        rows = [root_row]
        if shared_token and source == "manual:hermes_pkce":
            rows.insert(0, {
                **root_row, "id": "unrelated-first-pkce",
                "access_token": "sk-ant-oat01-fake-unrelated",
                "refresh_token": "fake-refresh-unrelated",
            })
        store = {
            "version": 1, "providers": {}, "active_provider": "anthropic",
            "credential_pool": {"anthropic": rows},
        }
        (root / "auth.json").write_text(json.dumps(store))
        (profile / "auth.json").write_text(json.dumps({
            "version": 1, "providers": {}, "active_provider": "anthropic",
        }))
        if root_singleton:
            (root / ".anthropic_oauth.json").write_text(json.dumps({
                "accessToken": root_row["access_token"],
                "refreshToken": root_row["refresh_token"],
                "expiresAt": root_row["expires_at_ms"],
            }))
        singleton = profile / ".anthropic_oauth.json"
        singleton.write_text(json.dumps(pair))
        return root, profile, singleton, pair

    return seed


@pytest.mark.parametrize("source,root_singleton", [
    ("env:ANTHROPIC_TOKEN", False),
    ("manual:hermes_pkce", False),
    ("hermes_pkce", True),
])
def test_load_pool_preserves_foreign_singleton(oauth_homes, source, root_singleton):
    from agent.credential_pool import load_pool
    from hermes_cli.auth import heal_forked_single_use_oauth_grants

    root, _, singleton, pair = oauth_homes(source, root_singleton=root_singleton)
    before = singleton.read_bytes()
    root_before = (root / "auth.json").read_bytes()
    root_singleton_before = (
        (root / ".anthropic_oauth.json").read_bytes() if root_singleton else None
    )
    summary = heal_forked_single_use_oauth_grants("anthropic")
    assert singleton.exists(), "healer deleted the only copy of account B's grant"
    assert summary is None
    assert singleton.read_bytes() == before
    assert (root / "auth.json").read_bytes() == root_before
    if root_singleton:
        assert (root / ".anthropic_oauth.json").read_bytes() == root_singleton_before
    for _ in range(2):
        load_pool("anthropic")
        root_rows = json.loads((root / "auth.json").read_text())["credential_pool"]["anthropic"]
        adopted = any(
            (row.get("access_token"), row.get("refresh_token"))
            == (pair["accessToken"], pair["refreshToken"])
            for row in root_rows
        )
        assert singleton.exists() or adopted, "account B's grant has no surviving owner"
        if singleton.exists():
            assert singleton.read_bytes() == before


@pytest.mark.parametrize("shared_token", ["access_token", "refresh_token"])
@pytest.mark.parametrize("source,root_singleton", [
    ("env:ANTHROPIC_TOKEN", False),
    ("manual:hermes_pkce", False),
    ("hermes_pkce", True),
])
def test_heal_consolidates_only_matching_singleton(oauth_homes, source, root_singleton, shared_token):
    from hermes_cli.auth import heal_forked_single_use_oauth_grants

    root, _, singleton, pair = oauth_homes(
        source, root_singleton=root_singleton, shared_token=shared_token,
    )
    summary = heal_forked_single_use_oauth_grants("anthropic")
    assert summary is not None
    assert summary["files"] == [".anthropic_oauth.json"]
    assert not singleton.exists()
    if root_singleton:
        saved = json.loads((root / ".anthropic_oauth.json").read_text())
        assert saved == pair
    else:
        rows = json.loads((root / "auth.json").read_text())["credential_pool"]["anthropic"]
        row = next(row for row in rows if row["id"] == "account-a")
        # PKCE rows adopt the newer pair. Env rows need only prove shared lineage.
        if source == "manual:hermes_pkce":
            assert (row["access_token"], row["refresh_token"]) == (
                pair["accessToken"], pair["refreshToken"],
            )
            unrelated = next(row for row in rows if row["id"] == "unrelated-first-pkce")
            assert unrelated["refresh_token"] == "fake-refresh-unrelated"
        else:
            singleton_key = {"access_token": "accessToken", "refresh_token": "refreshToken"}[shared_token]
            assert row[shared_token] == pair[singleton_key]
