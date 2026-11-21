"""A 403 written by a WAF/CDN in front of the provider is not an API-key rejection (#53099, #70566).

A relay that blocks the SDK User-Agent answers ``403 Your request was blocked.``; Cloudflare's
browser challenge answers 403 HTML. Both used to classify as ``auth`` and print key guidance.
"""
import pytest

from agent.error_classifier import FailoverReason, classify_api_error


class _APIError(Exception):
    def __init__(self, message, status_code, body=None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


@pytest.mark.parametrize("body", [
    "Error code: 403 - Your request was blocked.",
    "<!doctype html><html><body>Enable JavaScript and cookies to continue</body></html>",
    "<!doctype html><html><script src='/cdn-cgi/challenge-platform/h/g/orchestrate/chl_page'></script></html>",
])
def test_403_waf_block_is_upstream_blocked_not_auth(body):
    result = classify_api_error(_APIError(body, 403), provider="openai-api")
    assert result.reason == FailoverReason.upstream_blocked
    assert result.retryable is False and result.should_fallback is True
    assert result.should_rotate_credential is False and result.is_auth is False


@pytest.mark.parametrize("body, status, reason", [
    ("<html><title>Forbidden</title><body>Access denied</body></html>", 403, FailoverReason.auth),
    ("<html>Enable JavaScript and cookies to continue</html>", 401, FailoverReason.auth),
])
def test_generic_403_and_all_401_keep_auth(body, status, reason):
    assert classify_api_error(_APIError(body, status), provider="openai-api").reason == reason


def test_openrouter_security_policy_403_keeps_valid_key():
    """Regression for #150920: an edge security refusal must not exhaust a working API key."""
    body = {"success": False, "error": "Access denied by security policy."}
    result = classify_api_error(
        _APIError(f"Error code: 403 - {body}", 403, body=body),
        provider="openrouter", base_url="https://openrouter.ai/api/v1",
    )
    assert result.reason == FailoverReason.upstream_blocked
    assert result.retryable is False and result.should_fallback is True
    assert result.should_rotate_credential is False and result.is_auth is False

    # A provider-owned permission response with the same wording is not an edge envelope.
    permission = classify_api_error(
        _APIError("Access denied by security policy.", 403,
                  body={"error": {"message": "Access denied by security policy."}}),
        provider="openrouter",
    )
    assert permission.reason == FailoverReason.auth
