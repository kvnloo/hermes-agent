import time
from unittest.mock import MagicMock


# A 429 from an Anthropic subscription (OAuth) carries its reset only in the unified rate-limit
# headers (epoch seconds). With fallbacks off for interactive profiles, the failed turn must still
# say when the limit lifts: "Limit resets at HH:MM".
def _anthropic_429(headers):
    err = Exception("Error code: 429 - rate_limit_error: This request would exceed your account's rate limit.")
    err.status_code = 429
    err.response = MagicMock(headers=headers)
    return err


def test_anthropic_unified_reset_names_the_reset_time():
    from agent.agent_runtime_helpers import extract_api_error_context
    from agent.turn_failure_copy import limit_reset_copy
    from agent.credential_pool import _parse_absolute_timestamp
    reset = int(time.time()) + 2 * 3600
    ctx = extract_api_error_context(_anthropic_429({
        "anthropic-ratelimit-unified-status": "rejected",
        "anthropic-ratelimit-unified-reset": str(reset),
    }))
    at = _parse_absolute_timestamp(ctx["reset_at"])
    assert abs(at - reset) < 2
    assert limit_reset_copy(at).startswith(f"Limit resets at {time.strftime('%H:%M', time.localtime(reset))}")


def test_retry_after_still_wins_over_unified_reset():
    from agent.agent_runtime_helpers import extract_api_error_context
    from agent.credential_pool import _parse_absolute_timestamp
    ctx = extract_api_error_context(_anthropic_429({
        "retry-after": "30", "anthropic-ratelimit-unified-reset": str(int(time.time()) + 7200)}))
    assert _parse_absolute_timestamp(ctx["reset_at"]) - time.time() < 60
