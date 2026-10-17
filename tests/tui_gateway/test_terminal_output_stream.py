"""Foreground ANSI output delivery, ownership, bounded replay and final reconciliation (#572)."""
import json
import shlex
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import tui_gateway.server as server
from tools.environments.local import LocalEnvironment
from tools.terminal_output import current_output_callback, tool_output_scope
from tui_gateway.contracts.events import ToolOutputDeltaPayload


def session():
    return {"history_lock": threading.RLock(), "inflight_turn": {"streaming": True, "user": "run"}}


def install(monkeypatch, sid, record, frames):
    monkeypatch.setitem(server._sessions, sid, record)
    monkeypatch.setattr(server, "_emit", lambda event, sid, payload=None: frames.append((event, sid, payload)))
    monkeypatch.setattr(server, "_tool_progress_enabled", lambda _: True)
    monkeypatch.setattr(server, "_session_verbose", lambda _: False)


def test_real_process_stream_preserves_ansi_carriage_return_split_utf8_and_final(monkeypatch, tmp_path):
    frames = []
    record = session()
    install(monkeypatch, "ansi", record, frames)
    callback = server._agent_cbs("ansi")["tool_progress_callback"]
    env = LocalEnvironment(cwd=str(tmp_path), timeout=10)
    args = {"command": "unicode output"}
    server._on_tool_start("ansi", "call", "terminal", args)
    code = "import os,time;os.write(1,b'\\x1b[31m\\xe7');time.sleep(.05);os.write(1,b'\\xb4\\x85\\x1b[0m\\r100% \\xe2\\x9c\\x93\\n')"
    with tool_output_scope(callback, "terminal", "call"):
        result = env.execute(f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}", bounded_capture=True,
                             output_callback=current_output_callback())
    deltas = [p for event, _, p in frames if event == "tool.output.delta"]
    assert deltas
    assert "".join(p["text"] for p in deltas) == "\x1b[31m紅\x1b[0m\r100% ✓\n"
    assert [p["seq"] for p in deltas] == list(range(1, len(deltas) + 1))
    assert result["output"] == "\x1b[31m紅\x1b[0m\r100% ✓\n"
    for payload in deltas:
        ToolOutputDeltaPayload.model_validate(payload)
    snapshot = server._inflight_snapshot(record)
    assert snapshot["tools"][0]["output"]["operation"] == "replace"
    assert snapshot["tools"][0]["output"]["text"] == result["output"]
    server._on_tool_complete("ansi", "call", "terminal", args, json.dumps({"output": "final", "exit_code": 0}))
    assert "tools" not in server._inflight_snapshot(record)
    before = len(frames)
    callback("tool.output.delta", "terminal", "late", None, tool_call_id="call", stream_id=deltas[0]["stream_id"])
    assert len(frames) == before
    assert current_output_callback() is None


def test_concurrent_calls_have_independent_generation_and_scope(monkeypatch, tmp_path):
    frames = []
    record = session()
    install(monkeypatch, "parallel", record, frames)
    callback = server._agent_cbs("parallel")["tool_progress_callback"]
    for call_id in ("a", "b"):
        server._on_tool_start("parallel", call_id, "terminal", {})
    barrier = threading.Barrier(2)

    def run(call_id):
        with tool_output_scope(callback, "terminal", call_id):
            barrier.wait(timeout=10)
            env = LocalEnvironment(cwd=str(tmp_path), timeout=10)
            env.execute(f"printf '{call_id}\\r{call_id} ✓'", bounded_capture=True, output_callback=current_output_callback())
        assert current_output_callback() is None

    with ThreadPoolExecutor(2) as pool:
        list(pool.map(run, ("a", "b")))
    deltas = [p for event, _, p in frames if event == "tool.output.delta"]
    for call_id in ("a", "b"):
        own = [p for p in deltas if p["tool_id"] == call_id]
        assert "".join(p["text"] for p in own) == f"{call_id}\r{call_id} ✓"
    assert len({p["stream_id"] for p in deltas}) == 2


def test_bounded_snapshot_replaces_with_head_tail_and_rejects_retired_turn(monkeypatch):
    import tui_gateway.tool_output as output
    monkeypatch.setattr(output, "get_max_bytes", lambda: 200)
    frames = []
    record = session()
    install(monkeypatch, "bounded", record, frames)
    callback = server._agent_cbs("bounded")["tool_progress_callback"]
    server._on_tool_start("bounded", "a", "terminal", {})
    with tool_output_scope(callback, "terminal", "a"):
        sink = current_output_callback()
        sink("head\n" + "x" * 500 + "\ntail")
        payload = frames[-1][2]
        assert payload["operation"] == "replace" and payload["capture_truncated"]
        assert len(payload["text"]) <= 200
        assert payload["text"].startswith("head") and payload["text"].endswith("tail")
        snapshot = server._inflight_snapshot(record)
        assert snapshot["tools"][0]["output"] == payload
        record["inflight_turn"] = {"streaming": True, "user": "new turn"}
        server._on_tool_start("bounded", "a", "terminal", {})
        before = len(frames)
        sink("stale")
        assert len(frames) == before
    with tool_output_scope(callback, "terminal", "a"):
        current_output_callback()("new")
    assert frames[-1][2]["turn_id"] != payload["turn_id"]


def test_nonterminal_nested_scope_does_not_leak_and_exception_restores():
    frames = []
    callback = lambda *args, **kwargs: frames.append((args, kwargs))
    with tool_output_scope(callback, "terminal", "a"):
        outer = current_output_callback()
        with tool_output_scope(callback, "read_file", "b"):
            assert current_output_callback() is None
        assert current_output_callback() is outer
        try:
            with tool_output_scope(callback, "terminal", "c"):
                raise ValueError("test")
        except ValueError:
            pass
        assert current_output_callback() is outer
    assert current_output_callback() is None
