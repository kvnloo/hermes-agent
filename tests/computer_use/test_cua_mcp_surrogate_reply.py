"""A computer-use-only MCP session must not drop replies with half an emoji.

Regression for NousResearch/hermes-agent#154821: the cua-driver client opens its
own stdio SDK session, without running the configured MCP server SDK loader.
"""

import os
import sys
import textwrap

import pytest

pytest.importorskip("mcp")

_SERVER = textwrap.dedent(r'''
    import json
    import sys

    for line in sys.stdin:
        message = json.loads(line)
        request_id, method = message.get("id"), message.get("method")
        if request_id is None:
            continue
        if method == "initialize":
            reply = json.dumps({"jsonrpc": "2.0", "id": request_id, "result": {
                "protocolVersion": message["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "surrogate-cua", "version": "1"}}})
        elif method == "tools/list":
            reply = '{"jsonrpc":"2.0","id":%s,"result":{"tools":[{"name":"t","description":"cut \\ud83d","inputSchema":{"type":"object"}}]}}' % json.dumps(request_id)
        elif method == "tools/call":
            reply = '{"jsonrpc":"2.0","id":%s,"result":{"content":[{"type":"text","text":"hi \\ud83d"}]}}' % json.dumps(request_id)
        else:
            reply = json.dumps({"jsonrpc": "2.0", "id": request_id, "result": {}})
        sys.stdout.write(reply + "\n")
        sys.stdout.flush()
''')


def test_direct_cua_stdio_session_repairs_surrogates_in_discovery_and_result(tmp_path, monkeypatch):
    from tools.computer_use import cua_backend
    from tools.computer_use.cua_backend_session import _AsyncBridge, _CuaDriverSession

    server = tmp_path / "server.py"
    server.write_text(_SERVER, encoding="utf-8")
    monkeypatch.setattr(
        cua_backend, "sandbox_mcp_invocation",
        lambda: ((sys.executable, [str(server)]), dict(os.environ)),
    )

    bridge = _AsyncBridge()
    session = _CuaDriverSession(bridge)
    try:
        session.start()
        assert session.capabilities_discovered
        assert session._tool_schemas["t"] == {"type": "object"}
        listed = bridge.run(session._session.list_tools())
        assert listed.tools[0].description == "cut \ufffd"
        assert session.call_tool("t", {})["data"] == "hi \ufffd"
    finally:
        session.stop()
        bridge.stop()
