"""Display-only session payload regression for NousResearch/hermes-agent#153276."""

import json

from hermes_cli.web_routers.sessions import _project_for_display


def test_display_page_omits_shadowed_native_reasoning_replay(tmp_path):
    native_replay = json.dumps([{
        "type": "claude-subscription-directsdk-experimental.native_assistant",
        "messages": [{"content": [
            {"type": "thinking", "thinking": "", "signature": "opaque-signed-data"},
            {"type": "text", "text": "answer"},
        ]}],
        "projection": {"content": "answer", "tool_calls": []},
    }])
    with_reasoning = {
        "id": 1, "role": "assistant", "content": "answer",
        "reasoning": "readable thought", "reasoning_content": "readable thought",
        "reasoning_details": native_replay,
    }
    details_only = {
        "id": 2, "role": "assistant", "content": "fallback answer",
        "reasoning": None, "reasoning_content": None,
        "reasoning_details": native_replay,
    }

    display = {row["id"]: row for row in _project_for_display(
        [with_reasoning, details_only], home=tmp_path
    )}

    assert display[1]["reasoning"] == "readable thought"
    assert display[1]["content"] == "answer"
    assert "reasoning_details" not in display[1]
    assert display[2]["reasoning_details"] == native_replay
    assert with_reasoning["reasoning_details"] == native_replay
