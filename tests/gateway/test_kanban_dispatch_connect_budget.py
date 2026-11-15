"""Regression for NousResearch/hermes-agent#150278: bounded gateway DB opens."""

from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest

from gateway.kanban_watchers_dispatcher import _DispatcherSettings, _KanbanDispatcher
from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc
from hermes_cli import kanban_db_dispatch as kbd


@pytest.fixture
def dispatcher(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    return _KanbanDispatcher(kb, _DispatcherSettings(
        interval=60.0, max_spawn=None, max_in_progress=3, failure_limit=2,
        stale_timeout_seconds=0, reconcile_orphans=False,
        default_assignee=None, max_in_progress_per_profile=None,
    ))


def test_embedded_dispatcher_scans_each_board_once_per_pass(dispatcher, monkeypatch):
    for i in range(7):
        kb.create_board(f"board{i}")

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


@pytest.mark.parametrize("max_spawn", [None, 1])
@pytest.mark.parametrize("initial_running", [0, 2])
def test_host_budget_tracks_spawns_and_existing_workers(
    dispatcher, monkeypatch, max_spawn, initial_running,
):
    from hermes_cli import profiles

    kb.create_board("second")
    dispatcher.settings = replace(dispatcher.settings, max_spawn=max_spawn)
    monkeypatch.setattr(profiles, "profile_exists", lambda name: True)
    monkeypatch.setattr(kbd, "_memory_pressure_level", lambda: "ok")
    spawns = []

    def spawn(task, workspace, board=None):
        spawns.append((board, task.id))

    monkeypatch.setattr(kbd, "_default_spawn", spawn)
    for slug in dispatcher._board_slugs():
        with closing(kbc.connect(board=slug)) as conn:
            if slug == "default":
                for i in range(initial_running):
                    tid = kb.create_task(conn, title=f"busy-{i}", assignee="worker")
                    assert kb.claim_task(conn, tid) is not None
            for i in range(3):
                kb.create_task(conn, title=f"ready-{i}", assignee="worker")

    results = dispatcher.tick_once()
    assert all(result is not None for _, result in results)
    expected = min(3 - initial_running, 2 if max_spawn == 1 else 3)
    assert len(spawns) == expected
    running = []
    for slug in dispatcher._board_slugs():
        with closing(kbc.connect(board=slug)) as conn:
            running.append(kbd.count_running_tasks(conn))
    assert sum(running) == initial_running + expected
    assert sum(running) <= 3
    if max_spawn == 1:
        assert running[1] <= 1


def test_snapshot_does_not_reopen_quarantined_board(dispatcher, monkeypatch):
    import sqlite3

    kb.create_board("broken")
    original_connect = kbc.connect
    attempts = []

    def connect(*args, **kwargs):
        if kwargs.get("board") == "broken":
            attempts.append("broken")
            raise sqlite3.DatabaseError("file is not a database")
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(kbc, "connect", connect)
    results = dict(dispatcher.tick_once())
    assert results["default"] is not None
    assert results["broken"] is None
    assert "broken" in dispatcher.disabled_corrupt_boards
    attempts.clear()

    results = dict(dispatcher.tick_once())
    assert results["default"] is not None
    assert results["broken"] is None
    assert attempts == []
