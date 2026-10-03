"""Custom key_env must not change a registered provider's authentication contract."""

import json

import pytest

from agent import credential_pool
from hermes_cli.auth import ProviderConfig
from hermes_cli.config import invalidate_env_cache

PROVIDER = "fixture-provider"
CUSTOM_ENV = "FIXTURE_CUSTOM_KEY"
REGISTRY_ENV = "FIXTURE_REGISTRY_KEY"
CUSTOM_KEY = "synthetic-custom-credential"
REGISTRY_KEY = "synthetic-registry-credential"
CUSTOM_URL = "https://custom.invalid/v1"
REGISTRY_URL = "https://registry.invalid/v1"


@pytest.fixture
def configured_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    (home / "config.yaml").write_text(json.dumps({"providers": {
        PROVIDER: {"base_url": CUSTOM_URL, "api_mode": "chat_completions", "key_env": CUSTOM_ENV}
    }}), encoding="utf-8")
    (home / ".env").write_text(
        f"{CUSTOM_ENV}={CUSTOM_KEY}\n{REGISTRY_ENV}={REGISTRY_KEY}\n", encoding="utf-8")
    invalidate_env_cache()
    return home


@pytest.mark.parametrize("auth_type", ["oauth_device_code", "aws_sdk", "vertex", "external_process"])
def test_registered_non_api_provider_rejects_custom_key_collision(configured_home, monkeypatch, auth_type):
    monkeypatch.setitem(credential_pool.PROVIDER_REGISTRY, PROVIDER, ProviderConfig(
        id=PROVIDER, name="Fixture provider", auth_type=auth_type,
        inference_base_url=REGISTRY_URL,
    ))
    pool = credential_pool.load_pool(PROVIDER)
    assert pool.acquire_lease() is None
    assert pool.select() is None
    auth_file = configured_home / "auth.json"
    if auth_file.exists():
        rows = json.loads(auth_file.read_text(encoding="utf-8")).get("credential_pool", {}).get(PROVIDER, [])
        assert rows == []


@pytest.mark.parametrize("registered", [False, True], ids=["custom", "registry-api-key"])
def test_key_seeding_preserves_custom_and_registry_precedence(configured_home, monkeypatch, registered):
    if registered:
        monkeypatch.setitem(credential_pool.PROVIDER_REGISTRY, PROVIDER, ProviderConfig(
            id=PROVIDER, name="Fixture provider", auth_type="api_key",
            inference_base_url=REGISTRY_URL, api_key_env_vars=(REGISTRY_ENV,),
        ))
    else:
        monkeypatch.delitem(credential_pool.PROVIDER_REGISTRY, PROVIDER, raising=False)
    expected_key = REGISTRY_KEY if registered else CUSTOM_KEY
    expected_url = REGISTRY_URL if registered else CUSTOM_URL
    expected_source = f"env:{REGISTRY_ENV if registered else CUSTOM_ENV}"
    for _ in range(2):
        pool = credential_pool.load_pool(PROVIDER)
        selected = pool.select()
        assert selected is not None
        assert (selected.source, selected.runtime_api_key, selected.runtime_base_url) == (
            expected_source, expected_key, expected_url)
        lease = pool.acquire_lease()
        assert lease == selected.id
        pool.release_lease(lease)
    persisted = (configured_home / "auth.json").read_text(encoding="utf-8")
    assert CUSTOM_KEY not in persisted and REGISTRY_KEY not in persisted
    rows = json.loads(persisted)["credential_pool"][PROVIDER]
    assert len(rows) == 1 and rows[0]["source"] == expected_source
