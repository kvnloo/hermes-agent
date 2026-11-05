"""A Kanban host stall does not reset a previously counted worker failure.

Regression for moken627-hub's #146324 (report: nehaturov-hue, #148958).
"""
import sqlite3
from pathlib import Path

from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_dispatch as kbd


def test_host_stall_preserves_genuine_failure_streak(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    conn = sqlite3.connect(str(kb.kanban_db_path()))
    conn.row_factory = sqlite3.Row
    try:
        task_id = kb.create_task(conn, title="host stall then true failure", assignee="a")
        assert kb.claim_task(conn, task_id) is not None
        with kb.write_txn(conn):
            conn.execute("UPDATE tasks SET consecutive_failures=1 WHERE id=?", (task_id,))
        host = kbd._DeadWorker(
            "infrastructure_failure", kb.KANBAN_INFRASTRUCTURE_EXIT_CODE,
            "pid 100 exited 74: owner silent", "crashed",
            {"pid": 100, "claimer": "test"}, infrastructure_failure=True,
        )
        assert kbd._account_crashes(conn, [(task_id, 100, "test", host)]) == []
        assert conn.execute(
            "SELECT consecutive_failures FROM tasks WHERE id=?", (task_id,),
        ).fetchone()[0] == 1
        real = kbd._DeadWorker(
            "nonzero_exit", 1, "pid 101 exited 1: worker failed",
            "crashed", {"pid": 101, "claimer": "test"},
        )
        assert kbd._account_crashes(conn, [(task_id, 101, "test", real)]) == [task_id]
        row = conn.execute(
            "SELECT status, consecutive_failures FROM tasks WHERE id=?", (task_id,),
        ).fetchone()
        assert (row["status"], row["consecutive_failures"]) == ("blocked", 2)
        assert conn.execute(
            "SELECT COUNT(*) FROM task_events WHERE task_id=? AND kind='gave_up'",
            (task_id,),
        ).fetchone()[0] == 1
    finally:
        conn.close()
