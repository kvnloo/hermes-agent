"""The real buffered retry producer obeys the Telegram-only status policy (#125484)."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from agent.status_output import StatusOutputMixin
from agent.turn_recovery import compute_error_backoff
from gateway.config import Platform
from gateway.run import GatewayRunner
from gateway.run_turn_runner import TurnRunner
from gateway.session import SessionSource
from gateway.turn_context import TurnContext


@pytest.mark.parametrize("platform", [Platform.TELEGRAM, Platform.SLACK], ids=["telegram", "slack"])
@pytest.mark.parametrize("reset_source", ["absent", "retry-after", "body-reset"])
@pytest.mark.parametrize("suppressed", [False, True], ids=["visible", "suppressed"])
@pytest.mark.parametrize("recovered", [False, True], ids=["exhausted", "recovered"])
def test_real_buffered_rate_limit_status_keeps_platform_policy(
    monkeypatch, record_property, platform, reset_source, suppressed, recovered,
):
    from gateway import run
    from agent import retry_utils

    # Hold the fallback wait constant; this contract concerns presentation, not backoff policy.
    monkeypatch.setattr(retry_utils, "jittered_backoff", lambda *a, **k: 17.0)
    monkeypatch.setattr(retry_utils, "adaptive_rate_limit_backoff",
                        lambda *a, **k: (k["default_wait"], None))

    sent, live_waits = [], []

    async def send(chat_id, text, **kwargs):
        sent.append({"chat_id": chat_id, "text": text, "metadata": kwargs.get("metadata")})
        return SimpleNamespace(success=True)

    class RetryAgent(StatusOutputMixin):
        suppress_status_output = True
        log_prefix = ""

        def _touch_activity(self, _text):
            pass

        def _client_log_context(self):
            return "local synthetic rate-limit fixture"

    config = {"display": {"suppress_warning_notifications": suppressed}}
    source = SessionSource(platform=platform, chat_id="fixture-chat", user_id="fixture-user")
    ctx = TurnContext(
        source=source, user_config=config, _run_still_current=lambda: True,
        _status_adapter=SimpleNamespace(send=send), _status_chat_id=source.chat_id,
        _status_thread_metadata={"thread_id": "fixture-thread"},
    )
    gateway = object.__new__(GatewayRunner)
    agent = RetryAgent()
    agent._notification_platform = platform
    agent._notification_config = config
    agent.status_callback = TurnRunner(gateway, ctx)._status_callback_sync
    agent.thinking_callback = live_waits.append
    monkeypatch.setattr(run, "safe_schedule_threadsafe", lambda coro, *a, **k: asyncio.run(coro))

    error = Exception("HTTP 429: The usage limit has been reached")
    error.response = SimpleNamespace(headers={} if reset_source == "absent" else {"retry-after": "17"})
    error.body = {"error": {"type": "usage_limit_reached", "message": "The usage limit has been reached"}}
    if reset_source == "body-reset":
        error.body["error"]["resets_in_seconds"] = 756
    wait = compute_error_backoff(
        agent, error, retry_count=1, max_retries=3, is_rate_limited=True,
        is_zai_coding_overload=False, base_url="https://example.invalid/v1", model="fixture-model",
    )
    assert wait == 17
    assert sent == []  # The status buffer does not promise an immediate chat notice.
    assert len(live_waits) == 1
    assert len(agent._retry_status_buffer) == 1
    buffered = str(agent._retry_status_buffer[0][1])
    assert ("Resets in" in buffered) is (reset_source != "absent")
    if reset_source == "body-reset":
        assert "Resets in ~13m." in buffered
    elif reset_source == "retry-after":
        assert "Resets in ~17s." in buffered

    if recovered:
        agent._clear_status_buffer()
    else:
        agent._flush_status_buffer()
    first_delivery = list(sent)
    agent._flush_status_buffer()
    observation = {
        "platform": platform.value, "reset_source": reset_source, "suppressed": suppressed,
        "recovered": recovered, "wait": wait, "buffered": buffered,
        "live_waits": [str(x) for x in live_waits], "sent": sent,
        "buffer_empty": not agent._retry_status_buffer, "second_flush_replayed": sent != first_delivery,
    }
    record_property("rate_limit_status_observation", json.dumps(observation, sort_keys=True))
    expected = ([{"chat_id": source.chat_id, "text": f"⚠️ {buffered}",
                  "metadata": {"thread_id": "fixture-thread"}}]
                if platform == Platform.TELEGRAM and not suppressed and not recovered else [])
    assert observation["buffer_empty"] and not observation["second_flush_replayed"]
    assert sent == expected
