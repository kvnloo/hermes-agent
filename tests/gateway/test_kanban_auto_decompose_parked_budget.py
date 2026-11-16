"""Regression for #156280 / #62985: parked lane cards must not starve auto-decompose."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from gateway import kanban_watchers_dispatcher as kwd
from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc
from hermes_cli.config_defaults import DEFAULT_CONFIG


def test_auto_decompose_tick_skips_parked_lanes_before_default_budget(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("HERMES_KANBAN_BOARD", raising=False)
    kb.init_db()

    budget = DEFAULT_CONFIG["kanban"]["auto_decompose_per_tick"]
    with kbc.connect() as conn:
        parked = [
            kb.create_task(
                conn, title=f"human lane work order {i}", assignee="cw-ship",
                triage=True, priority=10,
            )
            for i in range(budget)
        ]
        eligible = kb.create_task(
            conn, title="spawnable work", assignee="engineer", triage=True, priority=0,
        )

    # Exercise the actual gateway tick and its DB-backed triage selection.
    # Only the LLM/graph effect is replaced; profile resolution stays explicit.
    monkeypatch.setattr(kwd, "_board_slugs", lambda _kb: ["default"])
    settings = kwd._DispatcherSettings(
        interval=60.0, max_spawn=None, max_in_progress=None,
        failure_limit=kb.DEFAULT_FAILURE_LIMIT, stale_timeout_seconds=0,
        reconcile_orphans=True, default_assignee=None, max_in_progress_per_profile=None,
    )
    dispatcher = kwd._KanbanDispatcher(kb, settings)
    with patch("hermes_cli.profiles.profile_exists",
               side_effect=lambda name: name == "engineer"), patch.object(
                   kwd._KanbanDispatcher, "_decompose_one", return_value=1,
               ) as decompose_one:
        successes = dispatcher.auto_decompose_tick(budget)

    assert successes == 1
    assert [call.args[2] for call in decompose_one.call_args_list] == [eligible]
    with kbc.connect() as conn:
        for task_id in parked:
            task = kb.get_task(conn, task_id)
            assert task.status == "triage"
            assert task.assignee == "cw-ship"
