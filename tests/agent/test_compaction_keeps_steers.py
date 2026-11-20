"""A mid-turn /steer is the user's own words, so compaction must keep it like any other user turn.

The steer row starts with the OUT-OF-BAND marker. The verbatim section used to drop it as scaffolding,
and the "User asked" anchor quoted the marker instead of the request.
"""
from __future__ import annotations

from agent.context_compressor import ContextCompressor, _build_verbatim_user_section
from agent.prompt_builder import steer_user_row

STEER = "dont publish that info, just keep offline for now"


def test_verbatim_section_quotes_steer_without_marker():
    out = _build_verbatim_user_section([{"role": "user", "content": "plan the release"}, steer_user_row(STEER)])
    assert f"> {STEER}" in out
    assert "OUT-OF-BAND" not in out


def test_user_asked_anchor_quotes_steer_words_not_marker():
    out = ContextCompressor._latest_user_task_snapshot([steer_user_row(STEER)])
    assert out and STEER in out
    assert "OUT-OF-BAND" not in out
