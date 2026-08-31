from gateway.context_budget import (
    DEFAULT_TELEGRAM_TOOL_RESULT_BUDGET_CHARS,
    retained_tool_result_chars,
    telegram_history_exceeds_attention_budget,
)


def _tool_result(size: int) -> dict:
    return {"role": "tool", "tool_call_id": "call", "content": "x" * size}


def test_tool_result_budget_reproduces_poisoned_telegram_transcript():
    history = [_tool_result(5_543) for _ in range(299)]

    assert retained_tool_result_chars(history) == 1_657_357
    assert telegram_history_exceeds_attention_budget(history)


def test_one_thousand_inline_results_cannot_remain_below_declared_budget():
    history = [_tool_result(1_000) for _ in range(1_000)]

    assert retained_tool_result_chars(history) == 1_000_000
    assert DEFAULT_TELEGRAM_TOOL_RESULT_BUDGET_CHARS < 1_000_000
    assert telegram_history_exceeds_attention_budget(history)


def test_non_tool_conversation_content_does_not_spend_tool_result_budget():
    history = [
        {"role": "user", "content": "latest intent"},
        {"role": "assistant", "content": "x" * 1_000_000},
        {"role": "user", "content": "approval granted"},
    ]

    assert retained_tool_result_chars(history) == 0
    assert not telegram_history_exceeds_attention_budget(history)


def test_budget_boundary_is_inclusive():
    history = [_tool_result(DEFAULT_TELEGRAM_TOOL_RESULT_BUDGET_CHARS)]

    assert not telegram_history_exceeds_attention_budget(history)
    history.append(_tool_result(1))
    assert telegram_history_exceeds_attention_budget(history)
