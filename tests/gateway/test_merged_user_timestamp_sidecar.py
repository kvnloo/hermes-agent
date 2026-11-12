"""Regression for #121836: timestamped gateway replay must retain a merged turn's injected context."""
from agent.message_metadata import MERGED_TURN_PREFIX
from gateway.message_timestamps import render_user_content_with_timestamp
from gateway.run import _build_gateway_agent_history
from hermes_state import SessionDB
from hermes_time import get_timezone


def test_merged_gateway_turn_replays_both_timestamps_and_memory_context(tmp_path):
    notice = "[IMPORTANT: Background process completed]"
    question = "Continue the task"
    memory = "<memory-context>recalled facts</memory-context>"
    notice_time, question_time = 1_700_000_000.0, 1_700_000_120.0
    tz = get_timezone()
    stamped_question = render_user_content_with_timestamp(question, question_time, tz=tz)

    db = SessionDB(db_path=tmp_path / "state.db")
    try:
        db.create_session("sid", source="telegram")
        db.append_message("sid", "assistant", "previous answer", timestamp=notice_time - 60)
        db.append_message("sid", "user", notice, timestamp=notice_time)
        db.append_message(
            "sid", "user", question, timestamp=question_time,
            api_content=f"{stamped_question}\n\n{memory}",
        )
        merged = db.get_messages_as_conversation("sid", repair_alternation=True)
        assert merged[-1][MERGED_TURN_PREFIX] == notice
        replayed, _ = _build_gateway_agent_history(merged, inject_timestamps=True)
    finally:
        db.close()

    stamped_notice = render_user_content_with_timestamp(notice, notice_time, tz=tz)
    assert replayed[-1]["content"] == render_user_content_with_timestamp(
        f"{notice}\n\n{question}", notice_time, tz=tz
    )
    # Replayed API bytes must match the live wire, including the second turn's
    # timestamp and memory prefetch. Losing either invalidates the cached prefix.
    assert replayed[-1]["api_content"] == (
        f"{stamped_notice}\n\n{stamped_question}\n\n{memory}"
    )
