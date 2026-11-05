"""Fallback invariants from oss-factory #314 and #316.

#316: a 401/403 that survives credential refresh fails the turn; it never runs another model
      unless the agent opts in with ``_fallback_on_auth_error``.
#314: while a session stays pinned to a fallback, every turn announces which model is answering
      and until when, instead of keeping the primary's label silently.
"""

import time
from unittest.mock import MagicMock

import pytest

from agent import agent_runtime_helpers as arh
from agent.error_classifier import classify_api_error
from agent.turn_recovery import route_classified_error


def _auth_error(status=401):
    err = Exception(f"Error code: {status} - You need to sign in to use this model.")
    err.status_code = status
    return err


def _route(agent, err):
    classified = classify_api_error(err, provider="custom", model="anthropic/claude-opus-5.5")
    retry = MagicMock(auth_failover_attempted=False)
    return route_classified_error(
        agent, err, classified, retry, error_msg=str(err), error_context={}, recovered_with_pool=False,
        base_url="https://api.kilo.ai/api/gateway", model="anthropic/claude-opus-5.5", messages=[],
        api_messages=[], system_message="", active_system_prompt="", conversation_history=[],
        retry_count=0, max_retries=3, compression_attempts=0, max_compression_attempts=3,
        api_call_count=1, effective_task_id="t",
    )


def _agent(**kw):
    agent = MagicMock()
    agent.provider = "custom"
    agent.compression_enabled = True
    agent._fallback_index = 0
    agent._fallback_chain = [{"provider": "openai-codex", "model": "gpt-6.1-sol"}]
    agent._credential_pool = None
    agent._try_activate_fallback.return_value = True
    for k, v in kw.items():
        setattr(agent, k, v)
    return agent


@pytest.mark.parametrize("status", [401, 403])
def test_auth_error_does_not_fall_back_by_default(status):
    agent = _agent()
    del agent._fallback_on_auth_error  # attribute absent -> default (fail closed)
    _route(agent, _auth_error(status))
    agent._try_activate_fallback.assert_not_called()


def test_auth_error_falls_back_only_when_opted_in():
    agent = _agent(_fallback_on_auth_error=True)
    _route(agent, _auth_error(401))
    agent._try_activate_fallback.assert_called_once()


def _pinned_agent(remaining_s):
    agent = MagicMock()
    agent._fallback_activated = True
    agent._primary_runtime = {"provider": "anthropic", "model": "claude-opus-5-5", "base_url": ""}
    agent.model, agent.provider = "gpt-6.1-sol", "openai-codex"
    agent._rate_limited_until = time.monotonic() + remaining_s
    agent._entitlement_rejected_models = set()
    return agent


def test_pinned_turn_announces_fallback_and_reset_time(monkeypatch):
    monkeypatch.setattr("agent.fallback_cooldown._is_entitlement_rejected", lambda *a: False)
    agent = _pinned_agent(3600)
    assert arh.restore_primary_runtime(agent) is False
    agent._emit_diagnostic_status.assert_called_once()
    msg = agent._emit_diagnostic_status.call_args[0][0]
    until = time.strftime("%H:%M", time.localtime(time.time() + 3600))
    assert "gpt-6.1-sol" in msg and "openai-codex" in msg
    assert f"until {until}" in msg and "claude-opus-5-5 rate-limited" in msg


def test_announce_never_raises(monkeypatch):
    monkeypatch.setattr("agent.fallback_cooldown._is_entitlement_rejected", lambda *a: False)
    agent = _pinned_agent(60)
    agent._emit_diagnostic_status.side_effect = RuntimeError("surface down")
    assert arh.restore_primary_runtime(agent) is False
