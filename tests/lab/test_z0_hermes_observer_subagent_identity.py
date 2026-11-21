"""A subagent's stop event belongs to the parent turn that delegated it.

Regression: the host announces ``subagent_stop`` with ``parent_session_id`` /
``parent_turn_id`` / ``child_session_id``, but the observer only read ``session_id`` /
``turn_id``.  Every real subagent row therefore had no trace identity and could not be
joined to the turn that spawned the child.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from hermes_cli.plugins import PluginManager
from tools.delegate_tool_results import _fire_subagent_stop_hooks

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "lab" / "z0_hermes_observer" / "__init__.py"
DEADLINE = 5.0  # seconds; deliberately generous so a loaded CI runner cannot flake


def _load():
    spec = importlib.util.spec_from_file_location("z0_hermes_observer_subagent_identity_plugin", PLUGIN)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def host(tmp_path, monkeypatch):
    """The observer behind a real PluginManager, reached through the real ``invoke_hook`` entry point."""
    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("Z0INT_HERMES_EVENT_PATH", str(spool))
    module = _load()
    manager = PluginManager()
    manager._discovered = True

    class Ctx:
        def register_hook(self, name, callback):
            manager._hooks.setdefault(name, []).append(callback)

    module.register(Ctx())
    monkeypatch.setattr("hermes_cli.plugins.get_plugin_manager", lambda: manager)

    def rows() -> list[dict]:
        assert module.flush(DEADLINE)
        return [json.loads(line) for line in spool.read_text(encoding="utf-8-sig").splitlines()]

    return SimpleNamespace(manager=manager, rows=rows)


def _child_finishes(parent_turn_id: str) -> None:
    """Fire ``subagent_stop`` through the host's own call site, with the payload it really builds."""
    parent = SimpleNamespace(session_id="parent-sess", _current_turn_id=parent_turn_id)
    child = SimpleNamespace(session_id="child-sess")
    results = [{
        "task_index": 0, "status": "completed", "summary": "done", "duration_seconds": 1.5,
        "tool_trace": [], "_child_role": "leaf",
    }]
    _fire_subagent_stop_hooks(results, {0: child}, parent)


def test_real_subagent_stop_joins_the_trace_of_the_turn_that_delegated(host):
    host.manager.invoke_hook("pre_api_request", session_id="parent-sess", turn_id="turn-7", api_request_id="req-1")

    _child_finishes("turn-7")

    pre, stop = host.rows()
    assert (pre["event"], stop["event"]) == ("pre_api_request", "subagent_stop")
    assert stop["identity"]["trace_id"] == pre["identity"]["trace_id"]
    assert stop["identity"]["session_id"] == "parent-sess"
    assert stop["identity"]["turn_id"] == "turn-7"
    assert stop["subagent"]["parent_session_id"] == "parent-sess"
    assert stop["subagent"]["child_session_id"] == "child-sess"


def test_subagent_stop_outside_a_turn_falls_back_to_the_parent_session(host):
    _child_finishes("")  # the host sends an empty parent_turn_id when no turn is current

    (stop,) = host.rows()
    assert stop["identity"]["session_id"] == "parent-sess"
    assert stop["identity"]["trace_id"] == "parent-sess"
