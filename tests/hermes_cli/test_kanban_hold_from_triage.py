"""A judged hold can move a loop-triaged card into a human-owned block."""

from pathlib import Path

import pytest

from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc


@pytest.fixture
def kanban_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    return home


def test_judged_hold_moves_triage_to_blocked(kanban_home: Path) -> None:
    """Only a judged hold may move a recurrence-triaged card to blocked."""
    with kbc.connect_closing() as conn:
        tid = kb.create_task(conn, title="await owner decision", assignee="worker")
        with kb.write_txn(conn):
            conn.execute("UPDATE tasks SET status = 'ready' WHERE id = ?", (tid,))

        # Exercise the real recurrence breaker using its configured default.
        for attempt in range(kb.BLOCK_RECURRENCE_LIMIT):
            assert kb.claim_task(conn, tid, claimer="worker") is not None
            assert kb.block_task(conn, tid, reason="missing access", kind="capability")
            if attempt + 1 < kb.BLOCK_RECURRENCE_LIMIT:
                assert kb.unblock_task(conn, tid)

        triaged = kb.get_task(conn, tid)
        assert triaged.status == "triage"
        assert triaged.current_run_id is None
        assert not kb.block_task(conn, tid, reason="unjudged", kind="needs_input")
        assert kb.get_task(conn, tid).status == "triage"

        condition = "release after owner approves access"
        assert kb.block_task(conn, tid, reason=condition, kind="hold")

        held = kb.get_task(conn, tid)
        assert (held.status, held.block_kind, held.block_recurrences) == (
            "blocked", "hold", 1,
        )
        assert held.current_run_id is None

        events = kb.list_events(conn, tid)
        holds = [
            event.payload for event in events
            if event.kind == "blocked" and (event.payload or {}).get("kind") == "hold"
        ]
        assert len(holds) == 1
        assert holds[0]["source_status"] == "triage"
        assert holds[0]["condition"] == condition
        assert holds[0]["judged"] is True
        assert len([event for event in events if event.kind == "block_loop_detected"]) == 1
