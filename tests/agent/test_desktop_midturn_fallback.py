"""Desktop 429 recovery: mid-turn fallbacks and unavailable-chain terminal (#156481)."""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.error_classifier import FailoverReason, classify_api_error
from agent.turn_api_error import settle_unrecovered_error
from agent.turn_recovery import route_classified_error
from agent.turn_retry_state import TurnRetryState


class _RateLimitError(Exception):
    status_code = 429

    def __init__(self, *, retry_after=True):
        super().__init__("This request would exceed your account's rate limit. Please try again later.")
        self.response = SimpleNamespace(headers={"Retry-After": "18000"} if retry_after else {}, status_code=429)
        self.body = {"error": {"type": "rate_limit_error", "message": str(self)}}


def _agent():
    agent = SimpleNamespace(
        provider="moa", model="default", base_url="http://127.0.0.1:9/v1",
        log_prefix="", compression_enabled=True, _credential_pool=None,
        _fallback_chain=[], _fallback_model=None, _fallback_index=0,
        _fallback_activated=False, _rate_limited_until=0, _unavailable_fallback_keys=set(),
        _auto_recovery_cycles=0, _buffer_diagnostic_status=lambda _: None,
        _try_recover_primary_transport=lambda *a, **k: False,
    )
    agent._has_pending_fallback = lambda: agent._fallback_index < len(agent._fallback_chain)
    agent._try_activate_fallback = lambda **kw: bool(agent._fallback_chain)
    return agent


@contextmanager
def _desktop(*, locked=False):
    policy = SimpleNamespace(source="gui", safe_mode=False, ignore_user_config=False)
    with patch("gateway.session_policy.active_policy", return_value=policy), patch(
        "gateway.session_api_turn.api_runtime_locked", return_value={"confirmed": True} if locked else None
    ):
        yield


def test_desktop_429_adopts_midturn_fallback_and_restarts(tmp_path, monkeypatch):
    """A fallback added after turn admission must be tried on that same failed model call."""
    from hermes_cli.config import get_config_path

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    cfg = get_config_path()
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("fallback_providers:\n  - provider: deepseek\n    model: deepseek-chat\n", encoding="utf-8")
    agent, error = _agent(), _RateLimitError()
    classified = classify_api_error(error, provider=agent.provider, model=agent.model)
    assert classified.reason == FailoverReason.rate_limit
    with _desktop(), patch(
        "agent.conversation_loop._ra",
        return_value=SimpleNamespace(_pool_may_recover_from_rate_limit=lambda pool: False),
    ), patch("agent.conversation_loop._arm_fallback_restart", lambda a, m, s, r: s):
        verdict = route_classified_error(
            agent, error, classified, TurnRetryState(), error_msg=str(error).lower(), error_context={},
            recovered_with_pool=False, base_url=agent.base_url, model=agent.model,
            messages=[], api_messages=[], system_message=None, active_system_prompt=None,
            conversation_history=None, retry_count=1, max_retries=3, compression_attempts=0,
            max_compression_attempts=3, api_call_count=1, effective_task_id=None,
        )
    assert verdict.action == "break"
    assert agent._fallback_chain == [{"provider": "deepseek", "model": "deepseek-chat"}]


@pytest.mark.parametrize("retry_after", [True, False])
def test_desktop_429_without_usable_fallback_ends_without_wait(retry_after):
    """An account limit of five hours must not schedule the capped 600-second retry."""
    agent, error = _agent(), _RateLimitError(retry_after=retry_after)
    classified = classify_api_error(error, provider=agent.provider, model=agent.model)
    assert classified.reason == FailoverReason.rate_limit
    with _desktop(), patch(
        "agent.turn_api_error.interruptible_backoff_sleep",
        side_effect=AssertionError("unusable fallback must not back off"),
    ), patch("agent.turn_api_error.max_retries_exhausted_result", return_value={"failed": True}):
        verdict = settle_unrecovered_error(
            agent, api_error=error, classified=classified, _retry=TurnRetryState(),
            status_code=429, error_msg=str(error).lower(), error_context={},
            is_context_length_error=False, is_rate_limited=True, _is_zai_coding_overload=False,
            _provider=agent.provider, _base=agent.base_url, _model=agent.model,
            messages=[], api_messages=[], api_kwargs=None, active_system_prompt=None,
            conversation_history=None, approx_tokens=0, retry_count=1, max_retries=3,
            compression_attempts=0, api_call_count=1,
        )
    assert verdict.action == "return"
    assert verdict.result == {"failed": True}
