"""A native Anthropic Kanban worker must not hide a missing primary key as unknown."""
import json
from types import SimpleNamespace

import pytest
import run_agent  # Bootstrap before the test home-I/O guard.

from agent import agent_init
from agent.auxiliary_unavailable import (
    ProviderCredentialsExhaustedError, ProviderNotConfiguredError,
)
from gateway import session_kanban
from hermes_cli.kanban_db import KANBAN_TERMINAL_PROVIDER_EXIT_CODE
from hermes_cli.turn_exit import credential_failure_flags, turn_exit_code


def _empty_anthropic(monkeypatch):
    monkeypatch.setattr("agent.anthropic_credentials.resolve_anthropic_token",
                        lambda **kwargs: None)
    monkeypatch.setattr("agent.auxiliary_unavailable.pool_billing_message",
                        lambda *args, **kwargs: None)
    monkeypatch.setattr("agent.auxiliary_unavailable.pool_cooldown_message",
                        lambda *args, **kwargs: None)
    monkeypatch.setattr("agent.anthropic_adapter.build_anthropic_client",
                        lambda *args, **kwargs: pytest.fail("empty key reached client construction"))
    return SimpleNamespace(provider="anthropic", model="claude-sonnet-4-5", quiet_mode=True)


def test_empty_anthropic_pool_records_terminal_config_error(monkeypatch):
    agent = _empty_anthropic(monkeypatch)
    with pytest.raises(ProviderNotConfiguredError, match="Provider 'anthropic'") as caught:
        agent_init._init_anthropic_client(agent, None, "https://api.anthropic.com", 30)
    assert caught.value.provider == "anthropic"
    flags = credential_failure_flags(caught.value)
    assert turn_exit_code(None, kanban_worker=True, **flags) == KANBAN_TERMINAL_PROVIDER_EXIT_CODE

    recorded = []
    monkeypatch.setattr(session_kanban, "_record_worker_result",
                        lambda ctx, code, output: recorded.append((ctx, code, output)))
    frame = {"policy": {"kanban_json": json.dumps({"run_id": 41})}}
    session_kanban.record_start_failure(frame, caught.value)
    assert recorded == [(
        {"run_id": 41}, KANBAN_TERMINAL_PROVIDER_EXIT_CODE,
        "config_error: no credentials for provider 'anthropic' (model.provider=anthropic)",
    )]


def test_anthropic_cooldown_is_not_a_missing_config(monkeypatch):
    agent = _empty_anthropic(monkeypatch)
    monkeypatch.setattr("agent.auxiliary_unavailable.pool_cooldown_message",
                        lambda provider: "Anthropic key is benched until quota resets")
    with pytest.raises(ProviderCredentialsExhaustedError) as caught:
        agent_init._init_anthropic_client(agent, None, "https://api.anthropic.com", 30)
    assert caught.value.provider == "anthropic"
    assert not credential_failure_flags(caught.value).get("credentials_terminal", False)
