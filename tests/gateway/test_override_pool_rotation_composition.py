"""Synthetic composition proof for gateway attachment plus owner PR #132231."""

import json
import time
from pathlib import Path

import pytest

from gateway.run import GatewayRunner


@pytest.mark.parametrize("path", ["fresh_turn", "cached_override"])
def test_attached_override_pool_rotates_for_its_model(tmp_path, monkeypatch, path):
    home = tmp_path / "profile"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(home))
    (home / "config.yaml").write_text(
        "model:\n  provider: openai-codex\n  default: unavailable-model\n"
        "auth:\n  adopt_external_logins: false\n"
    )
    rows = [
        {"id": f"seat-{i}", "label": f"seat-{i}", "priority": i,
         "auth_type": "api_key", "source": "manual",
         "access_token": f"synthetic-key-{i}",
         "model_cooldowns": {"unavailable-model": time.time() + 3600}}
        for i in range(2)
    ]
    (home / "auth.json").write_text(json.dumps({"credential_pool": {"openai-codex": rows}}))
    from hermes_cli import config
    config._LOAD_CONFIG_CACHE.clear()
    config._RAW_CONFIG_CACHE.clear()
    runner = object.__new__(GatewayRunner)
    runner._session_model_overrides = {"session": {
        "model": "supported-model", "provider": "openai-codex",
        "api_key": rows[0]["access_token"], "api_mode": "codex_responses",
        "base_url": "https://chatgpt.com/backend-api/codex",
    }}
    if path == "fresh_turn":
        model, runtime = runner._resolve_session_agent_runtime(session_key="session")
    else:
        model, runtime = runner._apply_session_model_override("session", "unavailable-model", {})
    pool = runtime["credential_pool"]
    assert pool is not None
    assert model == "supported-model"
    assert runtime["api_key"] == rows[0]["access_token"]
    assert runtime["provider"] == "openai-codex"
    assert runtime["base_url"] == "https://chatgpt.com/backend-api/codex"

    replacement = pool.mark_exhausted_and_rotate(
        status_code=429, api_key_hint=runtime["api_key"],
        failure_reason="rate_limit", model=model,
        error_context={"reason": "usage_limit_reached", "reset_at": time.time() + 3600},
    )
    assert replacement is not None
    assert replacement.access_token == rows[1]["access_token"]
    assert pool.select(model="unavailable-model") is None
    assert pool.select(model=model).id == replacement.id
