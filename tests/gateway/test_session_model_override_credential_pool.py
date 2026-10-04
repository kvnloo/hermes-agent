"""Session /model overrides must attach credential_pool for 402 rotation."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from gateway.run import GatewayRunner


def test_fast_session_override_includes_credential_pool(monkeypatch):
    runner = object.__new__(GatewayRunner)
    runner._session_model_overrides = {
        "sess-1": {
            "model": "kimi-k2.7",
            "provider": "custom:hyper",
            "api_key": "sk-test",
            "base_url": "https://hyper.charm.land/v1",
            "api_mode": "chat_completions",
        },
    }
    fake_pool = object()

    monkeypatch.setattr(
        "gateway.run._resolve_gateway_model",
        lambda _uc=None: "default-model",
    )
    monkeypatch.setattr(
        "gateway.run._credential_pool_for_provider",
        lambda provider, **kwargs: fake_pool if provider == "custom:hyper" else None,
    )

    model, runtime = runner._resolve_session_agent_runtime(session_key="sess-1")

    assert model == "kimi-k2.7"
    assert runtime.get("credential_pool") is fake_pool


@pytest.mark.parametrize("path", ["fresh_turn", "cached_agent"])
def test_override_pool_uses_effective_model(tmp_path, monkeypatch, path):
    """A default-model bench must not discard a supported override's pool (#132232)."""
    home = tmp_path / "profile"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(home))
    (home / "config.yaml").write_text(
        "model:\n  provider: openai-codex\n  default: benched-default\n"
        "auth:\n  adopt_external_logins: false\n"
    )
    (home / "auth.json").write_text(json.dumps({"credential_pool": {"openai-codex": [
        {"id": f"seat-{i}", "label": f"seat-{i}", "auth_type": "api_key",
         "source": "manual", "access_token": f"synthetic-key-{i}", "priority": i,
         "model_cooldowns": {"benched-default": time.time() + 3600}}
        for i in range(2)
    ]}}))
    from hermes_cli import config
    config._LOAD_CONFIG_CACHE.clear()
    config._RAW_CONFIG_CACHE.clear()
    runner = object.__new__(GatewayRunner)
    runner._session_model_overrides = {"session": {
        "model": "supported-override", "provider": "openai-codex",
        "api_key": "synthetic-key-0", "api_mode": "codex_responses",
        "base_url": "https://chatgpt.com/backend-api/codex",
    }}

    def resolve():
        if path == "fresh_turn":
            return runner._resolve_session_agent_runtime(session_key="session")
        return runner._apply_session_model_override("session", "benched-default", {})

    model, runtime = resolve()
    pool = runtime.get("credential_pool")
    assert model == "supported-override"
    assert pool is not None
    assert runtime["provider"] == "openai-codex"
    assert runtime["api_key"] == "synthetic-key-0"
    assert runtime["base_url"] == "https://chatgpt.com/backend-api/codex"
    assert len(pool.entries()) == 2
    assert pool.select(model=model) is not None
    assert pool.select(model="benched-default") is None

    # The same caller must still respect a cooldown for its actual model.
    runner._session_model_override("session")["model"] = "benched-default"
    _, blocked_runtime = resolve()
    assert blocked_runtime.get("credential_pool") is None
