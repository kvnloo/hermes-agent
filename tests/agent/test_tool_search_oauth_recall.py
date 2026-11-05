"""Replay the recorded OAuth alias failure through bridge parsing and real recall I/O.

The model's nested chat_history_lookup argument was not normalized by the
transport's top-level tool-name reversal. No provider or production DB is used.
"""

import json
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("batch", [False, True])
def test_nested_history_alias_reads_the_session_store(tmp_path, batch):
    import model_tools  # noqa: F401
    from agent.inline_tool_executors import INLINE_TOOL_EXECUTORS, InlineToolContext
    from agent.tool_executor import _parse_tool_call
    from hermes_state import SessionDB

    db = SessionDB(tmp_path / "state.db")
    try:
        db.create_session("replayed-history", source="cli")
        db.append_message("replayed-history", role="user", content="Remember the cobalt replay marker")
        agent = SimpleNamespace(
            session_id="current-owner-turn",
            enabled_toolsets=["session_search"],
            disabled_toolsets=[],
            _get_session_db_for_recall=lambda: db,
        )
        entry = {"name": "chat_history_lookup", "arguments": {"session_id": "replayed-history"}}
        call = SimpleNamespace(
            id="recorded-alias-call",
            function=SimpleNamespace(name="tool_call", arguments=json.dumps({"calls": [entry]} if batch else entry)),
        )
        parsed = _parse_tool_call(agent, call)
        assert parsed.parse_error is None
        assert parsed.scope_block is None
        assert parsed.name == "session_search"
        result = json.loads(INLINE_TOOL_EXECUTORS[parsed.name](
            agent, parsed.args, InlineToolContext(effective_task_id="replay"),
        ))
        assert result["success"] is True
        assert any("cobalt replay marker" in row["content"] for row in result["messages"])
        assert call.function.name == "tool_call"  # Transcript pairing stays on the original call.
    finally:
        db.close()


def test_nested_history_alias_does_not_bypass_session_scope():
    import model_tools  # noqa: F401
    from agent.tool_executor import _parse_tool_call

    agent = SimpleNamespace(enabled_toolsets=[], disabled_toolsets=[])
    call = SimpleNamespace(
        id="ungranted-alias-call",
        function=SimpleNamespace(name="tool_call", arguments=json.dumps({
            "calls": [{"name": "chat_history_lookup", "arguments": {"query": "private"}}],
        })),
    )
    parsed = _parse_tool_call(agent, call)
    assert parsed.scope_block and "not available" in parsed.scope_block
    assert parsed.name == "tool_call"
