"""LiteLLM proxy authentication recovery (NousResearch/hermes-agent#150575)."""

import pytest

from agent.error_classifier import FailoverReason, classify_api_error


@pytest.mark.parametrize(
    ("message", "in_body"),
    [
        ("No connected db.", True),
        ("No api key passed in.", False),
    ],
)
def test_400_proxy_auth_rejection_rotates(message, in_body):
    error = Exception("Error code: 400" if in_body else message)
    error.status_code = 400
    error.body = {"error": {"message": message}} if in_body else {}

    result = classify_api_error(error, provider="custom", api_key="sk-proxy")

    assert result.reason is FailoverReason.auth
    assert result.should_rotate_credential is True
    assert result.retryable is False


@pytest.mark.parametrize(
    ("status", "message", "expected_reason"),
    [
        (400, "Invalid parameter: tools", FailoverReason.format_error),
        (503, "No connected db.", FailoverReason.overloaded),
    ],
)
def test_other_proxy_errors_do_not_rotate(status, message, expected_reason):
    error = Exception(f"Error code: {status}")
    error.status_code = status
    error.body = {"error": {"message": message}}

    result = classify_api_error(error, provider="custom", api_key="sk-proxy")

    assert result.reason is expected_reason
    assert result.should_rotate_credential is False
