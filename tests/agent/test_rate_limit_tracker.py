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

class TestBucket:

    def test_usage_pct(self):
        b = RateLimitBucket(limit=100, remaining=20, reset_seconds=30.0, captured_at=time.time())
        assert b.usage_pct == pytest.approx(80.0)

    def test_remaining_seconds_now(self):
        now = time.time()
        b = RateLimitBucket(limit=800, remaining=795, reset_seconds=60.0, captured_at=now - 10)
        # ~50 seconds should remain
        assert 49 <= b.remaining_seconds_now <= 51


class TestPartialHeaders:
    """Unknown remaining values must not masquerade as an exhausted quota.

    Regression for the closed, unmerged downstream PR #47.
    """

    @pytest.mark.parametrize("remaining", [None, "unavailable"])
    def test_missing_or_invalid_remaining_has_no_quota_data(self, remaining):
        headers = {
            "x-ratelimit-limit-requests": "800",
            "x-ratelimit-reset-requests": "120",
        }
        if remaining is not None:
            headers["x-ratelimit-remaining-requests"] = remaining

        state = parse_rate_limit_headers(headers, provider="nous")
        assert state is not None
        assert not state.has_data
        assert state.requests_min.limit == 0
        assert state.requests_min.reset_seconds == 0
        assert format_rate_limit_compact(state) == "No rate limit data."
        assert format_rate_limit_display(state) == (
            "No rate limit data yet — make an API request first."
        )

    def test_missing_limit_is_also_unknown(self):
        state = parse_rate_limit_headers(
            {"x-ratelimit-remaining-requests": "50"}, provider="nous"
        )
        assert state is not None
        assert not state.has_data
        assert state.requests_min.limit == 0
        assert format_rate_limit_compact(state) == "No rate limit data."

    def test_mixed_complete_and_partial_windows_keep_valid_quota(self):
        state = parse_rate_limit_headers(
            {
                "x-ratelimit-limit-requests": "800",
                "x-ratelimit-reset-requests": "120",
                "x-ratelimit-limit-tokens": "1000",
                "x-ratelimit-remaining-tokens": "450",
            },
            provider="nous",
        )
        assert state is not None and state.has_data
        assert state.requests_min.limit == 0
        assert state.tokens_min.limit == 1000
        assert state.tokens_min.remaining == 450
        assert state.tokens_min.usage_pct == pytest.approx(55.0)
        assert "TPM: 450/1000" in format_rate_limit_compact(state)
        assert "RPM:" not in format_rate_limit_compact(state)
        rendered = format_rate_limit_display(state)
        assert "(no data)" in rendered
        assert "55.0%" in rendered
        assert "⚠" not in rendered

    def test_present_zero_remaining_still_warns_without_reset(self):
        state = parse_rate_limit_headers(
            {
                "x-ratelimit-limit-requests": "800",
                "x-ratelimit-remaining-requests": "0",
            },
            provider="nous",
        )
        assert state is not None and state.has_data
        assert state.requests_min.limit == 800
        assert state.requests_min.usage_pct == 100.0
        assert "⚠ requests/min at 100%" in format_rate_limit_display(state)
        assert "RPM: 0/800" in format_rate_limit_compact(state)
