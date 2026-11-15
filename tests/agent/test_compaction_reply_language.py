"""Regression for oldhandben's Turkish /compress report (NousResearch/hermes-agent#154973).

The prompt-level contract is testable without an LLM; actual output-language
reliability after a long tool chain still requires a live model check.
"""

from types import SimpleNamespace
from unittest.mock import patch

from agent.context_compressor import ContextCompressor
from agent.system_prompt import _guidance_parts


def test_turkish_reply_language_guard_survives_compression_and_21_tool_calls():
    """The handoff and stable guidance must survive an English-heavy tool tail."""
    with patch("agent.context_compressor.get_model_context_length", return_value=8000):
        compressor = ContextCompressor(
            model="test-model",
            threshold_percent=0.75,
            protect_first_n=1,
            protect_last_n=2,
            quiet_mode=True,
        )

    messages = [{"role": "system", "content": "Stable session instructions"}]
    for i in range(6):
        messages.extend((
            {"role": "user", "content": f"Türkçe soru {i}"},
            {"role": "assistant", "content": f"Türkçe yanıt {i}"},
        ))
    messages.append({"role": "user", "content": "Sonuçları Türkçe açıklar mısın?"})

    summary = ContextCompressor._with_summary_prefix("## Özet\nKullanıcı Türkçe konuşuyor.")
    with patch.object(compressor, "_generate_summary", return_value=summary):
        request = compressor.compress(messages, current_tokens=7000)

    for i in range(21):
        call_id = f"call_{i}"
        request.extend((
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": call_id,
                    "type": "function",
                    "function": {"name": "terminal", "arguments": "{}"},
                }],
            },
            {
                "role": "tool",
                "tool_call_id": call_id,
                "content": f"English diagnostic output {i}",
            },
        ))

    contents = [str(row.get("content") or "") for row in request]
    handoff_idx = next(i for i, text in enumerate(contents) if "Kullanıcı Türkçe" in text)
    live_user_idx = max(i for i, row in enumerate(request) if row["role"] == "user")
    assert "The language of that latest user message also controls your reply" in contents[handoff_idx]
    assert handoff_idx < live_user_idx < len(request) - 42
    assert "Türkçe" in contents[live_user_idx]
    assert sum(row["role"] == "tool" for row in request[live_user_idx + 1:]) == 21

    # The reply model sees the stable tier even after the long tool chain.
    with patch("agent.system_prompt._tool_guidance_block", return_value=""):
        guidance = _guidance_parts(SimpleNamespace(valid_tool_names=[]))
    assert any("latest message the user wrote themselves" in part for part in guidance)
