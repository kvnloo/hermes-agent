"""No built-in tool wait outlasts the 5-minute prompt-cache TTL.

A tool that blocks past the TTL makes the next model call rewrite the whole context, so every default
foreground wait must end before the executor's deadline, and that deadline must end before the TTL.
"""
from unittest.mock import patch

PROMPT_CACHE_TTL_S = 300.0


def test_default_tool_deadline_is_under_the_prompt_cache_ttl(monkeypatch):
    from agent import tool_executor

    monkeypatch.delenv("HERMES_CONCURRENT_TOOL_TIMEOUT_S", raising=False)
    with patch("agent.deadline._timeouts_section", dict):
        concurrent = tool_executor._resolve_concurrent_tool_timeout()
        sequential = tool_executor._resolve_sequential_tool_timeout()
    assert concurrent == sequential == tool_executor._DEFAULT_CONCURRENT_TOOL_TIMEOUT_S
    assert concurrent <= PROMPT_CACHE_TTL_S - 30  # leaves room for the model call that follows


def test_foreground_waits_end_before_the_executor_abandons_them():
    """Terminal and execute_code return their own timeout result (with partial output) first; a longer
    terminal wait is promoted to a tracked background process rather than orphaned by the executor."""
    from agent.tool_executor import _DEFAULT_CONCURRENT_TOOL_TIMEOUT_S
    from tools.code_execution_tool import DEFAULT_TIMEOUT
    from tools.terminal_tool import FOREGROUND_MAX_TIMEOUT

    assert FOREGROUND_MAX_TIMEOUT < _DEFAULT_CONCURRENT_TOOL_TIMEOUT_S
    assert DEFAULT_TIMEOUT < _DEFAULT_CONCURRENT_TOOL_TIMEOUT_S


def test_timeout_result_tells_the_model_to_repoll_or_background():
    from agent.tool_executor import _ToolCallRef, _unfinished_tool_result

    class _Agent:
        _interrupt_requested = False

    ref = _ToolCallRef("terminal", {"command": "sleep 999"}, "task", "call_1", [])
    with patch.object(_ToolCallRef, "emit_post", lambda *a, **k: None):
        result, _duration, _effect = _unfinished_tool_result(_Agent(), ref, timed_out=True, timeout_s=270.0)
    text = str(result)
    assert "timed out after 270.0s" in text
    assert "Re-poll" in text and "background=true" in text and "do not re-run" in text
