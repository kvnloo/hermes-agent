"""#123345: a stringified boolean ``notify`` must behave like the boolean it spells.

Production dispatch (``model_tools.handle_function_call``) runs
``coerce_tool_args`` before the registry handler, so the contract is checked
through that same two-step path: ``coerce_tool_args("terminal", args)`` then
``_handle_terminal(args)``. A fix in either layer satisfies it.
"""
import json

import pytest

from tools import terminal_tool as tt
from tools.arg_coercion import coerce_tool_args


@pytest.fixture
def captured(monkeypatch):
    calls = {}

    def fake_terminal_tool(**kwargs):
        calls.clear()
        calls.update(kwargs)
        return json.dumps({"output": "ok", "session_id": "proc_x", "exit_code": 0})

    monkeypatch.setattr(tt, "terminal_tool", fake_terminal_tool)
    return calls


def _dispatch(args):
    return json.loads(tt._handle_terminal(coerce_tool_args("terminal", dict(args))))


@pytest.mark.parametrize(
    "notify, expected",
    [("true", True), ("True", True), ("false", False), ("FALSE", False), (True, True), (False, False)],
)
def test_background_bool_or_bool_string_notify_maps_to_notify_on_complete(captured, notify, expected):
    result = _dispatch({"command": "sleep 1", "background": True, "notify": notify})
    assert not result.get("error"), result
    assert captured["notify_on_complete"] is expected
    assert captured["watch_patterns"] is None


def test_foreground_string_notify_false_is_a_no_op_like_native_false(captured):
    result = _dispatch({"command": "echo hi", "notify": "false"})
    assert not result.get("error"), result
    assert captured["notify_on_complete"] is False


def test_foreground_string_notify_true_is_still_refused(captured):
    result = _dispatch({"command": "echo hi", "notify": "true"})
    assert "background" in result.get("error", "")
    assert captured == {}


def test_pattern_list_still_maps_to_watch_patterns(captured):
    result = _dispatch({"command": "serve", "background": True, "notify": ["ready"]})
    assert not result.get("error"), result
    assert captured["watch_patterns"] == ["ready"]
    assert captured["notify_on_complete"] is False


def test_unrecognized_string_never_enables_completion_notify(captured):
    result = _dispatch({"command": "sleep 1", "background": True, "notify": "maybe"})
    assert result.get("error") or captured.get("notify_on_complete") is False
