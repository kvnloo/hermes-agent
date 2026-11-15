"""Regression for NousResearch/hermes-agent#149942: pending Bot Mode DM hand-offs."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent.agent_runtime_helpers import looks_like_codex_intermediate_ack
from run_agent import AIAgent


PREFERENCE = "Keep coordinating the project and let the specialist finish."
PENDING_ACK = (
    "Understood. I'll report back when the already queued project review completes."
)


def _agent():
    return SimpleNamespace(_strip_think_blocks=lambda text: text)


def _history(status="queued"):
    return [
        {"role": "user", "content": "Ask the specialist to review the project."},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "dm-1",
                    "type": "function",
                    "function": {
                        "name": "message_agent",
                        "arguments": '{"target":"specialist","message":"Review the project."}',
                    },
                },
            ],
        },
        {
            "role": "tool",
            "name": "message_agent",
            "tool_call_id": "dm-1",
            "content": json.dumps(
                {"status": status, "detail": "Do NOT wait or resend; finish your turn."}
            ),
        },
        {"role": "assistant", "content": "The specialist is working."},
        {"role": "user", "content": PREFERENCE},
    ]


def test_prior_queued_delivery_ack_does_not_reprompt():
    """A later preference turn must not duplicate an admitted async dispatch."""
    assert not looks_like_codex_intermediate_ack(
        _agent(), PREFERENCE, PENDING_ACK, _history(), require_workspace=True
    )


def test_unrelated_new_request_still_requires_dispatch():
    """An old queued DM must not disable continuation for genuinely new work."""
    user = "Please inspect the new repository now."
    history = _history()
    history[-1] = {"role": "user", "content": user}
    assert looks_like_codex_intermediate_ack(
        _agent(),
        user,
        "I'll inspect the new repository now.",
        history,
        require_workspace=True,
    )


def test_unconfirmed_dispatch_does_not_exempt_ack():
    """A failed/non-queued result is not proof of pending delegated work."""
    assert looks_like_codex_intermediate_ack(
        _agent(), PREFERENCE, PENDING_ACK, _history(status="failed"), require_workspace=True
    )


def test_current_turn_tool_result_already_prevents_reprompt():
    """Keep the existing current-turn tool-result exclusion."""
    history = _history()
    current = [
        {"role": "user", "content": PREFERENCE},
        history[1],
        history[2],
    ]
    assert not looks_like_codex_intermediate_ack(
        _agent(), PREFERENCE, PENDING_ACK, current, require_workspace=True
    )


@pytest.mark.parametrize("status", ["queued", "failed"])
def test_pending_ack_conversation_finishes_only_for_confirmed_dispatch(
    status, tmp_path, monkeypatch
):
    """Exercise the real conversation loop with a deterministic model response."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HERMES_VERIFY_ON_STOP", "0")
    with (
        patch("model_tools.get_tool_definitions", return_value=[]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        agent = AIAgent(
            session_id="pending-dm-ack-test",
            api_key="test-key",
            base_url="https://example.invalid/v1",
            provider="openai-compat",
            model="test/model",
            max_iterations=1,
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
    agent._cached_system_prompt = "stable test prompt"
    agent._session_db = None
    agent.save_trajectories = False
    agent.compression_enabled = False
    agent._cleanup_task_resources = lambda *_a, **_kw: None
    agent._save_trajectory = lambda *_a, **_kw: None
    agent.valid_tool_names = ["message_agent"]
    agent._intent_ack_continuation = True
    agent._interruptible_api_call = MagicMock(return_value=SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(content=PENDING_ACK, tool_calls=None),
            finish_reason="stop",
        )],
        model="test/model",
        usage=None,
    ))
    agent._handle_max_iterations = MagicMock(return_value="continuation required")
    with (
        patch("hermes_cli.plugins.has_hook", return_value=False),
        patch("hermes_cli.plugins.invoke_hook", return_value=[]),
    ):
        result = agent.run_conversation(
            PREFERENCE, conversation_history=_history(status=status)[:-1]
        )
    agent._interruptible_api_call.assert_called_once()
    if status == "queued":
        assert result["final_response"] == PENDING_ACK
        assert result["completed"] is True
        assert result["turn_exit_reason"] == "text_response(finish_reason=stop)"
        agent._handle_max_iterations.assert_not_called()
    else:
        assert result["final_response"].startswith("continuation required")
        assert result["completed"] is False
        assert result["turn_exit_reason"] == "max_iterations_reached(1/1)"
        agent._handle_max_iterations.assert_called_once()
