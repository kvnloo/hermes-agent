"""Regression for #142288: a gateway reload must not misdescribe a past tool image.

Tool-image bytes are sent in the live turn but not retained in SQLite. The next
turn gets a text-only tool result, so that result must explain how to re-view.
"""

from agent.session_persistence import _durable_content
from hermes_state import SessionDB
from tools.vision_tools import _build_native_vision_tool_result


def test_reloaded_gateway_vision_tool_result_explains_missing_pixels(tmp_path):
    live = _build_native_vision_tool_result(
        image_url="/tmp/scoreboard.png",
        question="Read the score",
        image_data_url="data:image/png;base64,ZmFrZQ==",
        image_size_bytes=4,
    )
    assert live["_multimodal"] is True
    assert live["content"][1]["type"] == "image_url"

    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session(session_id="discord-session", source="discord")
    db.append_message("discord-session", role="user", content="Read this scoreboard", timestamp=1000.0)
    db.append_message(
        "discord-session",
        role="assistant",
        tool_calls=[{
            "id": "vision-call",
            "type": "function",
            "function": {"name": "vision_analyze", "arguments": '{"image_url":"/tmp/scoreboard.png"}'},
        }],
        timestamp=1001.0,
    )
    db.append_message(
        "discord-session",
        role="tool",
        tool_name="vision_analyze",
        tool_call_id="vision-call",
        content=_durable_content(live["content"]),
        timestamp=1002.0,
    )
    db.append_message("discord-session", role="assistant", content="The score is 42", timestamp=1003.0)
    db.append_message("discord-session", role="user", content="Did you really see it?", timestamp=1004.0)

    history = db.get_messages_as_conversation("discord-session")
    assert history[-1]["content"] == "Did you really see it?"
    saved = next(row["content"] for row in history if row["role"] == "tool")
    assert isinstance(saved, str)
    assert "[screenshot]" in saved
    assert "data:image/png;base64" not in saved
    # A text-only replay cannot claim the pixels remain attached without recovery guidance.
    assert "not attached" in saved
    assert "vision_analyze again to re-view" in saved
