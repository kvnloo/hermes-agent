"""Copilot Responses physical retries must renew watchdog state (#153115)."""

from __future__ import annotations

from types import SimpleNamespace

from agent.chat_completion_nonstream import _NonStreamRequest
from agent.codex_runtime import _codex_watchdog_state_var, run_codex_stream
from tests.agent.test_codex_ttfb_watchdog import _make_codex_agent


def test_copilot_retry_rearms_first_event_and_event_idle_watchdogs(tmp_path, monkeypatch):
    """A new physical attempt cannot inherit old SSE activity or keep idle suppressed."""
    monkeypatch.delenv("HERMES_CODEX_EVENT_STALE_TIMEOUT_SECONDS", raising=False)
    agent = _make_codex_agent(
        tmp_path, monkeypatch,
        provider="copilot", base_url="https://api.githubcopilot.com",
    )
    # Restore the real stale budget (the shared helper shortens it for time-based tests).
    monkeypatch.delattr(agent, "_compute_non_stream_stale_timeout")
    kwargs = {"model": "gpt-6.1-sol", "input": "hi"}
    request = _NonStreamRequest(agent, kwargs)
    assert request.wd.idle_enabled and not request.wd.idle_requires_progress

    state = request.codex_watchdog_state
    seen = {}
    attempts = []

    def snapshot():
        with state.lock:
            return state.last_event_ts, state.last_progress_ts, state.retry_started_ts

    class Events:
        def __init__(self, attempt):
            self.attempt = attempt

        def __iter__(self):
            yield SimpleNamespace(type="response.created")
            if self.attempt == 1:
                yield SimpleNamespace(type="response.reasoning_text.delta", delta="started")
                seen["prior"] = snapshot()
                raise ConnectionError("physical connection dropped")
            seen["lifecycle"] = snapshot()
            yield SimpleNamespace(
                type="response.completed",
                response=SimpleNamespace(id="response-2", status="completed", usage=None),
            )

        def close(self):
            pass

    def create(**_kwargs):
        attempt = len(attempts) + 1
        attempts.append(attempt)
        if attempt == 2:
            seen["retry_open"] = snapshot()
        return Events(attempt)

    client = SimpleNamespace(
        base_url="https://api.githubcopilot.com",
        responses=SimpleNamespace(create=create),
    )
    request._install_codex_request_token()
    token = _codex_watchdog_state_var.set(state)
    try:
        response = run_codex_stream(agent, kwargs, client=client)
    finally:
        _codex_watchdog_state_var.reset(token)
        request._retire_codex_request_token()

    assert response.status == "completed"
    assert attempts == [1, 2]
    assert seen["prior"][0] is not None and seen["prior"][1] is not None
    retry_event, retry_progress, retry_origin = seen["retry_open"]
    assert retry_event is None and retry_progress is None
    assert retry_origin is not None and retry_origin >= seen["prior"][0]

    first_event, first_progress, marker = seen["lifecycle"]
    assert first_event is not None and first_progress is None
    assert marker is None  # first parsed lifecycle event must re-arm normal event-idle
