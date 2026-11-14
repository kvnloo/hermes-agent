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


@pytest.mark.parametrize("provider, status, body", [
    ("openai", 403, {"success": False, "error": "Access denied by security policy."}),
    ("openrouter", 401, {"success": False, "error": "Access denied by security policy."}),
    ("openrouter", 403, {"success": True, "error": "Access denied by security policy."}),
    ("openrouter", 403, {"success": 0, "error": "Access denied by security policy."}),
    ("openrouter", 403, {"error": "Access denied by security policy."}),
    ("openrouter", 403, {"success": False, "error": "Access denied."}),
])
def test_security_policy_exception_requires_exact_openrouter_envelope(provider, status, body):
    result = classify_api_error(_APIError(str(body), status, body=body), provider=provider)
    assert result.reason == FailoverReason.auth


def test_openrouter_security_policy_turn_preserves_pool_key(monkeypatch):
    """Drive a real SDK 403 through the turn loop without contacting a provider."""
    import httpx

    from agent.credential_pool import CredentialPool, PooledCredential
    from run_agent import AIAgent

    requests = []

    def deny(request):
        requests.append(request)
        return httpx.Response(403, json={"success": False, "error": "Access denied by security policy."})

    monkeypatch.setattr(
        AIAgent, "_build_keepalive_http_client",
        lambda self, *args, **kwargs: httpx.Client(transport=httpx.MockTransport(deny)),
    )
    key = PooledCredential("openrouter", "test-key", "test", "api_key", 0, "manual", "sk-test")
    pool = CredentialPool("openrouter", [key])
    agent = AIAgent(
        api_key="sk-test", base_url="https://openrouter.ai/api/v1", provider="openrouter",
        api_mode="chat_completions", model="openai/gpt-4.1-nano", quiet_mode=True,
        skip_context_files=True, skip_memory=True, enabled_toolsets=[], max_iterations=1,
        credential_pool=pool, save_trajectories=False,
    )
    try:
        result = agent.run_conversation("ping", conversation_history=[], task_id="security-policy-test")
    finally:
        agent.client.close()

    assert len(requests) == 1
    assert requests[0].url.path == "/api/v1/chat/completions"
    assert result["failed"] is True
    assert result["failure_reason"] == "upstream_blocked"
    assert result["failure_retryable"] is False
    assert "firewall" in result["final_response"].lower()
    assert pool.entries()[0].last_status is None
    assert pool.has_available()
