"""Tests for agent.rate_limit_tracker — header parsing and formatting."""

import time
import pytest
from agent.rate_limit_tracker import (
    RateLimitBucket,
    RateLimitState,
    parse_rate_limit_headers,
    format_rate_limit_display,
    format_rate_limit_compact,
    _fmt_count,
    _fmt_seconds,
    _bar,
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



class TestFormatting:



    def test_fmt_seconds_short(self):
        assert _fmt_seconds(45) == "45s"
        assert _fmt_seconds(0) == "0s"



    def test_bar(self):
        bar = _bar(50.0, width=10)
        assert bar == "[█████░░░░░]"
        assert _bar(0.0, width=10) == "[░░░░░░░░░░]"
        assert _bar(100.0, width=10) == "[██████████]"




    def test_format_compact(self):
        state = parse_rate_limit_headers(NOUS_HEADERS, provider="nous")
        result = format_rate_limit_compact(state)
        assert "RPM:" in result
        assert "RPH:" in result
        assert "TPM:" in result
        assert "TPH:" in result
        assert "resets" in result



class TestAgentIntegration:
    """Test that AIAgent captures rate limit state correctly."""

    def test_capture_rate_limits_from_headers(self):
        """Simulate the header capture path without a real API call."""
        # Use a mock httpx-like response
        class MockResponse:
            headers = NOUS_HEADERS

        # Import AIAgent minimally

        # Test the parsing directly
        state = parse_rate_limit_headers(MockResponse.headers, provider="nous")
        assert state is not None
        assert state.requests_min.limit == 800
        assert state.tokens_hour.limit == 336000000

    def test_capture_rate_limits_none_response(self):
        """_capture_rate_limits should handle None gracefully."""
        from agent.rate_limit_tracker import parse_rate_limit_headers
        # None should not crash
        result = parse_rate_limit_headers({})
        assert result is None


class TestPartialHeaders:
    """A bucket missing one side of limit/remaining renders as '(no data)',
    not a fabricated 100%-exhausted bucket.

    Regression for the bug where a response carrying only
    ``x-ratelimit-limit-*`` (no matching ``x-ratelimit-remaining-*``)
    defaulted ``remaining`` to ``0`` and rendered a false 100% usage plus a
    spurious ``⚠`` warning, with no way to distinguish "missing" from
    "genuinely exhausted".
    """

    def test_missing_remaining_treated_as_no_data(self):
        state = parse_rate_limit_headers(
            {"x-ratelimit-limit-requests": "800"}, provider="custom"
        )
        assert state is not None
        bucket = state.requests_min
        assert bucket.limit == 0
        assert bucket.remaining == 0
        assert bucket.reset_seconds == 0.0
        assert bucket.usage_pct == 0.0
        assert state.has_data is False
        assert format_rate_limit_compact(state) == "No rate limit data."
        rendered = format_rate_limit_display(state)
        assert "⚠" not in rendered
        assert "100.0%" not in rendered

    def test_missing_limit_treated_as_no_data(self):
        # Symmetry: the inverse case (only remaining, no limit) must also
        # collapse to "(no data)", not render a percentage.
        state = parse_rate_limit_headers(
            {"x-ratelimit-remaining-requests": "10"}, provider="custom"
        )
        assert state is not None
        bucket = state.requests_min
        assert bucket.limit == 0
        assert bucket.remaining == 0
        assert bucket.usage_pct == 0.0
        assert state.has_data is False
        assert format_rate_limit_compact(state) == "No rate limit data."

    def test_missing_reset_still_complete_when_limit_and_remaining_present(self):
        # If limit and remaining are present but reset is missing, the bucket
        # is still meaningful; reset only affects the cosmetic 'resets in' text.
        state = parse_rate_limit_headers(
            {
                "x-ratelimit-limit-requests": "800",
                "x-ratelimit-remaining-requests": "795",
            },
            provider="custom",
        )
        bucket = state.requests_min
        assert bucket.limit == 800
        assert bucket.remaining == 795
        assert bucket.usage_pct == pytest.approx(0.625, abs=0.01)
        assert state.has_data is True

    def test_mixed_partial_and_complete_buckets(self):
        # A partial bucket renders as "(no data)" while a complete bucket in
        # the same response renders its real values; the compact form omits
        # the partial bucket's part.
        state = parse_rate_limit_headers(
            {
                "x-ratelimit-limit-requests": "800",
                "x-ratelimit-limit-tokens": "10000",
                "x-ratelimit-remaining-tokens": "5000",
                "x-ratelimit-reset-tokens": "30.0",
            },
            provider="custom",
        )
        assert state.requests_min.limit == 0
        assert state.requests_min.remaining == 0
        assert state.tokens_min.limit == 10000
        assert state.tokens_min.remaining == 5000
        assert state.tokens_min.usage_pct == pytest.approx(50.0)
        assert state.has_data is True
        compact = format_rate_limit_compact(state)
        assert "TPM" in compact
        assert "RPM" not in compact
        rendered = format_rate_limit_display(state)
        assert "(no data)" in rendered
        assert "50.0%" in rendered
        assert "⚠" not in rendered

    def test_genuine_zero_remaining_still_reports_exhaustion(self):
        # A present limit with a present remaining of 0 is genuine exhaustion
        # and must still render 100% plus a warning — distinguishing a real
        # "0 left" from a missing header, which is the whole point of the fix.
        state = parse_rate_limit_headers(
            {
                "x-ratelimit-limit-requests": "800",
                "x-ratelimit-remaining-requests": "0",
                "x-ratelimit-reset-requests": "120.0",
            },
            provider="custom"
        )
        bucket = state.requests_min
        assert bucket.limit == 800
        assert bucket.remaining == 0
        assert bucket.usage_pct == 100.0
        assert state.has_data is True
        rendered = format_rate_limit_display(state)
        assert "100.0%" in rendered
        assert "⚠ requests/min at 100%" in rendered
        assert "RPM: 0/800" in format_rate_limit_compact(state)


class TestHasData:
    """``has_data`` reflects whether any usable bucket was captured, not
    merely that some rate-limit header was seen at all."""

    def test_empty_state_has_data_false(self):
        assert RateLimitState().has_data is False

    def test_all_no_data_buckets_has_data_false(self):
        # Headers were present (so the parser returns a state, not None) but
        # no bucket is complete — must not claim data to show the user.
        state = parse_rate_limit_headers(
            {"x-ratelimit-limit-requests": "800"}, provider="custom"
        )
        assert state is not None
        assert state.has_data is False

    def test_at_least_one_usable_bucket_has_data_true(self):
        state = parse_rate_limit_headers(
            {
                "x-ratelimit-limit-requests": "800",
                "x-ratelimit-limit-tokens": "10000",
                "x-ratelimit-remaining-tokens": "5000",
            },
            provider="custom",
        )
        assert state.has_data is True

    def test_complete_headers_has_data_true(self):
        state = parse_rate_limit_headers(NOUS_HEADERS, provider="nous")
        assert state.has_data is True
