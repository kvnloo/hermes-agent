"""Channel selection consumer for Enough1122's review of upstream PR #132231."""
import json
import time
from pathlib import Path

import httpx
import pytest

from gateway.config import ChannelOverride, GatewayConfig, Platform, PlatformConfig
from gateway.run import GatewayRunner
from gateway.session import SessionSource


@pytest.mark.parametrize("explicit_provider", [False, True], ids=["model-only", "model-and-provider"])
def test_channel_override_selects_credential_for_actual_model(tmp_path, monkeypatch, explicit_provider):
    home = tmp_path / "profile"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(home))
    (home / "config.yaml").write_text(
        "model:\n  provider: openai-codex\n  default: default-model\n"
        "auth:\n  adopt_external_logins: false\n"
    )
    rows = [
        {"id": f"seat-{i}", "label": f"seat-{i}", "priority": i,
         "auth_type": "api_key", "source": "manual", "access_token": f"synthetic-key-{i}",
         "model_cooldowns": {"channel-model": time.time() + 3600} if i == 0 else {}}
        for i in range(2)
    ]
    (home / "auth.json").write_text(json.dumps({"credential_pool": {"openai-codex": rows}}))

    def no_http(*args, **kwargs):
        raise AssertionError("This local selection proof must not make HTTP requests")

    monkeypatch.setattr(httpx.Client, "send", no_http)
    monkeypatch.setattr(httpx.AsyncClient, "send", no_http)
    from hermes_cli import config
    config._LOAD_CONFIG_CACHE.clear()
    config._RAW_CONFIG_CACHE.clear()
    runner = object.__new__(GatewayRunner)
    runner._session_model_overrides = {}
    runner.config = GatewayConfig(platforms={Platform.DISCORD: PlatformConfig(
        enabled=True, channel_overrides={"channel": ChannelOverride(
            model="channel-model", provider="openai-codex" if explicit_provider else None)})})
    source = SessionSource(platform=Platform.DISCORD, chat_id="channel", user_id="synthetic-user")

    model, runtime = runner._resolve_session_agent_runtime(source=source, session_key="synthetic-session")
    assert model == "channel-model"
    assert runtime["provider"] == "openai-codex"
    eligible = runtime["credential_pool"].select(model=model)
    assert eligible is not None
    assert eligible.id == "seat-1"
    assert runtime["api_key"] == eligible.runtime_api_key
