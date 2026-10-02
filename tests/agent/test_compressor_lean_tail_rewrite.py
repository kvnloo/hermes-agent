"""Preserve lean-tail recovery rewrites across the media extraction in fork issue #420."""

from copy import deepcopy

from agent.context_compressor import (
    ContextCompressor,
    SKILL_PRUNED_MARKER_PREFIX,
    _LEAN_TAIL_DEMOTE_MIN_CHARS,
    _LEAN_TAIL_KEEP_TOOL_ROUNDS,
)


def _tool(call_id: str, content: object) -> dict:
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "tool_name": "terminal",
        "content": content,
        "api_content": "stale wire representation: " + call_id,
    }


def test_lean_tail_demotes_old_results_without_replaying_stale_wire_content():
    compressor = ContextCompressor.__new__(ContextCompressor)
    compressor.quiet_mode = True
    compressor._session_id = "fixture-session"
    long_content = "x" * (_LEAN_TAIL_DEMOTE_MIN_CHARS + 100)
    messages = [
        {"role": "user", "content": "inspect these results"},
        _tool("before-tail", long_content),
    ]
    tail_start = len(messages)
    messages.append({"role": "assistant", "content": "old tool round"})
    old_index = len(messages)
    messages.extend([
        _tool("demote-me", long_content),
        _tool("skill-marker", SKILL_PRUNED_MARKER_PREFIX + "example]" + long_content),
        _tool("short-result", "short"),
        _tool("structured-result", [{"type": "text", "text": long_content}]),
    ])
    # Adjacent tool messages are one round, so both rows in every recent round stay protected.
    for index in range(_LEAN_TAIL_KEEP_TOOL_ROUNDS):
        messages.extend([
            {"role": "assistant", "content": f"recent round {index}"},
            _tool(f"recent-{index}-a", long_content),
            _tool(f"recent-{index}-b", long_content),
        ])
    original = deepcopy(messages)

    result = compressor._demote_stale_tail_tools(messages, tail_start)

    assert result is not messages
    assert len(result) == len(messages)
    assert messages == original
    demoted = result[old_index]
    assert demoted is not messages[old_index]
    assert len(demoted["content"]) < len(long_content)
    assert "session_search" in demoted["content"]
    assert compressor._session_id in demoted["content"]
    assert "api_content" not in demoted
    assert demoted["tool_call_id"] == "demote-me"
    assert demoted["tool_name"] == "terminal"
    for index, message in enumerate(messages):
        if index != old_index:
            assert result[index] is message
