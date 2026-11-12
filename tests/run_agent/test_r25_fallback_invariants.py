"""R25: persistent auth fails closed; pinned fallbacks remain visible each turn."""

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent.agent_runtime_helpers import restore_primary_runtime
from run_agent import AIAgent


@pytest.mark.parametrize("status", [401, 403])
def test_persistent_auth_never_attempts_another_model(status):
    with (
        patch("run_agent.get_tool_definitions", return_value=[]),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key", provider="custom", model="primary-model",
            base_url="https://primary.example/v1", quiet_mode=True,
            skip_context_files=True, skip_memory=True,
            fallback_model=[{"provider": "custom", "model": "other-model"}],
        )
    agent._cached_system_prompt = "You are helpful."
    agent._use_prompt_caching = False
    agent.compression_enabled = False
    agent.save_trajectories = False
    agent._credential_pool = None
    agent.client = MagicMock()
    error = Exception(f"Error code: {status} - Invalid API key")
    error.status_code = status
    agent.client.chat.completions.create.side_effect = error
    with (
        patch.object(agent, "_try_activate_fallback", return_value=False) as fallback,
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
        patch("agent.conversation_loop.time.sleep"),
    ):
        result = agent.run_conversation("hello")
    assert result["failed"] is True
    assert result["completed"] is False
    assert str(status) in result["error"]
    fallback.assert_not_called()
    assert agent.model == "primary-model"


def _pinned_agent():
    return SimpleNamespace(
        _fallback_activated=True,
        _primary_runtime={"provider": "custom", "model": "primary-model", "base_url": ""},
        _rate_limited_until=time.monotonic() + 3600,
        model="actual-model", provider="custom", _pending_fallback_notice=None,
        _buffer_status=MagicMock(),
    )


def test_cooldown_repeats_actual_model_notice_each_turn(monkeypatch):
    monkeypatch.setattr(time, "monotonic", lambda: 100)
    monkeypatch.setattr(time, "time", lambda: 100000)
    agent = _pinned_agent()
    for _ in range(2):
        agent._pending_fallback_notice = None
        assert restore_primary_runtime(agent) is False
        notice = agent._pending_fallback_notice
        assert notice is not None
        assert "actual-model" in notice and "custom" in notice
        assert "primary-model" in notice
        assert time.strftime("%H:%M", time.localtime(103600)) in notice


def test_pool_reset_repeats_actual_model_notice_each_turn(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 100000)
    agent = _pinned_agent()
    agent._rate_limited_until = 0
    agent._credential_pool = SimpleNamespace(
        provider="custom", next_available_at=lambda: 103600,
    )
    agent._restore_wait_logged = False
    with patch("agent.agent_runtime_helpers.credential_pool_matches_provider", return_value=True):
        for _ in range(2):
            agent._pending_fallback_notice = None
            assert restore_primary_runtime(agent) is False
            notice = agent._pending_fallback_notice
            assert notice is not None
            assert "actual-model" in notice and "primary-model" in notice
            assert time.strftime("%H:%M", time.localtime(103600)) in notice


def test_cached_conversation_emits_actual_fallback_on_every_successful_turn():
    notices = []
    with (
        patch("run_agent.get_tool_definitions", return_value=[]),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
        patch("agent.model_metadata.get_model_context_length", return_value=200000),
    ):
        agent = AIAgent(
            api_key="test-key", provider="custom", model="primary-model",
            base_url="https://primary.example/v1", quiet_mode=True,
            skip_context_files=True, skip_memory=True,
            status_callback=lambda kind, message: notices.append((kind, message)),
        )
    agent._cached_system_prompt = "You are helpful."
    agent._use_prompt_caching = False
    agent.compression_enabled = False
    agent.save_trajectories = False
    agent._credential_pool = None
    agent._fallback_activated = True
    agent._rate_limited_until = time.monotonic() + 3600
    agent.model = "actual-model"
    agent.client = MagicMock()
    agent.client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(content="Answer.", tool_calls=None),
            finish_reason="stop",
        )],
        model="actual-model", usage=None,
    )
    with (
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        for turn in ("hello", "hello again"):
            notices.clear()
            result = agent.run_conversation(turn)
            assert result["completed"] is True
            assert result["final_response"] == "Answer."
            fallback_notices = [message for kind, message in notices if "On fallback" in message]
            assert len(fallback_notices) == 1
            assert "actual-model via custom" in fallback_notices[0]
            assert "primary-model" in fallback_notices[0]
