"""Regression for NousResearch/hermes-agent#156255: finite CLI turns cannot receive process wakes."""

from types import SimpleNamespace

from gateway.session_context import (
    async_delivery_supported,
    clear_session_vars,
    set_session_vars,
)
from gateway.session_finite import finite_turn_scope
from tools.terminal_tool_background import _apply_async_support, _stamp_routing_if_gateway


def test_finite_gateway_turn_does_not_promise_terminal_completion():
    session_key = "agent:main:local:dm:oneshot-test"
    tokens = set_session_vars(
        platform="local", chat_id="oneshot-test", session_key=session_key,
        async_delivery=True,
    )
    try:
        assert async_delivery_supported()

        # A long-lived chat still gets an ordinary completion notification.
        with finite_turn_scope(False):
            regular = SimpleNamespace(id="regular", watcher_platform="")
            enabled, patterns = _apply_async_support(regular, {}, True, None)
            assert (enabled, patterns) == (True, None)
            assert regular.watcher_platform == "local"

        with finite_turn_scope(True):
            # Both terminal notification forms must fall back to polling.
            for notify, patterns in ((True, None), (False, ["ready"])):
                process = SimpleNamespace(id="finite", watcher_platform="")
                result = {}
                enabled, kept_patterns = _apply_async_support(
                    process, result, notify, patterns,
                )
                assert (enabled, kept_patterns) == (False, None)
                assert result["notify_on_complete"] is False
                assert "poll" in result["notify_unsupported"]
                assert process.watcher_platform == ""

            # A foreground command yielded mid-turn uses the same finite gate.
            yielded = SimpleNamespace(
                id="yielded", watcher_platform="", notify_on_complete=True,
            )
            registry = SimpleNamespace(pending_watchers=[])
            _stamp_routing_if_gateway(registry, yielded, session_key)
            assert yielded.notify_on_complete is False
            assert yielded.watcher_platform == ""
            assert registry.pending_watchers == []
    finally:
        clear_session_vars(tokens)
