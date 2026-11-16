"""Regression for NousResearch/hermes-agent#148911: Chrome MCP reports a missing DevToolsActivePort."""

import json
import sys
import textwrap
from types import SimpleNamespace

import pytest

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


@pytest.mark.parametrize("is_error,message", [
    (True, "Could not find DevToolsActivePort. Configure --userDataDir first."),
    (False, "Could not find DevToolsActivePort"),
    (True, "Could not connect to Chrome: permission denied"),
])
def test_existing_guidance_success_and_other_chrome_errors_are_unchanged(is_error, message):
    result = _error_from_server(message)
    result.is_error = is_error
    payload = json.loads(_render_call_tool_result(result, "chrome-devtools-win"))
    assert payload == {"error" if is_error else "result": message}


@pytest.mark.no_isolate
@pytest.mark.platforms("posix")
def test_missing_devtools_hint_reaches_registry_from_real_stdio_server(monkeypatch, tmp_path):
    pytest.importorskip("mcp.server.mcpserver")
    home = tmp_path / "home"
    home.mkdir()
    server_path = home / "server.py"
    server_path.write_text(textwrap.dedent('''\
        from mcp.server.mcpserver import MCPServer
        app = MCPServer("chrome-devtools")

        @app.tool()
        def inspect_pages() -> str:
            raise RuntimeError("Could not find DevToolsActivePort for chrome")

        app.run()
    '''), encoding="utf-8")
    (home / "config.yaml").write_text(
        "mcp_servers:\n  chrome-devtools:\n"
        f"    command: {json.dumps(sys.executable)}\n"
        f"    args: [{json.dumps(str(server_path))}]\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))

    from tools import mcp_tool_discovery as discovery
    from tools import mcp_tool_loop
    from tools.mcp_tool_lifecycle import shutdown_mcp_servers
    from tools.registry import registry

    try:
        name = "mcp__chrome_devtools__inspect_pages"
        assert name in discovery.discover_mcp_tools()
        payload = json.loads(registry.dispatch(name, {}))
        assert "Could not find DevToolsActivePort" in payload["error"]
        assert "custom user data directory" in payload["error"]
        assert "--userDataDir" in payload["error"]
        assert "parent of profiles like Default" in payload["error"]
    finally:
        shutdown_mcp_servers()
        mcp_tool_loop._stop_mcp_loop()
