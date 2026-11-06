"""Primary authentication errors must not silently switch the executing model."""

from unittest.mock import MagicMock

import pytest

from agent.error_classifier import classify_api_error
from agent.turn_recovery import route_classified_error


def _agent():
    agent = MagicMock()
    agent.provider = "custom"
    agent.compression_enabled = True
    agent._fallback_index = 0
    agent._fallback_chain = [{"provider": "openai-codex", "model": "gpt-6.1-sol"}]
    agent._credential_pool = None
    agent._try_activate_fallback.return_value = True
    return agent


def _route_auth_error(agent, status):
    error = Exception(f"Error code: {status} - You need to sign in to use this model.")
    error.status_code = status
    classified = classify_api_error(
        error, provider="custom", model="anthropic/claude-opus-5.5"
    )
    assert classified.is_auth, "fixture must exercise the auth-error branch"
    retry = MagicMock(auth_failover_attempted=False)
    return route_classified_error(
        agent, error, classified, retry,
        error_msg=str(error), error_context={}, recovered_with_pool=False,
        base_url="https://api.kilo.ai/api/gateway",
        model="anthropic/claude-opus-5.5",
        messages=[], api_messages=[], system_message="",
        active_system_prompt="", conversation_history=[],
        retry_count=0, max_retries=3,
        compression_attempts=0, max_compression_attempts=3,
        api_call_count=1, effective_task_id="auth-invariant",
    )


@pytest.mark.parametrize("status", [401, 403])
@pytest.mark.parametrize("explicit_opt_out", [False, True])
def test_auth_error_never_uses_fallback_by_default(status, explicit_opt_out):
    agent = _agent()
    if explicit_opt_out:
        agent._fallback_on_auth_error = False
    else:
        del agent._fallback_on_auth_error
    _route_auth_error(agent, status)
    agent._try_activate_fallback.assert_not_called()


def test_auth_error_fallback_requires_explicit_opt_in():
    agent = _agent()
    agent._fallback_on_auth_error = True
    _route_auth_error(agent, 401)
    agent._try_activate_fallback.assert_called_once()
