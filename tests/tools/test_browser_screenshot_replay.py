"""Regression for #142288: browser screenshots replay from a persisted tool row.

The native browser result embeds pixels like vision_analyze; a gateway turn rebuilt
from SessionDB must send the same tool image, not a [screenshot] placeholder.
"""

from agent.session_persistence import _durable_content
from agent.turn_context import build_api_messages
from hermes_state import SessionDB
from tests.agent.test_image_replay import _Agent, _config
from tests.tools.test_vision_native_fast_path import _TINY_PNG
from tools.browser_use_cli import _native_screenshot_result


def test_browser_screenshot_resends_identical_tool_image_after_db_reload(tmp_path, monkeypatch):
    _config()
    # The browser tool runs this path only after the main-model native-vision gate.
    monkeypatch.setattr("tools.vision_tools._should_use_native_vision_fast_path", lambda: True)
    screenshot = tmp_path / "browser.png"
    screenshot.write_bytes(_TINY_PNG)
    envelope = _native_screenshot_result({"success": True, "output": "captured"}, str(screenshot))
    assert envelope is not None
    live = envelope["content"]
    assert [part["type"] for part in live] == ["text", "image_url"]

    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session(session_id="s", source="telegram")
    call = {
        "id": "browser_call", "type": "function",
        "function": {"name": "browser_exec", "arguments": '{"code": "capture_screenshot()"}'},
    }
    db.append_message("s", role="user", content="What is on this page?", timestamp=1000.0)
    db.append_message("s", role="assistant", content="", tool_calls=[call], timestamp=1001.0)
    db.append_message("s", role="tool", content=_durable_content(live),
                      tool_call_id="browser_call", tool_name="browser_exec", timestamp=1002.0)
    db.append_message("s", role="assistant", content="I can see the page.", timestamp=1003.0)
    history = db.get_messages_as_conversation("s") + [{"role": "user", "content": "And the footer?"}]

    request, _ = build_api_messages(
        _Agent(), history, current_turn_user_idx=len(history) - 1,
        ext_prefetch_cache="", plugin_user_context="", moa_config=None, active_system_prompt="",
    )
    # The provider's prompt-cache prefix must survive the database round-trip.
    assert next(row for row in request if row["role"] == "tool")["content"] == live
