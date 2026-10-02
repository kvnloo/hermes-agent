"""Tests for agent.rate_limit_tracker — header parsing and formatting."""

import time
import pytest
from agent.rate_limit_tracker import (
    RateLimitBucket,
    format_rate_limit_compact,
    format_rate_limit_display,
    parse_rate_limit_headers,
)

# ── Sample headers from Nous inference API ──────────────────────────────

NOUS_HEADERS = {
    "x-ratelimit-limit-requests": "800",
    "x-ratelimit-limit-requests-1h": "33600",
    "x-ratelimit-limit-tokens": "8000000",
    "x-ratelimit-limit-tokens-1h": "336000000",
    "x-ratelimit-remaining-requests": "795",
    "x-ratelimit-remaining-requests-1h": "33590",
    "x-ratelimit-remaining-tokens": "7999500",
    "x-ratelimit-remaining-tokens-1h": "335999000",
    "x-ratelimit-reset-requests": "45.5",
    "x-ratelimit-reset-requests-1h": "3500.0",
    "x-ratelimit-reset-tokens": "42.3",
    "x-ratelimit-reset-tokens-1h": "3490.0",
}

class TestParseHeaders:
    def test_basic_parsing(self):
        state = parse_rate_limit_headers(NOUS_HEADERS, provider="nous")
        assert state is not None
        assert state.provider == "nous"
        assert state.has_data

        assert state.requests_min.limit == 800
        assert state.requests_min.remaining == 795
        assert state.requests_min.reset_seconds == 45.5

        assert state.requests_hour.limit == 33600
        assert state.requests_hour.remaining == 33590

        assert state.tokens_min.limit == 8000000
        assert state.tokens_min.remaining == 7999500

        assert state.tokens_hour.limit == 336000000
        assert state.tokens_hour.remaining == 335999000
        assert state.tokens_hour.reset_seconds == 3490.0

    def test_no_headers(self):
        state = parse_rate_limit_headers({})
        assert state is None

    def test_missing_remaining_is_unknown_not_exhausted(self):
        # A limit without its remaining header must not read as "0 left":
        # remaining=0 is the real exhaustion signal, so an absent header is no data.
        state = parse_rate_limit_headers(
            {"x-ratelimit-limit-requests": "800", "x-ratelimit-reset-requests": "30"},
            provider="custom",
        )
        assert state is not None
        assert state.requests_min.usage_pct == 0.0
        assert not state.has_data
        assert format_rate_limit_compact(state) == "No rate limit data."

        # A present remaining of 0 is still genuine exhaustion.
        exhausted = parse_rate_limit_headers(
            {"x-ratelimit-limit-requests": "800", "x-ratelimit-remaining-requests": "0",
             "x-ratelimit-reset-requests": "120"},
            provider="custom",
        )
        assert exhausted.requests_min.usage_pct == 100.0
        assert "⚠ requests/min at 100%" in format_rate_limit_display(exhausted)

class TestBucket:

    def test_usage_pct(self):
        b = RateLimitBucket(limit=100, remaining=20, reset_seconds=30.0, captured_at=time.time())
        assert b.usage_pct == pytest.approx(80.0)

    def test_remaining_seconds_now(self):
        now = time.time()
        b = RateLimitBucket(limit=800, remaining=795, reset_seconds=60.0, captured_at=now - 10)
        # ~50 seconds should remain
        assert 49 <= b.remaining_seconds_now <= 51


@pytest.mark.parametrize("unknown_remaining", [None, "not-a-count"])
def test_response_capture_keeps_unknown_windows_distinct_from_exhaustion(unknown_remaining):
    """The native capture cache must not turn partial response headers into a breaker signal."""
    from httpx import Response

    from agent.nous_rate_guard import is_genuine_nous_rate_limit
    from agent.rate_limit_credits import RateLimitCreditsMixin

    class Agent(RateLimitCreditsMixin):
        provider = "nous"
        _rate_limit_state = None

    agent = Agent()
    partial = {
        "X-RateLimit-Limit-Requests": "800",
        "X-RateLimit-Reset-Requests": "3600",
    }
    if unknown_remaining is not None:
        partial["X-RateLimit-Remaining-Requests"] = unknown_remaining

    # A complete sibling window survives; the partial one supplies no exhaustion evidence.
    agent._capture_rate_limits(Response(200, headers={
        **partial,
        "X-RateLimit-Limit-Tokens": "100",
        "X-RateLimit-Remaining-Tokens": "75",
        "X-RateLimit-Reset-Tokens": "3600",
    }))
    state = agent.get_rate_limit_state()
    assert state is agent._rate_limit_state
    assert state.provider == "nous" and state.has_data
    assert state.requests_min.limit == 0
    assert (state.tokens_min.limit, state.tokens_min.remaining) == (100, 75)
    assert "TPM: 75/100" in format_rate_limit_compact(state)
    assert "RPM:" not in format_rate_limit_compact(state)
    assert not is_genuine_nous_rate_limit(headers=None, last_known_state=state)

    # Explicit zero still replaces the cache with genuine exhaustion.
    agent._capture_rate_limits(Response(200, headers={
        **partial, "X-RateLimit-Remaining-Requests": "0",
    }))
    exhausted = agent.get_rate_limit_state()
    assert exhausted.has_data and exhausted.requests_min.usage_pct == 100
    assert is_genuine_nous_rate_limit(headers=None, last_known_state=exhausted)

    # No relevant headers retain the last-known state, while a new partial report
    # replaces it with unknown rather than leaving a stale exhaustion signal cached.
    agent._capture_rate_limits(Response(200, headers={"Content-Type": "application/json"}))
    assert agent.get_rate_limit_state() is exhausted
    agent._capture_rate_limits(Response(200, headers=partial))
    unknown = agent.get_rate_limit_state()
    assert unknown is not exhausted and not unknown.has_data
    assert not is_genuine_nous_rate_limit(headers=None, last_known_state=unknown)
