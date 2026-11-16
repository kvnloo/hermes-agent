"""A /goal continuation prompt is runtime scaffolding, not the user's words.

The goal loop re-sends the standing goal as a ``role=user`` row after every turn. Compaction
treated those rows as real user messages, so in a goal-armed session the capsule's
"User asked" snapshot and "User Messages (verbatim)" section quoted the old goal (labelled as
overriding everything else), and the protected tail kept the newest goal row instead of the
person's newest message.
"""
import pytest

from agent.context_compressor import ContextCompressor, _build_verbatim_user_section
from hermes_cli.goals import (
    CONTINUATION_PROMPT_GATE_FAILED_TEMPLATE,
    CONTINUATION_PROMPT_TEMPLATE,
    CONTINUATION_PROMPT_WITH_CONTRACT_TEMPLATE,
    CONTINUATION_PROMPT_WITH_SUBGOALS_TEMPLATE,
)

GOAL = "keep running the hill climb"
REAL = "others online get good results with optmem. why did our attempts fail?"


def _goal_rows() -> list[str]:
    fields = {"goal": GOAL, "contract_block": "- done: x", "subgoals_block": "- y",
              "attempt": 1, "max_retries": 3, "command": "pytest", "exit_code": 1, "output": "FAILED"}
    rows = []
    for template in (CONTINUATION_PROMPT_TEMPLATE, CONTINUATION_PROMPT_WITH_CONTRACT_TEMPLATE,
                     CONTINUATION_PROMPT_WITH_SUBGOALS_TEMPLATE, CONTINUATION_PROMPT_GATE_FAILED_TEMPLATE):
        try:
            rows.append(template.format(**fields))
        except KeyError as missing:  # a template grew a field this test does not know yet
            pytest.fail(f"goal template needs field {missing}")
    return rows


@pytest.mark.parametrize("text", _goal_rows())
def test_goal_continuation_is_synthetic(text):
    assert ContextCompressor._is_synthetic_compression_user_turn({"role": "user", "content": text})


def test_real_user_message_is_not_synthetic():
    assert not ContextCompressor._is_synthetic_compression_user_turn({"role": "user", "content": REAL})


def test_verbatim_section_quotes_the_person_not_the_goal_loop():
    turns = [{"role": "user", "content": REAL}, {"role": "assistant", "content": "on it"}]
    for row in _goal_rows():
        turns += [{"role": "user", "content": row}, {"role": "assistant", "content": "step"}]
    section = _build_verbatim_user_section(turns)
    assert REAL in section
    assert "standing goal" not in section


def test_tail_anchor_keeps_the_persons_newest_message():
    compressor = ContextCompressor.__new__(ContextCompressor)
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": REAL},
        {"role": "assistant", "content": "answer"},
        {"role": "user", "content": _goal_rows()[0]},
        {"role": "assistant", "content": "step"},
    ]
    assert compressor._find_last_user_message_idx(messages, 1) == 1
