"""Behaviour of the post-lease stale-snapshot guard through ``AIAgent._compress_context`` (#134239 Gap 2).

Every test drives the real facade entrypoint against a real ``SessionDB``; only the summary step
(``ContextCompressor.compress``, the model call) is stubbed. The stale generations are produced by
real compactions from a second agent on the same session, never by hand-built store fixtures, so the
guard is exercised with exactly the rows production leaves behind.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from hermes_state import SessionDB

SESSION_ID = "20260101_000000_aaaaaa"


def _agent(db: SessionDB, label: str, *, in_place: bool = True):
    """A real ``AIAgent`` on ``SESSION_ID`` whose summary step records its input instead of calling a model."""
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
        from run_agent import AIAgent

        agent = AIAgent(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
            model="test/model",
            quiet_mode=True,
            session_db=db,
            session_id=SESSION_ID,
            skip_context_files=True,
            skip_memory=True,
        )
    agent.compression_in_place = in_place
    # The one-time feasibility probe would resolve a real auxiliary provider.
    agent._compression_feasibility_checked = True
    summarized: list[list[str]] = []

    def _summarize(messages, current_tokens=None, focus_topic=None, force=False):
        summarized.append(_contents(messages))
        return [
            {"role": "user", "content": f"[CONTEXT COMPACTION] summary by {label}"},
            {"role": "assistant", "content": f"recent reply by {label}"},
        ]

    agent.context_compressor.compress = _summarize
    return agent, summarized


def _contents(messages) -> list[str]:
    return [m.get("content") for m in messages]


def _held(db: SessionDB) -> list[dict]:
    """The history a surface holds after loading the session: durable rows with their row ids."""
    return db.get_messages_as_conversation(SESSION_ID, include_row_ids=True)


def _live(db: SessionDB, session_id: str = SESSION_ID) -> list[str]:
    return _contents(db.get_messages_as_conversation(session_id))


def _compress(agent, messages, **kwargs):
    return agent._compress_context(messages, "sys", approx_tokens=100_000, **kwargs)


@pytest.fixture
def db(tmp_path):
    session_db = SessionDB(db_path=tmp_path / "state.db")
    session_db.create_session(SESSION_ID, "cli", model="test/model")
    for i in range(8):
        session_db.append_message(
            session_id=SESSION_ID, role="user" if i % 2 == 0 else "assistant", content=f"msg {i}",
        )
    yield session_db
    session_db.close()


def test_snapshot_archived_by_an_earlier_compaction_is_not_summarized(db):
    held = _held(db)
    winner, _ = _agent(db, "winner")
    _compress(winner, _held(db))
    winner_generation = _live(db)
    assert winner_generation == ["[CONTEXT COMPACTION] summary by winner", "recent reply by winner"]

    stale_holder, summarized = _agent(db, "stale holder")
    result, _system_prompt = _compress(stale_holder, held)

    assert summarized == []
    assert _contents(result) == [f"msg {i}" for i in range(8)]
    assert _live(db) == winner_generation
    assert stale_holder.session_id == SESSION_ID


def test_live_snapshot_with_a_concurrent_append_is_still_compacted(db):
    held = _held(db)
    db.append_message(session_id=SESSION_ID, role="user", content="appended by another surface")

    holder, summarized = _agent(db, "holder")
    result, _system_prompt = _compress(holder, held)

    assert summarized == [[f"msg {i}" for i in range(8)]]
    assert _contents(result)[:2] == ["[CONTEXT COMPACTION] summary by holder", "recent reply by holder"]
    live = _live(db)
    assert live[:2] == ["[CONTEXT COMPACTION] summary by holder", "recent reply by holder"]
    assert "appended by another surface" in live
    assert "msg 7" not in live


def test_rotated_parent_is_left_to_child_adoption_even_when_held_rows_are_archived(db):
    held = _held(db)
    in_place_winner, _ = _agent(db, "in-place winner")
    _compress(in_place_winner, _held(db))
    rotator, _ = _agent(db, "rotator", in_place=False)
    _compress(rotator, _held(db))
    child_id = rotator.session_id
    assert child_id != SESSION_ID
    assert db.get_session(SESSION_ID)["end_reason"] == "compression"
    # The held tip is archived, so only the rotation check keeps this out of the stale-abort path.
    assert db.get_message_role(SESSION_ID, held[-1]["_row_id"]) is None

    stale_holder, summarized = _agent(db, "stale holder")
    result, _system_prompt = _compress(stale_holder, held)

    assert summarized == []
    assert stale_holder.session_id == child_id
    assert _contents(result) == _live(db, child_id)


def test_host_snapshot_check_still_vetoes_a_durably_current_snapshot(db):
    holder, summarized = _agent(db, "holder")
    before = _live(db)

    result, _system_prompt = _compress(holder, _held(db), snapshot_is_current=lambda: False)

    assert summarized == []
    assert _contents(result) == before
    assert _live(db) == before
