"""Mid-turn rotation must not give a surviving steer the original turn's context."""

import copy
import json
from unittest.mock import MagicMock

import pytest

from agent.turn_context import build_api_messages
from agent.turn_context_compaction import _reanchor
from tests.agent.test_replay_cleanup import _SendAgent
from agent.prompt_builder import steer_user_row
from tests.agent.test_compression_adoption_preserves_live_tail import _build_agent_with_db
from tests.agent.test_tool_call_incremental_persistence import _mock_response, _mock_tool_call
from hermes_state import SessionDB


@pytest.mark.parametrize("matches_turn, sidecar", [(True, None), (False, None), (False, "Frozen wire content")])
def test_only_matching_or_stamped_anchors_receive_context(matches_turn, sidecar):
    agent = _SendAgent()
    messages = [
        {"role": "user", "content": "confirm reboot", "timestamp": 1},
        {"role": "assistant", "content": "Acknowledged."},
        {"role": "user", "content": "current ask" if matches_turn else "surviving ask"},
    ]
    if sidecar is not None:
        messages[-1]["api_content"] = sidecar
    idx = _reanchor(agent, messages, "current ask")
    wire, _ = build_api_messages(
        agent, messages, current_turn_user_idx=idx, user_message="current ask",
        ext_prefetch_cache="", plugin_user_context="Live context", moa_config=None,
        active_system_prompt="",
    )
    expected = "current ask\n\nLive context" if matches_turn else sidecar or "surviving ask"
    assert wire[-1]["content"] == expected
    assert agent._persist_user_message_idx == (idx if matches_turn else None)
    if not matches_turn and sidecar is None:
        assert wire[0]["content"] == "confirm reboot"


def test_rotation_preserves_wire_prefix_and_steer_after_finalize(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.title_generator.maybe_auto_title", lambda *a, **kw: None)
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", lambda *a, **kw: [])
    with SessionDB(db_path=tmp_path / "state.db") as db:
        db.create_session("parent", source="cli")
        agent = _build_agent_with_db(db, "parent")
        agent.compression_enabled = False
        agent.save_trajectories = False
        agent._cached_system_prompt = "Fixed system prompt."
        monkeypatch.setattr(agent, "_build_system_prompt", lambda *a, **kw: "Fixed system prompt.")
        agent._gateway_turn_context_notes = "Private context for turn N."
        steer = steer_user_row("Keep the steer instruction intact.")
        agent.context_compressor.compress.side_effect = lambda *a, **kw: [
            {"role": "assistant", "content": "Summary of the work so far."},
            copy.deepcopy(steer),
        ]
        requests = []
        responses = iter([
            _mock_response(content="", finish_reason="tool_calls", tool_calls=[_mock_tool_call()]),
            _mock_response(content="Turn N finished."),
            _mock_response(content="Turn N+1 finished."),
        ])

        def respond(**kwargs):
            requests.append(copy.deepcopy(kwargs["messages"]))
            return next(responses)

        agent.client = MagicMock()
        agent.client.chat.completions.create.side_effect = respond

        def rotate(assistant_message, messages, effective_task_id, api_call_count=0):
            messages.extend([
                {"role": "tool", "tool_call_id": "call_1", "content": "result " * 200},
                copy.deepcopy(steer),
            ])
            compressed, _ = agent._compress_context(
                messages, agent._cached_system_prompt, approx_tokens=10_000,
            )
            messages[:] = compressed

        monkeypatch.setattr(agent, "_execute_tool_calls", rotate)
        turn = agent.run_conversation(
            "Original request with API-only guidance. " * 100,
            persist_user_message="Original clean request.",
        )
        assert agent.session_id != "parent"
        assert turn["final_response"] == "Turn N finished."
        assert len(requests) == 2
        last_wire = [json.dumps(row, sort_keys=True).encode() for row in requests[-1]]
        history = db.get_messages_as_conversation(agent.session_id)
        next_turn = agent.run_conversation("Next request.", conversation_history=history)
        assert next_turn["final_response"] == "Turn N+1 finished."
        next_wire = [json.dumps(row, sort_keys=True).encode() for row in requests[-1]]
        assert next_wire[:len(last_wire)] == last_wire
        assert next(row for row in turn["messages"] if row["role"] == "user")["content"] == steer["content"]
        assert next(row for row in history if row["role"] == "user")["content"] == steer["content"]
