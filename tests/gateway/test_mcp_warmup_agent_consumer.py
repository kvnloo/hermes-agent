"""Offline gateway warmup-to-agent consumer for the lifecycle hypothesis in #132397."""

import asyncio
import json
import socket
import sys
from pathlib import Path

import pytest
import hermes_yaml as yaml


@pytest.mark.parametrize("teardown", [False, True], ids=["healthy", "teardown-control"])
def test_stdio_connection_survives_real_warmup_and_agent_snapshot(tmp_path, monkeypatch, teardown):
    attempted_network = []

    def deny_network(original):
        def guarded(sock, address):
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                attempted_network.append(str(address))
                raise OSError("offline MCP consumer fixture forbids network connections")
            return original(sock, address)
        return guarded

    monkeypatch.setattr(socket.socket, "connect", deny_network(socket.socket.connect))
    monkeypatch.setattr(socket.socket, "connect_ex", deny_network(socket.socket.connect_ex))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    pid_log = tmp_path / "pids"
    fixture = Path(__file__).parents[1] / "e2e/core/parity/fixture_mcp_server.py"
    (home / "config.yaml").write_text(yaml.safe_dump({
        "model": {"provider": "custom", "default": "offline-probe", "base_url": "http://127.0.0.1:9/v1", "context_length": 128000},
        "agent": {"environment_probe": False},
        "local_runtime": {"enabled": False},
        "tools": {"tool_search": {"enabled": False}},
        "mcp_servers": {"warmup": {
            "command": sys.executable, "args": [str(fixture)], "connect_timeout": 15,
            "env": {"PARITY_MCP_PID_LOG": str(pid_log), "PARITY_MCP_CANARY": "warmup-consumer",
                    "PARITY_MCP_SPAWN_GRANDCHILD": "0", "PARITY_MCP_DEATH_TOOL": "0"},
        }},
    }))

    import gateway.run as gateway_run
    from gateway.config import GatewayConfig
    from tools import mcp_tool
    from tools.mcp_tool_lifecycle import shutdown_mcp_servers
    from tools.registry import registry

    # The warmup's model catalog is unrelated to MCP ownership; keep its metadata local.
    monkeypatch.setattr(gateway_run, "_resolve_gateway_model_context", lambda: gateway_run._GatewayModelContext(
        model="offline-probe", provider="custom", base_url="http://127.0.0.1:9/v1",
        context_length=128000, context_source="fixture"))
    monkeypatch.setattr("agent.model_metadata.fetch_model_metadata", lambda *a, **kw: {})
    monkeypatch.setattr("agent.model_metadata.detect_local_server_type", lambda *a, **kw: None)
    agent = None
    tool = "mcp__warmup__parity_canary"
    try:
        asyncio.run(gateway_run._discover_gateway_mcp_tools(GatewayConfig(multiplex_profiles=False)))
        initial = mcp_tool._servers["warmup"]
        assert initial.session is not None
        assert json.loads(registry.dispatch(tool, {"nonce": "before"}))["result"] == "warmup-consumer:before"
        if teardown:
            shutdown_mcp_servers()

        # Unlike repeat discovery, this executes actual boot imports and schema materialization.
        assert gateway_run._warm_turn_machinery_sync() > 0
        from run_agent import AIAgent
        agent = AIAgent(
            model="offline-probe", provider="custom", api_key="fixture-not-a-secret",
            base_url="http://127.0.0.1:9/v1", enabled_toolsets=["mcp-warmup"],
            quiet_mode=True, skip_context_files=True, skip_memory=True, skip_background_review=True,
        )
        assert (tool in agent.valid_tool_names) is not teardown
        assert len(pid_log.read_text().splitlines()) == 1
        if teardown:
            assert "warmup" not in mcp_tool._servers
        else:
            assert mcp_tool._servers["warmup"] is initial
            assert initial.session is not None and initial._ever_connected
            assert json.loads(registry.dispatch(tool, {"nonce": "after"}))["result"] == "warmup-consumer:after"
        assert not attempted_network, attempted_network
    finally:
        if agent is not None:
            agent.close()
        shutdown_mcp_servers()
