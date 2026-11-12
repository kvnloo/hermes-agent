"""Tests for tool-context-trim's transform_tool_result hook (Z21, t_01df79f7).

Run: /workspace/hermes-home/hermes-agent/venv/bin/python -m pytest \
     /workspace/hermes-home/plugins/tool-context-trim/tests/test_trim.py -q
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

PLUGIN_DIR = Path(os.environ.get("HZ21_TEST_PLUGIN_SOURCE", str(Path(__file__).resolve().parents[1])))


def _load():
    spec = importlib.util.spec_from_file_location("tool_context_trim", PLUGIN_DIR / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


@pytest.fixture()
def mod(monkeypatch):
    module = _load()
    monkeypatch.setenv("Z21_TRIM_MAX_CHARS", "100")
    monkeypatch.setenv("Z21_TRIM_HEAD", "40")
    monkeypatch.setenv("Z21_TRIM_TAIL", "20")
    monkeypatch.setenv("Z21_TRIM_DEDUPE_HEAD", "30")
    return module


OSS = {"path": "/mnt/zer0models/workspace/zer0/oss/dash/src/big.py", "offset": 1, "limit": 2000}
OWNER = {"path": "/mnt/zer0models/sft-svlm/data/train.jsonl", "offset": 1, "limit": 2000}
LONG = "".join(f"line {i} " + "x" * 20 + "\n" for i in range(20))  # > 100 chars


def test_long_oss_result_is_capped(mod):
    out = mod._on_transform_tool_result(
        tool_name="read_file", args=OSS, result=LONG, task_id="t1", session_id="s1")
    assert out is not None
    assert "z21 tool-output trim" in out
    assert LONG[:40] in out and LONG[-20:] in out
    assert len(out) < len(LONG) + 200


def test_short_result_untouched(mod):
    assert mod._on_transform_tool_result(
        tool_name="read_file", args=OSS, result="small", session_id="s1") is None


def test_json_result_never_capped(mod):
    long_json = '{"rows": [' + ",".join(f'{{"i": {i}}}' for i in range(200)) + "]}"
    assert len(long_json) > 100
    assert mod._on_transform_tool_result(
        tool_name="trace_query", args={"q": "x"}, result=long_json, session_id="s1") is None


@pytest.mark.parametrize("args", [OWNER, {"path": "/home/kvn/.z0int/auth.json"}])
def test_owner_paths_stay_verbatim(mod, args):
    out = mod._on_transform_tool_result(
        tool_name="read_file", args=args, result=LONG, task_id="", session_id="s-owner")
    assert out is None, "owner-path output must never be trimmed"


def test_identical_read_is_deduped(mod):
    first = mod._on_transform_tool_result(
        tool_name="search_files", args={"pattern": "TODO", "path": "/oss"},
        result=LONG, session_id="s2")
    assert first is not None and "z21 tool-output trim" in first  # first call still trims
    second = mod._on_transform_tool_result(
        tool_name="search_files", args={"pattern": "TODO", "path": "/oss"},
        result="different bytes this time", session_id="s2")
    assert second is not None and "z21 dedupe" in second
    assert LONG[:30] in second and "different bytes this time" not in second


def test_write_clears_the_dedupe_cache(mod):
    args = {"pattern": "TODO", "path": "/oss"}
    mod._on_transform_tool_result(tool_name="search_files", args=args, result=LONG, session_id="s3")
    mod._on_transform_tool_result(tool_name="write_file", args={"path": "/oss/f.py"}, result="ok", session_id="s3")
    third = mod._on_transform_tool_result(tool_name="search_files", args=args, result="after write", session_id="s3")
    assert third is None or "z21 dedupe" not in third


def test_sessions_do_not_share_the_cache(mod):
    args = {"pattern": "TODO", "path": "/oss"}
    mod._on_transform_tool_result(tool_name="search_files", args=args, result=LONG, session_id="s4")
    other = mod._on_transform_tool_result(tool_name="search_files", args=args, result="fresh", session_id="s5")
    assert other is None or "z21 dedupe" not in other


def test_kill_switch(mod, monkeypatch):
    monkeypatch.setenv("Z21_TRIM_OFF", "1")
    assert mod._on_transform_tool_result(
        tool_name="read_file", args=OSS, result=LONG, session_id="s6") is None


def test_non_read_tool_passes_through(mod):
    assert mod._on_transform_tool_result(
        tool_name="terminal", args={"command": "make -j8"}, result="build output", session_id="s7") is None
