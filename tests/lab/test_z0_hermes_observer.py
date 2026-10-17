from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "lab" / "z0_hermes_observer" / "__init__.py"


def _load():
    spec = importlib.util.spec_from_file_location("z0_hermes_observer_test_plugin", PLUGIN)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registers_observer_surface(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setenv("Z0INT_HERMES_EVENT_PATH", str(tmp_path / "events.jsonl"))
    seen = {}

    class Ctx:
        def register_hook(self, name, callback):
            seen[name] = callback

    module.register(Ctx())
    assert set(seen) == set(module._HOOKS)
    assert {"pre_api_request", "post_api_request", "pre_tool_call", "post_tool_call", "on_session_end"} <= set(seen)
    assert all(callback(test_only=True) is None for callback in seen.values())
    assert module.flush()


def test_metadata_only_default_does_not_persist_content(tmp_path, monkeypatch):
    module = _load()
    path = tmp_path / "events.jsonl"
    monkeypatch.setenv("Z0INT_HERMES_EVENT_PATH", str(path))
    monkeypatch.delenv("Z0INT_HERMES_CAPTURE_SANITIZED_CONTENT", raising=False)

    module.observe(
        "pre_api_request",
        session_id="sess-1",
        task_id="task-1",
        turn_id="turn-1",
        api_request_id="req-1",
        model="model-x",
        provider="provider-x",
        api_call_count=1,
        request_char_count=123,
        request={"body": {"messages": [{"role": "user", "content": "TOP SECRET USER TEXT"}]}},
    )
    assert module.flush()

    raw = path.read_text()
    assert "TOP SECRET USER TEXT" not in raw
    row = json.loads(raw)
    assert row["schema"] == "z0int.hermes_observer_event.v1"
    assert row["event"] == "pre_api_request"
    assert row["identity"]["session_id"] == "sess-1"
    assert row["identity"]["turn_id"] == "turn-1"
    assert row["identity"]["trace_id"]
    assert row["fields"]["request_char_count"] == 123
    assert "request" not in row


def test_trace_identity_is_stable_within_turn(tmp_path, monkeypatch):
    module = _load()
    path = tmp_path / "events.jsonl"
    monkeypatch.setenv("Z0INT_HERMES_EVENT_PATH", str(path))

    common = dict(session_id="sess", task_id="task", turn_id="turn")
    module.observe("pre_api_request", api_request_id="a", **common)
    module.observe("post_api_request", api_request_id="a", usage={"input_tokens": 10, "output_tokens": 2}, **common)
    module.observe("pre_tool_call", tool_call_id="tool-1", tool_name="terminal", args={"command": "secret"}, **common)
    module.observe("on_session_end", completed=True, failed=False, interrupted=False, **common)
    assert module.flush()

    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 4
    assert len({row["identity"]["trace_id"] for row in rows}) == 1
    assert rows[1]["usage"] == {"input_tokens": 10, "output_tokens": 2}
    assert rows[2]["tool"]["arg_keys"] == ["command"]
    assert "secret" not in path.read_text()


def test_observer_failure_is_fail_open(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setenv("Z0INT_HERMES_EVENT_PATH", str(tmp_path / "events.jsonl"))

    def boom(_path, _lines):
        raise OSError("disk full")

    monkeypatch.setattr(module, "_append", boom)
    assert module.observe("post_api_request", session_id="s", turn_id="t") is None
    assert module.flush()
    assert module.stats()["dropped"] == 1
