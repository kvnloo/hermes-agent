"""Synthetic consumer probe for #132397's proposed startup connection handoff.

Repeated gateway discovery must retain a healthy stdio connection. An explicit
shutdown is the negative control: the same observation must then detect a new
child. This does not emulate macOS launchd or the reporter's third-party servers.
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest
import hermes_yaml as yaml


@pytest.mark.parametrize("shutdown_between", [False, True], ids=["reuse", "teardown-control"])
def test_gateway_discovery_reuses_stdio_until_explicit_teardown(tmp_path, monkeypatch, shutdown_between):
    import gateway.run as gateway_run
    from gateway.config import GatewayConfig
    from tools import mcp_tool
    from tools.mcp_tool_lifecycle import shutdown_mcp_servers
    from tools.registry import registry

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    log = tmp_path / "spawns"
    server = tmp_path / "local_server.py"
    server.write_text('''import os, sys
from mcp.server import MCPServer
with open(sys.argv[1], "a") as stream:
    stream.write(str(os.getpid()) + "\\n")
server = MCPServer("reuse")
@server.tool()
def echo(nonce: str) -> str:
    return nonce
server.run("stdio")
''')
    (home / "config.yaml").write_text(yaml.safe_dump({
        "model": {"provider": "custom", "default": "local-probe", "base_url": "http://127.0.0.1:9/v1"},
        "mcp_servers": {"reuse": {"command": sys.executable, "args": [str(server), str(log)], "connect_timeout": 15}},
    }))
    config = GatewayConfig(multiplex_profiles=False)
    try:
        asyncio.run(gateway_run._discover_gateway_mcp_tools(config))
        first = mcp_tool._servers["reuse"]
        assert json.loads(registry.dispatch("mcp__reuse__echo", {"nonce": "before"}))["result"] == "before"
        if shutdown_between:
            shutdown_mcp_servers()
        asyncio.run(gateway_run._discover_gateway_mcp_tools(config))
        second = mcp_tool._servers["reuse"]
        assert (second is first) is not shutdown_between
        assert second.session is not None and second._ever_connected
        assert json.loads(registry.dispatch("mcp__reuse__echo", {"nonce": "after"}))["result"] == "after"
        assert len(log.read_text().splitlines()) == (2 if shutdown_between else 1)
    finally:
        shutdown_mcp_servers()
