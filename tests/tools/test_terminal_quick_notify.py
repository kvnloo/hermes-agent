"""#156715: quick notified terminal commands finish in the current model turn."""
import json
from unittest.mock import patch

import pytest

from tools.process_registry import process_registry
from tools.terminal_tool import _handle_terminal


@pytest.fixture
def local_terminal(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hh"))
    config = {
        "env_type": "local", "timeout": 180, "cwd": str(tmp_path),
        "host_cwd": None, "modal_mode": "auto", "docker_image": "",
        "modal_image": "", "daytona_image": "",
    }
    with patch("tools.terminal_tool._get_env_config", return_value=config), \
         patch("tools.terminal_tool._start_cleanup_thread"), \
         patch("tools.terminal_tool._check_all_guards", return_value={"approved": True}), \
         patch("gateway.session_context.async_delivery_supported", return_value=True):
        yield


def test_quick_notified_terminal_consumes_completion_without_new_turn(local_terminal):
    # Shell builtins exit promptly; output deliberately exceeds the notification tail.
    command = "printf 'QUICK_HEAD:'; printf '%04096d' 0; printf ':QUICK_TAIL'; exit 7"
    result = json.loads(_handle_terminal(
        {"command": command, "background": True, "notify": True}, task_id="quick-notify",
    ))
    assert result["error"] is None, result
    assert result["status"] == "exited"
    assert result["exit_code"] == 7
    assert "QUICK_HEAD:" in result["output"] and ":QUICK_TAIL" in result["output"]
    assert result["notify_on_complete"] is False
    assert process_registry.is_completion_consumed(result["session_id"])
    assert not [
        event for event, _ in process_registry.drain_notifications()
        if event.get("session_id") == result["session_id"]
    ]


def test_long_notified_terminal_still_returns_background_receipt(local_terminal):
    result = json.loads(_handle_terminal(
        {"command": "sleep 30", "background": True, "notify": True}, task_id="slow-notify",
    ))
    try:
        assert result["error"] is None, result
        assert result["output"] == "Background process started"
        assert result["notify_on_complete"] is True
        assert not process_registry.is_completion_consumed(result["session_id"])
    finally:
        process_registry.kill_process(result["session_id"])
