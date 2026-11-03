"""Pinned characterization probe, not a production fix or a model recall test."""
import copy
import inspect
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

MAIN_SHA = "e82bf01eec9bb58848209b07f0bc7d8895a39f9b"


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HERMES_RUNTIME_DIR", str(tmp_path / "runtime"))
    def no_network(*args, **kwargs):
        raise AssertionError("network forbidden in deterministic probe")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)


def pinned():
    from agent import context_compressor as cc
    root = Path(cc.__file__).resolve().parents[1]
    assert subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip() == MAIN_SHA
    return cc


def pair(name, args, call_id, content):
    return [{"role": "assistant", "content": "", "tool_calls": [{
        "id": call_id, "type": "function", "function": {
            "name": name, "arguments": json.dumps(args)}}]},
        {"role": "tool", "tool_name": name, "tool_call_id": call_id, "content": content}]


def transcript(tmp_path):
    # Actual UTF-8 bytes on disk, not the four-character text '\\xef'. The memory
    # result is deliberately an injected historical read: main has no read API.
    source = tmp_path / "source.txt"
    source.write_bytes(("café source line\n" * 900).encode("utf-8"))
    body = source.read_text(encoding="utf-8")
    rows = [{"role": "system", "content": "synthetic study"},
            {"role": "user", "content": "load references"}]
    rows += pair("skill_view", {"name": "study-skill"}, "skill", "# study-skill\n" + body)
    rows += pair("memory", {"action": "read", "target": "memory"}, "memory",
                 json.dumps({"success": True, "entries": [body]}))
    for i in range(30):
        rows += [{"role": "user", "content": f"next operation {i}"}]
        rows += pair("terminal", {"command": f"synthetic-{i}"}, f"recent-{i}", f"short-{i}")
    rows += [{"role": "assistant", "content": "finished"}]
    return rows


def observe(tmp_path):
    cc = pinned()
    from agent.context_compressor_tail import demote_stale_tail_tools
    rows = transcript(tmp_path)
    before = copy.deepcopy(rows)
    demoted, count = demote_stale_tail_tools(rows, tail_start=2, session_id="synthetic-session")
    compressor = cc.ContextCompressor(model="study/no-network", config_context_length=100000,
        protect_first_n=1, protect_last_n=20, quiet_mode=True, proactive_prune_tokens=1,
        proactive_prune_min_result_chars=1500, proactive_prune_min_reclaim_tokens=1)
    pruned, prune_count = compressor.prune_tool_results_only(rows, current_tokens=100000)
    assert rows == before, "pruning may not mutate the original transcript"
    assert count == 2 and prune_count >= 2
    outcomes = {}
    for label, result in (("tail_demote", demoted), ("proactive_prune", pruned)):
        stubs = {m["tool_call_id"]: m["content"] for m in result if m.get("role") == "tool"}
        assert cc._skill_pruned_marker("study-skill") in stubs["skill"]
        assert "reload with skill_view(name='study-skill')" in stubs["skill"]
        assert "café" not in stubs["memory"]
        assert "reload" not in stubs["memory"].lower()
        assert "memory(action=" not in stubs["memory"]
        if label == "tail_demote":
            assert "session_search(" in stubs["memory"]
        outcomes[label] = {"skill_stub": stubs["skill"], "memory_stub": stubs["memory"],
                           "skill_reload_marker": True, "memory_reload_marker": False}
    return {"main_sha": MAIN_SHA, "verdict": "PARTIAL",
            "mechanism_verdict": "CONFIRMED",
            "reason": "Missing memory reload marker confirmed on injected historical read; current main has no memory read/doc API.",
            "memory_read_dispatch": "unsupported", "doc_read": "SKIPPED: unsupported on pinned main",
            "outcomes": outcomes}


def test_real_demote_and_proactive_prune(tmp_path):
    receipt = observe(tmp_path)
    out = os.environ.get("RFC_OUT")
    if out:
        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / "demote-gap.json").write_text(json.dumps(receipt, indent=2) + "\n")


def test_read_dispatch_is_not_shipped():
    pinned()
    from tools.memory_tool import MemoryStore, memory_tool
    result = json.loads(memory_tool(action="read", target="memory", store=MemoryStore()))
    assert result["success"] is False
    assert "Unknown action 'read'" in result["error"]


def test_doc_read_when_supported(tmp_path):
    pinned()
    from tools.memory_tool import memory_tool, MemoryStore
    if "doc" not in inspect.signature(memory_tool).parameters:
        pytest.skip("pinned main has no doc parameter or chain-doc read support")
    # Fail closed on a future signature change: a new pin needs a real fixture.
    pytest.fail("doc support appeared; define and review its real on-disk fixture before repinning")


@pytest.mark.parametrize("size,recent_rounds,expected", [(1499, 7, False), (1500, 6, True), (1500, 5, False)])
def test_tail_boundary(size, recent_rounds, expected):
    pinned()
    from agent.context_compressor_tail import demote_stale_tail_tools
    rows = pair("memory", {"action": "read"}, "old", "x" * size)
    for i in range(recent_rounds):
        rows += pair("terminal", {"command": str(i)}, str(i), "short")
    result, count = demote_stale_tail_tools(rows, 0, "test")
    assert (result[1]["content"] != rows[1]["content"]) is expected
    assert count == int(expected)
