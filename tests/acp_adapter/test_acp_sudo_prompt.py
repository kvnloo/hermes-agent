"""ACP sudo prompt: the password comes from the client's request_secret file, never a tool result."""
import pytest
import json
import os

from acp_adapter.sudo_prompt import find_secret_tool, make_sudo_callback


def test_prefers_t3_secret_tool():
    names = {"terminal", "mcp__other__request_secret", "mcp__editor_t3_code_ab12__request_secret"}
    assert find_secret_tool(names) == "mcp__editor_t3_code_ab12__request_secret"
    assert find_secret_tool({"terminal"}) is None


def test_reads_and_deletes_secret_file(tmp_path):
    secret = tmp_path / "s"
    secret.write_text("hunter2\n")
    calls = []

    def dispatch(name, args):
        calls.append((name, args))
        return json.dumps({"result": json.dumps({"status": "saved", "file": str(secret)})})

    cb = make_sudo_callback(lambda: {"mcp__editor_t3_code_x__request_secret"}, dispatch)
    assert cb() == "hunter2"
    assert not secret.exists()
    assert calls[0][1]["delivery"] == "file" and "hunter2" not in json.dumps(calls)


def test_no_tool_or_cancel_returns_empty(tmp_path):
    assert make_sudo_callback(lambda: set(), lambda *a: None)() == ""
    cb = make_sudo_callback(lambda: {"a__request_secret"}, lambda *a: {"result": '{"status":"cancelled"}'})
    assert cb() == ""


@pytest.mark.asyncio
async def test_acp_turn_routes_sudo_through_client_secret_card(tmp_path, monkeypatch):
    """Seam: an ACP turn installs a sudo callback that reads the client's request_secret file
    (base: no callback, so ACP sudo always took the headless path); the callback is gone after the turn."""
    from unittest.mock import AsyncMock, MagicMock

    import acp
    from acp.schema import TextContentBlock

    from acp_adapter.server import HermesACPAgent
    from acp_adapter.session import SessionManager
    from tools import terminal_tool
    from tools.registry import registry

    secret = tmp_path / "s"
    secret.write_text("pw\n")
    monkeypatch.setattr(registry, "dispatch", lambda name, args, **kw: json.dumps(
        {"result": json.dumps({"status": "saved", "file": str(secret)})}))
    agent = HermesACPAgent(session_manager=SessionManager(agent_factory=lambda: MagicMock(name="A")))
    resp = await agent.new_session(cwd=".")
    state = agent.session_manager.get_session(resp.session_id)
    state.agent.valid_tool_names = {"mcp__editor_t3_code_x__request_secret"}
    state.agent.model, state.agent.provider = "m", "openrouter"
    seen = {}

    def _run(**kw):
        cb = terminal_tool._get_sudo_password_callback()
        seen["pw"] = cb() if cb else None
        return {"final_response": "ok", "messages": []}

    state.agent.run_conversation = _run
    conn = MagicMock(spec=acp.Client)
    conn.session_update = AsyncMock()
    agent._conn = conn
    await agent.prompt(prompt=[TextContentBlock(type="text", text="hi")], session_id=resp.session_id)
    assert seen["pw"] == "pw" and not secret.exists()
    assert terminal_tool._get_sudo_password_callback() is None
