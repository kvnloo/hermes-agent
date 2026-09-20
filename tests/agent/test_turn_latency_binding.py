"""Integration coverage for turn-level critical-path trace binding."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.agent.test_run_agent import _make_tool_defs, _mock_response


def _agent():
    from run_agent import AIAgent

    with (
        patch("model_tools.get_tool_definitions", return_value=_make_tool_defs("web_search")),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
    agent.client = MagicMock()
    agent.client.chat.completions.create.return_value = _mock_response(
        content="Done", finish_reason="stop"
    )
    agent._cached_system_prompt = "You are helpful."
    agent._use_prompt_caching = False
    agent.compression_enabled = False
    agent.save_trajectories = False
    return agent


def test_real_turn_keeps_content_free_latency_receipt():
    agent = _agent()
    with (
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation("secret user content must not enter timing")

    assert result["final_response"] == "Done"
    receipt = agent._last_turn_latency_receipt
    assert receipt["turn_id"] == agent._current_turn_id
    assert isinstance(receipt["spans"], list)
    rendered = repr(receipt)
    assert "secret user content" not in rendered
    assert "Done" not in rendered


def test_new_turn_clears_stale_receipt_before_admission():
    agent = _agent()
    agent._last_turn_latency_receipt = {"turn_id": "stale"}

    # An admission denial/early result is enough to prove the clear happens
    # before the inner agent loop. Keep this test at the facade seam.
    from types import SimpleNamespace

    early = {"final_response": "", "failed": True}
    with (
        patch(
            "agent.turn_facade_lease.admit_durable_turn_lease",
            return_value=SimpleNamespace(
                early_result=early, lease=None, conversation_history=[]
            ),
        ),
        patch("agent.turn_facade_lease.carry_unadmitted_user_message"),
    ):
        result = agent.run_conversation("blocked")

    assert result is early
    assert agent._last_turn_latency_receipt is None


def test_failed_agent_loop_still_leaves_latency_receipt():
    agent = _agent()

    with patch(
        "agent.conversation_loop.run_conversation",
        side_effect=RuntimeError("provider exploded"),
    ), pytest.raises(RuntimeError, match="provider exploded"):
        agent.run_conversation("do not copy this into timing")

    receipt = agent._last_turn_latency_receipt
    assert receipt["turn_id"] == agent._current_turn_id
    assert "do not copy this" not in repr(receipt)
