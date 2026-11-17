"""Regression coverage for steer display identity across compactions (#117137)."""

from unittest.mock import patch

from agent.prompt_builder import steer_user_row
from hermes_state import SessionDB
from run_agent import AIAgent


def test_flushed_steer_keeps_one_display_identity_across_compactions(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    session_id = "steer-compaction"
    with (
        patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}),
        patch("agent.model_metadata.fetch_model_metadata", return_value={}),
    ):
        agent = AIAgent(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
            model="test/model",
            quiet_mode=True,
            session_db=db,
            session_id=session_id,
            skip_context_files=True,
            skip_memory=True,
        )
    agent._ensure_db_session()
    steer = steer_user_row("focus on the persistence failure")

    agent._flush_messages_to_session_db([steer], [])

    durable_timestamp = db.get_messages(session_id)[0]["timestamp"]
    assert steer["timestamp"] == durable_timestamp

    for _ in range(2):
        db.archive_and_compact(session_id, [dict(steer)])

    physical = db.get_messages(session_id, include_inactive=True)
    assert len([row for row in physical if row["display_kind"] == "steer"]) == 3
    visible = db.get_messages(session_id, include_compacted=True)
    assert [(row["display_kind"], row["content"]) for row in visible] == [
        ("steer", steer["content"]),
    ]


def test_flushed_steer_row_keeps_content_under_stale_persist_override(tmp_path):
    """#132165 defense-in-depth: even if a stale ``_persist_user_message_idx`` points
    at a steer row, the opening-prompt override must not replace the correction's
    stored content (or displace it into api_content)."""
    import os

    db = SessionDB(tmp_path / "state.db")
    session_id = "steer-stale-override"
    with (
        patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}),
        patch("agent.model_metadata.fetch_model_metadata", return_value={}),
    ):
        agent = AIAgent(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
            model="test/model",
            quiet_mode=True,
            session_db=db,
            session_id=session_id,
            skip_context_files=True,
            skip_memory=True,
        )
    agent._ensure_db_session()
    steer = steer_user_row("focus on the persistence failure")
    agent._persist_user_message_idx = 0
    agent._persist_user_message_override = "the opening prompt"

    agent._flush_messages_to_session_db([steer], [])

    row = db.get_messages(session_id)[0]
    assert row["display_kind"] == "steer"
    assert row["content"] == steer["content"]
    assert row.get("api_content") is None


def test_steer_after_model_switch_keeps_correction_through_repair_and_flush(tmp_path, monkeypatch):
    """#132165, the full sequence: a model-switch marker row precedes the opening prompt, the
    alternation repair merges the two (no exact match for the prompt survives), a mid-turn steer
    row lands after a tool result, and the persist override is flushed. The correction must be
    stored as the steer row's content, not displaced by the opening prompt."""
    from agent.turn_context import _reset_per_turn_agent_state
    from agent.turn_iteration_prep import prepare_iteration

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    db = SessionDB(tmp_path / "state.db")
    agent = AIAgent(
        model="test-model", provider="openai-compat", api_key="test", base_url="http://127.0.0.1:1/v1",
        session_db=db, session_id="steer-after-model-switch", max_iterations=4,
        quiet_mode=True, skip_context_files=True, skip_memory=True,
    )
    agent._ensure_db_session()
    _reset_per_turn_agent_state(agent)
    prompt = "the opening prompt"
    agent._persist_user_message_override = prompt
    messages = [
        {"role": "user", "content": "[System: The active model for this chat has changed to haiku.]",
         "display_kind": "model_switch"},
        {"role": "user", "content": prompt},
    ]
    prep = prepare_iteration(
        agent, messages=messages, api_call_count=1, user_message=prompt, current_turn_user_idx=1,
    )
    messages = prep.messages
    assert len(messages) == 1  # the repair merged the marker into the prompt row
    messages += [
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "t", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "out"},
        steer_user_row("focus on the persistence failure"),
    ]
    prep = prepare_iteration(
        agent, messages=messages, api_call_count=2, user_message=prompt,
        current_turn_user_idx=prep.current_turn_user_idx,
    )
    assert prep.messages[prep.current_turn_user_idx].get("display_kind") != "steer"

    agent._flush_messages_to_session_db(prep.messages, [])

    steer_rows = [row for row in db.get_messages(agent.session_id) if row["display_kind"] == "steer"]
    assert len(steer_rows) == 1
    assert "focus on the persistence failure" in steer_rows[0]["content"]
    assert prompt not in steer_rows[0]["content"]


def test_turn_timestamp_and_platform_id_never_land_on_a_steer_row(tmp_path, monkeypatch):
    """Compaction re-anchors ``_persist_user_message_idx`` at ``len(messages)``, the slot the next appended
    row takes. When that row is a mid-turn steer, the content guard keeps its text, but the turn's
    timestamp and platform_message_id must not be written onto it either (restart dedup keys on the id)."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    db = SessionDB(tmp_path / "state.db")
    session_id = "steer-turn-metadata"
    agent = AIAgent(
        model="test-model", provider="openai-compat", api_key="test", base_url="http://127.0.0.1:1/v1",
        session_db=db, session_id=session_id, max_iterations=4,
        quiet_mode=True, skip_context_files=True, skip_memory=True,
    )
    agent._ensure_db_session()
    history = [{"role": "user", "content": "ya go ahead"}, {"role": "assistant", "content": "on it"}]
    agent._flush_messages_to_session_db(history, [])
    agent._persist_user_message_idx = len(history)  # the compaction re-anchor
    agent._persist_user_message_override = "ya go ahead"
    agent._persist_user_message_timestamp = 1.0
    agent._persist_user_message_platform_id = "turn-platform-id"
    steer = steer_user_row("fill in the gaps of the rigging")
    messages = [*history, steer]

    agent._apply_persist_user_message_override(messages)
    assert "platform_message_id" not in steer and steer.get("timestamp") != 1.0

    agent._flush_messages_to_session_db(messages, [])
    row = [r for r in db.get_messages(session_id) if r["display_kind"] == "steer"][-1]
    assert row["content"] == steer["content"]
    assert row["timestamp"] != 1.0
