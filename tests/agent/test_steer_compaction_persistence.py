"""Regression coverage for steer display identity across compactions (#117137)."""

from unittest.mock import patch

from agent.prompt_builder import steer_user_row
from hermes_state import SessionDB
from run_agent import AIAgent


def _agent(db, session_id):
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
    return agent


def test_flushed_steer_keeps_one_display_identity_across_compactions(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    session_id = "steer-compaction"
    agent = _agent(db, session_id)
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


def test_turn_persist_override_never_lands_on_a_steer_row(tmp_path):
    """Compaction re-anchors the persist cursor at ``len(messages)`` -- the slot the NEXT appended row
    takes. When that row is a mid-turn steer, the turn's clean prompt replaced the steer's visible
    content and the steer text survived only in ``api_content`` (seen live: 18 rows in 7 days)."""
    db = SessionDB(tmp_path / "state.db")
    session_id = "steer-override"
    agent = _agent(db, session_id)
    history = [{"role": "user", "content": "ya go ahead"}, {"role": "assistant", "content": "on it"}]
    agent._flush_messages_to_session_db(history, [])
    agent._persist_user_message_idx = len(history)  # the compaction re-anchor
    agent._persist_user_message_override = "ya go ahead"
    agent._persist_user_message_timestamp = 1.0
    agent._persist_user_message_platform_id = "turn-platform-id"
    steer = steer_user_row("fill in the gaps of the rigging")
    messages = [*history, steer]

    agent._apply_persist_user_message_override(messages)
    assert steer["content"].endswith("fill in the gaps of the rigging\n[/OUT-OF-BAND USER MESSAGE]")
    assert "platform_message_id" not in steer and steer.get("timestamp") != 1.0

    agent._flush_messages_to_session_db(messages, [])
    row = [r for r in db.get_messages(session_id) if r["display_kind"] == "steer"][-1]
    assert row["content"] == steer["content"]
    assert row["api_content"] is None
    assert row["timestamp"] != 1.0
