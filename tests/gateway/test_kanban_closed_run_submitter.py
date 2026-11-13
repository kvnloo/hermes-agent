"""The bound Kanban interpreter exits after a terminal run loses its PID (#154563)."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from hermes_cli.kanban_db_dispatch import TERMINAL_WORKER_REAP_GRACE_SECONDS


def test_submitter_watches_ended_run_even_after_reaper_clears_pid(tmp_path):
    db = tmp_path / "board.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE task_runs (id INTEGER PRIMARY KEY, worker_pid INTEGER, "
            "worker_started_at TEXT, ended_at INTEGER)"
        )
        conn.execute(
            "INSERT INTO task_runs (id, worker_pid, worker_started_at, ended_at) "
            "VALUES (1, NULL, NULL, ?)",
            (int(time.time()),),
        )

    # Real submitter thread in a separate process; the reaper has cleared PID.
    child_code = """
import sys
from pathlib import Path
from threading import Event
from gateway.session_kanban import _watch_submitter
_watch_submitter(Path(sys.argv[1]), 1)
Event().wait(3)
"""
    # Both invariants belong to one regression: preserve the real completion
    # grace, yet stop a worker whose closed run has aged past that grace.
    for ended_ago, expected_exit in (
        (0, 0),
        (TERMINAL_WORKER_REAP_GRACE_SECONDS + 5, 1),
    ):
        with sqlite3.connect(db) as conn:
            conn.execute(
                "UPDATE task_runs SET ended_at=? WHERE id=1",
                (int(time.time()) - ended_ago,),
            )
        result = subprocess.run(
            [sys.executable, "-c", child_code, str(db)],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert result.returncode == expected_exit, result.stdout + result.stderr
