#!/usr/bin/env python3
"""Seed the disposable hold-to-drag review board. Never resolves canonical state."""
from __future__ import annotations

import json
import os
from pathlib import Path

from hermes_cli import kanban_db as kb

BOARD = "hold-drag-review"
TASKS = (
    ("t_hold_alpha", "Alpha card", "todo"),
    ("t_hold_beta", "Beta card with nested controls", "todo"),
    ("t_hold_gamma", "Gamma running card", "running"),
    ("t_hold_delta", "Delta review card", "review"),
)


def main() -> None:
    home = Path(os.environ["HERMES_HOME"]).resolve()
    if home == (Path.home() / ".hermes").resolve():
        raise SystemExit("refusing canonical HERMES_HOME")
    kb.create_board(BOARD, name="Hold Drag Review Fixture", description="Disposable browser harness")
    db = kb.init_db(board=BOARD)
    with kb.connect(board=BOARD) as conn:
        for task_id, title, status in TASKS:
            conn.execute(
                "INSERT INTO tasks (id,title,body,status,assignee,created_by,workspace_kind,priority,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,strftime('%s','now'))",
                (task_id, title, "fixture body with nested links and controls", status, "reviewer", "hold-harness", "scratch", 10),
            )
            conn.execute(
                "INSERT INTO task_events(task_id,kind,payload,created_at) VALUES(?,?,?,strftime('%s','now'))",
                (task_id, "created", json.dumps({"fixture": True, "status": status})),
            )
        conn.commit()
    print(db)


if __name__ == "__main__":
    main()
