"""Regression for NousResearch/hermes-agent#148911: Chrome MCP reports a missing DevToolsActivePort."""

import json
from types import SimpleNamespace

from tools.mcp_tool_handlers import _render_call_tool_result


def _error_from_server(message: str):
    return SimpleNamespace(
        is_error=True,
        content=[SimpleNamespace(type="text", text=message)],
    )


def test_missing_devtools_port_suggests_custom_chrome_data_directory():
    original = (
        "Could not connect to Chrome. Check chrome://inspect/#remote-debugging.\n"
        "Cause: Could not find DevToolsActivePort for chrome at "
        r"C:\Users\Test\AppData\Local\Google\Chrome\User Data\DevToolsActivePort"
    )

    payload = json.loads(_render_call_tool_result(_error_from_server(original), "chrome-devtools-win"))
    message = payload["error"]

    assert message.startswith(original)
    assert "custom user data directory" in message
    assert "chrome-devtools-mcp" in message
    assert "--userDataDir" in message


def test_other_mcp_error_is_not_reworded():
    original = "Could not list pages: permission denied"
    payload = json.loads(_render_call_tool_result(_error_from_server(original), "other-server"))
    assert payload["error"] == original
