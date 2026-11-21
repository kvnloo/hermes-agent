"""Regression for NousResearch/hermes-agent#150278: bounded gateway DB opens."""

from pathlib import Path

from gateway.kanban_watchers_dispatcher import _DispatcherSettings, _KanbanDispatcher
from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc


def test_embedded_dispatcher_scans_each_board_once_per_pass(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    for i in range(7):
        kb.create_board(f"board{i}")

    settings = _DispatcherSettings(
        interval=60.0,
        max_spawn=None,
        max_in_progress=3,
        failure_limit=2,
        stale_timeout_seconds=0,
        reconcile_orphans=False,
        default_assignee=None,
        max_in_progress_per_profile=None,
    )
    dispatcher = _KanbanDispatcher(kb, settings)
    boards = dispatcher._board_slugs()
    assert len(boards) >= 7

    connects = []
    original_connect = kbc.connect

    def tracked_connect(*args, **kwargs):
        connects.append(kwargs.get("board"))
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(kbc, "connect", tracked_connect)
    results = dispatcher.tick_once()

    assert len(results) == len(boards)
    assert all(result is not None for _, result in results)
    assert len(connects) <= 3 * len(boards), (len(connects), len(boards))
