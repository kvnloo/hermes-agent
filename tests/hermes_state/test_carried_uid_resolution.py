"""Regression for #123985: durable message IDs disambiguate same-stamp compaction carries."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from gateway.run import _build_gateway_agent_history
from hermes_state import SessionDB


def test_equal_timestamp_carried_replies_are_rewound_by_message_uid(tmp_path: Path) -> None:
    """Only carried originals are hidden; an identical uncarried reply stays searchable."""
    path = tmp_path / "state.db"
    session_id = "uid-collision"
    uids = ("1" * 32, "2" * 32, "3" * 32)
    stamp = 1_800_000_100.0

    with closing(SessionDB(db_path=path)) as db:
        db.create_session(session_id, "test")
        for n, uid in enumerate(uids, start=1):
            db.append_message(session_id, "user", f"question {n}", timestamp=stamp + n)
            db.append_message(session_id, "assistant", "identical answer", timestamp=stamp, message_uid=uid)

        replayed, _ = _build_gateway_agent_history(db.get_messages_as_conversation(session_id))
        carried = [
            message for message in replayed
            if message.get("content") in {"question 1", "question 3"}
            or message.get("message_uid") in {uids[0], uids[2]}
        ]
        assert [message["role"] for message in carried] == ["user", "assistant", "user", "assistant"]
        assert all("_row_id" not in message for message in carried)
        assert [message["timestamp"] for message in carried if message["role"] == "assistant"] == [stamp, stamp]

        db.archive_and_compact(
            session_id,
            [{"role": "user", "content": "[CONTEXT COMPACTION] summary"}, *carried],
            carried_messages=carried,
        )

    with sqlite3.connect(path) as conn:
        states = conn.execute(
            "SELECT message_uid, active, compacted FROM messages "
            "WHERE session_id = ? AND role = 'assistant' AND message_uid IN (?, ?, ?)",
            (session_id, *uids),
        ).fetchall()

    def flags(uid: str) -> list[tuple[int, int]]:
        return sorted((active, compacted) for row_uid, active, compacted in states if row_uid == uid)

    assert flags(uids[0]) == [(0, 0), (1, 0)]
    assert flags(uids[1]) == [(0, 1)]
    assert flags(uids[2]) == [(0, 0), (1, 0)]
