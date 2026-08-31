from types import SimpleNamespace
from unittest.mock import MagicMock

from agent.conversation_loop import telegram_attention_guard_result


def _agent(platform: str, budget: int = 1000):
    return SimpleNamespace(
        platform=platform,
        telegram_tool_result_budget_chars=budget,
        _persist_session=MagicMock(),
    )


def test_mid_turn_telegram_tool_growth_fails_closed_and_persists_every_row():
    agent = _agent("telegram")
    messages = [
        {"role": "user", "content": "latest intent"},
        *[
            {"role": "tool", "tool_call_id": f"call-{i}", "content": "x" * 2}
            for i in range(1000)
        ],
    ]
    history = [{"role": "user", "content": "prior intent"}]

    result = telegram_attention_guard_result(agent, messages, history, api_calls=7)

    assert result is not None
    assert result["failed"] is True
    assert result["api_calls"] == 7
    assert "2,000 > 1,000" in result["error"]
    agent._persist_session.assert_called_once_with(messages, history)


def test_cli_is_not_subject_to_telegram_attention_guard():
    agent = _agent("cli", budget=1)
    messages = [{"role": "tool", "content": "large"}]

    assert telegram_attention_guard_result(agent, messages, [], api_calls=1) is None
    agent._persist_session.assert_not_called()


def test_exact_budget_is_allowed():
    agent = _agent("telegram", budget=5)
    messages = [{"role": "tool", "content": "12345"}]

    assert telegram_attention_guard_result(agent, messages, [], api_calls=1) is None
    agent._persist_session.assert_not_called()
