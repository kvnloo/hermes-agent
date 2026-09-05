"""MoA/aux chat.completions must not leak Hermes persistence fields to Groq."""

from agent.auxiliary_client import (
    _approx_prompt_tokens,
    _build_call_kwargs,
    _groq_prompt_token_ceiling,
    _trim_messages_to_token_ceiling,
)


def test_strips_timestamp_and_db_persisted():
    original = [
        {
            "role": "user",
            "content": "ping",
            "timestamp": 1781976577.0,
            "_db_persisted": True,
        }
    ]
    kwargs = _build_call_kwargs(
        provider="groq",
        model="openai/gpt-oss-20b",
        messages=original,
        base_url="https://api.groq.com/openai/v1",
    )
    sent = kwargs["messages"]
    assert sent[0]["role"] == "user"
    assert sent[0]["content"] == "ping"
    assert "timestamp" not in sent[0]
    assert "_db_persisted" not in sent[0]
    assert original[0]["timestamp"] == 1781976577.0
    assert original[0]["_db_persisted"] is True


def test_strips_compressed_summary_markers():
    original = [
        {
            "role": "user",
            "content": "[CONTEXT COMPACTION — REFERENCE ONLY] summary",
            "_compressed_summary": True,
            "_compressed_summary_has_user_turn": True,
            "_db_persisted": True,
        }
    ]
    kwargs = _build_call_kwargs(
        provider="groq",
        model="openai/gpt-oss-120b",
        messages=original,
        base_url="https://api.groq.com/openai/v1",
    )
    sent = kwargs["messages"]
    assert sent[0]["content"].startswith("[CONTEXT COMPACTION")
    assert "_compressed_summary" not in sent[0]
    assert "_compressed_summary_has_user_turn" not in sent[0]
    assert "_db_persisted" not in sent[0]
    assert original[0]["_compressed_summary"] is True


def test_groq_trim_drops_oldest_history_under_tpm_ceiling():
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "old " * 4000},
        {"role": "assistant", "content": "ack " * 4000},
        {"role": "user", "content": "newest question"},
    ]
    assert _approx_prompt_tokens(messages) > 7500
    trimmed = _trim_messages_to_token_ceiling(messages, 7500)
    assert trimmed[0]["role"] == "system"
    assert trimmed[-1]["content"] == "newest question"
    assert _approx_prompt_tokens(trimmed) <= 7500
    assert messages[1]["content"].startswith("old ")


def test_groq_strips_unsupported_reasoning_extra_body():
    kwargs = _build_call_kwargs(
        provider="groq",
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": "ping"}],
        base_url="https://api.groq.com/openai/v1",
        reasoning_config={"enabled": True, "effort": "medium"},
    )
    extra = kwargs.get("extra_body") or {}
    assert "reasoning" not in extra
    assert "reasoning" not in kwargs


def test_non_groq_provider_is_not_tpm_trimmed():
    assert _groq_prompt_token_ceiling("xai-oauth", "grok-4.6") is None
    assert (
        _groq_prompt_token_ceiling(
            "groq", "openai/gpt-oss-120b", "https://api.groq.com/openai/v1"
        )
        == 7500
    )
    assert _groq_prompt_token_ceiling("groq", "groq/compound-mini") == 65000
