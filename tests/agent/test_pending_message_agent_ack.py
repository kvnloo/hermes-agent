"""Regression for NousResearch/hermes-agent#149942: pending Bot Mode DM hand-offs."""

import json
from types import SimpleNamespace

from agent.agent_runtime_helpers import looks_like_codex_intermediate_ack


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
