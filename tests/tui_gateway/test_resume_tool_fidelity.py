"""Regression for #521: stored tool results survive the real resume RPC in a temp home."""

import copy
import json

import pytest

from hermes_state import SessionDB
from tui_gateway import server
from tui_gateway.tool_result_display import TOOL_RESULT_TEXT_BUDGET, bounded_tool_result


def invocation(name="terminal", call_id="call", args=None):
    return {"id": call_id, "type": "function", "function": {
        "name": name, "arguments": json.dumps(args or {"command": "npm test"}),
    }}


@pytest.mark.parametrize("lazy", [False, True])
def test_resume_preserves_stored_tool_result(tmp_path, monkeypatch, lazy):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(server, "_schedule_agent_build", lambda *a, **kw: None)
    monkeypatch.setattr(server, "_schedule_session_cap_enforcement", lambda *a, **kw: None)
    monkeypatch.setattr(server, "_enable_gateway_prompts", lambda: None)
    content = json.dumps({"output": "test failed", "exit_code": 2, "duration_s": 1.25})
    with SessionDB(db_path=home / "state.db") as db:
        db.create_session("resume-tools", "cli")
        db.append_message("resume-tools", "user", "Run the tests")
        db.append_message("resume-tools", "assistant", "", tool_calls=[invocation()])
        db.append_message("resume-tools", "tool", content, tool_call_id="call", tool_name="terminal")
    known = set(server._sessions)
    try:
        response = server._methods["session.resume"](1, {"session_id": "resume-tools", "lazy": lazy})
        assert "error" not in response, response
        tool = next(m for m in response["result"]["messages"] if m["role"] == "tool")
        assert tool["content"] == content
        assert tool["args"] == {"command": "npm test"}
        assert tool["tool_call_id"] == "call"
        assert "duration_s" not in tool  # only the stored result contains timing
    finally:
        for sid in set(server._sessions) - known:
            server._sessions.pop(sid)
    with SessionDB(db_path=home / "state.db") as db:
        assert next(m for m in db.get_messages("resume-tools") if m["role"] == "tool")["content"] == content


def test_missing_result_invocation_is_projected_without_success():
    messages = server._history_to_messages([
        {"role": "user", "content": "Run tests"},
        {"role": "assistant", "content": "", "tool_calls": [invocation()]},
    ])
    assert messages[-1] == {"role": "tool", "tool_call_id": "call", "name": "terminal",
                            "args": {"command": "npm test"}, "context": "npm test"}
    assert "content" not in messages[-1]


def test_live_and_history_share_bounded_json_output_without_mutating_history(monkeypatch):
    output = "start\n" + "x" * (TOOL_RESULT_TEXT_BUDGET * 4) + "\nlast failure"
    raw = json.dumps({"output": output, "exit_code": 2, "duration_s": 2.5})
    history = [{"role": "assistant", "content": "", "tool_calls": [invocation()]},
               {"role": "tool", "tool_call_id": "call", "content": raw}]
    frozen = copy.deepcopy(history)
    emitted = []
    monkeypatch.setattr(server, "_emit_tool_lifecycle", lambda *args: emitted.append(args[-1]))
    monkeypatch.setattr(server, "_tool_progress_enabled", lambda sid: True)
    monkeypatch.setattr(server, "_session_verbose", lambda sid: False)
    monkeypatch.setattr(server, "_prepare_tool_result_metadata", lambda *args: {})
    server._on_tool_complete("display-test", "call", "terminal", {"command": "npm test"}, raw)
    resumed = json.loads(server._history_to_messages(history)[0]["content"])
    assert resumed == emitted[0]["result"]
    assert resumed["exit_code"] == 2
    assert resumed["duration_s"] == 2.5
    assert resumed["output"].endswith("last failure")
    assert "truncated" in resumed["output"]
    assert len(json.dumps(resumed)) < TOOL_RESULT_TEXT_BUDGET + 200
    assert history == frozen


def test_bounding_preserves_read_and_search_structure_and_limits_fanout():
    raw = json.dumps({"content": "1|" + "a" * (TOOL_RESULT_TEXT_BUDGET * 2), "total_lines": 1})
    read = json.loads(bounded_tool_result(raw))
    assert read["content"].startswith("1|")
    assert read["total_lines"] == 1
    matches = {"matches": [{"path": "src/main.ts", "line": i, "content": "a"} for i in range(10_000)], "total_count": 10_000}
    result = bounded_tool_result(matches)
    assert result["total_count"] == 10_000
    assert len(json.dumps(result)) < TOOL_RESULT_TEXT_BUDGET * 2
    assert result["matches"][0] == {"path": "src/main.ts", "line": 0, "content": "a"}
