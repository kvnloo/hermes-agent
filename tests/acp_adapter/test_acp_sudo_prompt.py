"""ACP sudo prompt: the password comes from the client's request_secret file, never a tool result."""
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
