"""Regression for #156020: approval for one subtask is not a goal-wide blocker."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from hermes_cli import goals


@pytest.mark.parametrize(
    "contract,subgoals",
    [
        (None, None),
        (goals.GoalContract(verification="Investigate latency", stop_when="Release requires approval"), None),
        (None, ["Investigate latency independently"]),
    ],
    ids=["plain", "contract", "subgoals"],
)
def test_judge_scopes_pending_permission_to_subtask(contract, subgoals):
    """The actual judge call must distinguish a local permission gate from global impossibility."""
    seen = {}

    def fake_call_llm(**kwargs):
        seen["system"] = kwargs["messages"][0]["content"]
        seen["user"] = kwargs["messages"][1]["content"]
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content='{"verdict":"continue","reason":"latency investigation remains authorized"}'
        ))])

    with patch("agent.auxiliary_client.call_llm", side_effect=fake_call_llm):
        verdict, _reason, parse_failed, _wait, transport_failed = goals.judge_goal(
            "A: mouse test needing approval; B: investigate latency without mouse access",
            "A needs user approval and is pending; B has not been investigated.",
            contract=contract, subgoals=subgoals,
        )

    assert (verdict, parse_failed, transport_failed) == ("continue", False, False)
    assert "latency" in seen["user"]
    assert "permission" in seen["system"].lower()
    assert "authorized, independent work" in seen["system"]
    assert "EVERY remaining" in seen["system"]
    assert "return CONTINUE" in seen["system"]
    assert "Never infer or bypass user approval" in seen["system"]


@pytest.mark.parametrize(
    "template,fields",
    [
        (goals.CONTINUATION_PROMPT_TEMPLATE, {"goal": "test A; investigate B"}),
        (goals.CONTINUATION_PROMPT_WITH_CONTRACT_TEMPLATE, {
            "goal": "test A; investigate B", "contract_block": "- Stop when blocked: release needs approval",
        }),
        (goals.CONTINUATION_PROMPT_WITH_SUBGOALS_TEMPLATE, {
            "goal": "test A; investigate B", "subgoals_block": "- 1. investigate B",
        }),
    ],
    ids=["plain", "contract", "subgoals"],
)
def test_continuation_preserves_independent_work_and_permission_gate(template, fields):
    prompt = template.format(**fields).lower()
    assert "independent" in prompt
    assert "authorized" in prompt
    assert "approval" in prompt
    assert "pending" in prompt
