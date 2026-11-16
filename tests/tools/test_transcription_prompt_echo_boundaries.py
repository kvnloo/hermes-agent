"""Prompt echo retries must require a prompt-aware hosted Whisper backend.

The routing seam is real; only provider network handlers are replaced.
"""
from unittest.mock import patch

import pytest

from tools import transcription_tools


PROMPT = "Hermes, Teknium, Nous Research, kanban, Ollama"
LONG_PROMPT = ", ".join([PROMPT] * 6)  # Longer than SequenceMatcher's autojunk threshold.


@pytest.mark.parametrize(("provider", "hint", "heard", "retry"), [
    pytest.param("groq", LONG_PROMPT, "Q" + LONG_PROMPT, True, id="long-whisper-echo"),
    pytest.param("xai", PROMPT, PROMPT, False, id="xai-ignores-hints"),
    pytest.param("elevenlabs", PROMPT, PROMPT, False, id="elevenlabs-ignores-hints"),
])
def test_prompt_echo_retry_requires_a_hosted_prompt_aware_backend(provider, hint, heard, retry):
    calls = []

    def fake_handler(file_path, model_name, *, language=None, prompt=None):
        calls.append(prompt)
        return {
            "success": True,
            "transcript": heard if len(calls) == 1 else "Actual speech, not the hint",
            "provider": provider,
        }

    with patch.object(transcription_tools, f"_transcribe_{provider}", side_effect=fake_handler):
        result = transcription_tools._route_stt_provider(
            "recording.wav", provider, {"provider": provider}, None, None, hint
        )

    assert calls == ([hint, None] if retry else [hint])
    assert result["transcript"] == ("Actual speech, not the hint" if retry else heard)
