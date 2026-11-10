"""Replayed encrypted reasoning is priced at the provider-reported count (#125920).

The reporter's shape: an xAI/Codex session compacted once, then one long tool-calling turn whose
visible text is tiny while every tool round replays thousands of tokens of encrypted reasoning.
Priced at 0, that whole turn fit inside the protected tail, so the planned summary window held only
the earlier handoff row: compression found nothing to cut (and armed the structural backoff) while
the real bill sat over the window. Priced at the stamped count, the cut lands inside the active turn
and its older tool rounds (with their reasoning) are summarized.
"""
from unittest.mock import patch

from agent.context_compressor import ContextCompressor
from agent.message_metadata import stamp_reasoning_tokens


def _compacted_then_long_tool_turn(rounds: int = 12, reasoning_tokens: int = 8_000) -> list[dict]:
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "[CONTEXT COMPACTION] earlier work summarized."},
        {"role": "assistant", "content": "ok, continuing."},
        {"role": "user", "content": "Audit every file in the repo and report the totals."},
    ]
    for i in range(rounds):
        assistant = {
            "role": "assistant", "content": "",
            "tool_calls": [{"id": f"c{i}", "type": "function",
                            "function": {"name": "read_file", "arguments": f'{{"path": "f{i}"}}'}}],
            "codex_reasoning_items": [{"type": "reasoning", "encrypted_content": "x" * 400}],
        }
        stamp_reasoning_tokens(assistant, reasoning_tokens)
        messages += [assistant, {"role": "tool", "tool_call_id": f"c{i}", "content": f"value={i}"}]
    return messages


def test_window_reaches_into_a_reasoning_heavy_active_turn():
    with patch("agent.context_compressor.get_model_context_length", return_value=200_000):
        c = ContextCompressor(model="grok-4.7", threshold_percent=0.5, protect_first_n=1,
                              protect_last_n=2, quiet_mode=True)
        _ = c.context_length
    messages = _compacted_then_long_tool_turn()
    start, end = c._compress_window(messages)
    # ~96k of replayed reasoning against a 10k tail budget: most tool rounds must be summarizable.
    summarizable_rounds = sum(1 for m in messages[start:end] if m.get("codex_reasoning_items"))
    assert summarizable_rounds >= 8, f"window {start}-{end}: only {summarizable_rounds} rounds summarizable"


def test_incomplete_codex_refresh_without_usage_drops_stale_reasoning_price():
    """An incomplete continuation replaces the ciphertext; old provider usage must not price new bytes."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from agent.message_metadata import stamped_reasoning_tokens
    from agent.replayed_reasoning import codex_reasoning_replay_tokens
    from agent.turn_truncation import continue_codex_incomplete

    agent = MagicMock()
    agent.max_tokens = 2_048
    agent.quiet_mode = True
    agent.log_prefix = ""
    agent._codex_incomplete_retries = 0
    agent._codex_reasoning_only_streak = 0
    agent._interim_assistant_visible_text.return_value = ""

    def build(message, finish_reason):
        row = {
            "role": "assistant", "content": message.content, "finish_reason": finish_reason,
            "codex_reasoning_items": message.codex_reasoning_items,
        }
        stamp_reasoning_tokens(row, message.reasoning_tokens)
        return row

    agent._build_assistant_message.side_effect = build
    prior = {
        "role": "assistant", "content": "", "finish_reason": "incomplete",
        "codex_reasoning_items": [{"type": "reasoning", "encrypted_content": "x" * 13_500}],
        "display_metadata": {"display_kind": "progress"},
    }
    stamp_reasoning_tokens(prior, 8_000)
    current = SimpleNamespace(
        content="", tool_calls=None, reasoning=None, reasoning_tokens=0,
        codex_reasoning_items=[{"type": "reasoning", "encrypted_content": "y" * 1_350}],
    )
    messages = [{"role": "user", "content": "continue"}, prior]

    outcome = continue_codex_incomplete(
        agent, current, "incomplete", messages=messages, conversation_history=None,
        api_call_count=1, response=SimpleNamespace(status="incomplete", usage=None),
    )

    assert outcome is None
    assert messages[1] is prior
    assert prior["codex_reasoning_items"] == current.codex_reasoning_items
    assert prior["display_metadata"]["display_kind"] == "progress"
    assert stamped_reasoning_tokens(prior) == 0
    assert codex_reasoning_replay_tokens(prior) == 100
