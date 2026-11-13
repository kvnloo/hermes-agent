"""Foundry tool + reasoning 400 switches the wire, rather than dropping reasoning.

Regression for NousResearch/hermes-agent#120263: #139489 handles initial route
selection; a stale chat route must recover using Azure's explicit endpoint hint.
"""
from unittest.mock import patch

from agent.error_classifier import classify_api_error
from agent.turn_recovery import recover_after_classification
from agent.turn_retry_state import TurnRetryState


class _AzureToolError(Exception):
    def __init__(self, model):
        message = (
            f"Function tools with reasoning_effort are not supported for {model} "
            "in /v1/chat/completions. To use function tools, use /v1/responses "
            "or set reasoning_effort to 'none'."
        )
        super().__init__(f"Error code: 400 - {message}")
        self.status_code = 400
        self.message = message
        self.body = {"error": {"message": message, "type": "invalid_request_error"}}


class _Agent:
    log_prefix = ""

    def __init__(self, model, provider="azure-foundry"):
        self.model = model
        self.provider = provider
        self.base_url = "https://resource.services.ai.azure.com/openai/v1"
        self.api_mode = "chat_completions"
        self.client = object()
        self._client_kwargs = {"api_key": "test-key", "base_url": self.base_url}
        self._transport_cache = {"chat_completions": object()}
        self._wire_reasoning_config = {"enabled": True, "effort": "high"}
        self._reasoning_effort_rejected = False
        self.notices = []

    def _recover_with_credential_pool(self, **kwargs):
        return False, False

    def _vprint(self, message, **kwargs):
        self.notices.append(message)


def _recover(agent, error, retry):
    classified = classify_api_error(
        error, provider=agent.provider, model=agent.model, base_url=agent.base_url,
    )
    with patch("hermes_cli.models_reasoning_caps.refresh_reasoning_caps_async", lambda provider: None):
        return recover_after_classification(
            agent, error, classified, retry, status_code=400, error_context={},
            messages=[], api_messages=[],
        )


def test_azure_foundry_function_tools_error_switches_transport_once():
    for model in ("gpt-6-luna", "gpt-6.1-sol"):
        agent = _Agent(model)
        retry = TurnRetryState()
        recovered, pool = _recover(agent, _AzureToolError(model), retry)
        assert recovered is True
        assert pool is False
        assert retry.azure_responses_switch_attempted is True
        assert agent.api_mode == "codex_responses"
        assert agent.client is None
        assert agent._transport_cache == {}
        assert agent._client_kwargs == {
            "api_key": "test-key", "base_url": agent.base_url,
        }, "transport repair must retain Azure credentials"
        assert agent._reasoning_effort_rejected is False
        assert any("switching wire" in notice for notice in agent.notices)

    # A superficially identical 400 on another provider must not switch its wire.
    other = _Agent("gpt-6-luna", provider="custom")
    _recover(other, _AzureToolError("gpt-6-luna"), TurnRetryState())
    assert other.api_mode == "chat_completions"
