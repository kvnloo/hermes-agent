"""terminal ``notify`` accepts bool-ish strings after provider/schema round-trips.

Origin: NousResearch/hermes-agent#123345 — models emit ``notify=true`` but some
transports deliver the string ``"true"`` (anyOf boolean|array). The dispatch
wrapper must coerce recognized tokens onto ``notify_on_complete`` and still
fail closed on unrecognized values.
"""
import json

import pytest

from tools import terminal_tool as tt


@pytest.fixture
def capture_terminal(monkeypatch):
    captured = {}

    def fake_terminal_tool(**kwargs):
        captured.clear()
        captured.update(kwargs)
        return json.dumps(
            {"output": "Background process started", "session_id": "proc_x", "exit_code": 0}
        )

    monkeypatch.setattr(tt, "terminal_tool", fake_terminal_tool)
    return captured


def _dispatch(args):
    return json.loads(tt._handle_terminal(args))


@pytest.mark.parametrize(
    "notify",
    [True, "true", "TRUE", "1", "yes", "on", " True "],
)
def test_notify_truthy_coerces_to_notify_on_complete(capture_terminal, notify):
    result = _dispatch({"command": "sleep 1", "background": True, "notify": notify})
    assert not result.get("error"), result
    assert capture_terminal["notify_on_complete"] is True
    assert capture_terminal["watch_patterns"] is None


@pytest.mark.parametrize(
    "notify",
    [False, "false", "FALSE", "0", "no", "off", " False "],
)
def test_notify_falsy_coerces_to_silent_background(capture_terminal, notify):
    result = _dispatch({"command": "sleep 1", "background": True, "notify": notify})
    assert not result.get("error"), result
    assert capture_terminal["notify_on_complete"] is False
    assert capture_terminal["watch_patterns"] is None


def test_notify_pattern_list_still_sets_watch_patterns(capture_terminal):
    result = _dispatch(
        {"command": "sleep 1", "background": True, "notify": ["Application startup complete"]}
    )
    assert not result.get("error"), result
    assert capture_terminal["notify_on_complete"] is False
    assert capture_terminal["watch_patterns"] == ["Application startup complete"]


@pytest.mark.parametrize("notify", ["maybe", "tru", 2, {"ok": True}, 1.5])
def test_notify_unrecognized_fails_closed(capture_terminal, notify):
    result = _dispatch({"command": "sleep 1", "background": True, "notify": notify})
    assert result.get("error")
    assert "notify must be true/false" in result["error"]
    assert capture_terminal == {}


def test_string_notify_true_still_refused_on_foreground(capture_terminal):
    result = _dispatch({"command": "sleep 1", "notify": "true"})
    assert result.get("error")
    assert "background" in result["error"]
    assert capture_terminal == {}


def test_string_false_notify_allows_foreground(capture_terminal):
    result = _dispatch({"command": "echo unchanged", "notify": "false"})
    assert not result.get("error"), result
    assert capture_terminal["background"] is False
    assert capture_terminal["notify_on_complete"] is False
    assert capture_terminal["watch_patterns"] is None


@pytest.mark.parametrize("notify", [False, "false"])
def test_explicit_false_overrides_legacy_flags_before_foreground_gate(capture_terminal, notify):
    result = _dispatch({
        "command": "echo unchanged", "notify": notify,
        "notify_on_complete": True, "watch_patterns": ["stale legacy pattern"],
    })
    assert not result.get("error"), result
    assert capture_terminal["background"] is False
    assert capture_terminal["notify_on_complete"] is False
    assert capture_terminal["watch_patterns"] is None


def test_explicit_pattern_list_overrides_legacy_completion_without_filtering(capture_terminal):
    patterns = ["ready", "  literal spaces  "]
    result = _dispatch({
        "command": "echo unchanged", "background": True,
        "notify": patterns, "notify_on_complete": True,
    })
    assert not result.get("error"), result
    assert capture_terminal["notify_on_complete"] is False
    assert capture_terminal["watch_patterns"] is patterns


@pytest.mark.parametrize("notify", [{"pattern": "ready"}, ("ready",), '["ready"]'])
def test_unsupported_pattern_representations_do_not_dispatch(capture_terminal, notify):
    result = _dispatch({"command": "echo unchanged", "background": True, "notify": notify})
    assert "notify must be true/false" in result.get("error", "")
    assert capture_terminal == {}


def test_native_true_notify_still_refused_on_foreground(capture_terminal):
    result = _dispatch({"command": "echo unchanged", "notify": True})
    assert "background" in result.get("error", "")
    assert capture_terminal == {}
