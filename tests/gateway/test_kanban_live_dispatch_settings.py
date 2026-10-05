"""Edited dispatch settings reach the real board consumer without restarting (#117734)."""
import asyncio
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_config_edit_reaches_dispatch_caps_and_wait_without_ignoring_pause(tmp_path, monkeypatch):
    from agent.estop import sentinel_path
    import gateway.kanban_watchers as watchers
    from hermes_cli import kanban_db_dispatch

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path))
    database_path = tmp_path / "fixture.db"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(database_path))
    monkeypatch.delenv("HERMES_KANBAN_BOARD", raising=False)
    monkeypatch.delenv("HERMES_KANBAN_TASK", raising=False)
    monkeypatch.delenv("HERMES_KANBAN_DISPATCH_IN_GATEWAY", raising=False)
    config_path = tmp_path / "config.yaml"

    def write_config(cap, interval):
        config_path.write_text(
            "kanban:\n  dispatch_in_gateway: true\n  auto_decompose: false\n"
            f"  max_spawn: {cap}\n  dispatch_interval_seconds: {interval}\n"
            "  max_in_progress: 3\n", encoding="utf-8",
        )

    write_config(1, 3)
    runner = watchers.GatewayKanbanWatchersMixin()
    runner._running = True
    received_caps = []
    waits = []

    def inert_dispatch(connection, *, board, **settings):
        # The real dispatcher has opened the temporary board and expanded its
        # resolved settings. Stop at the execution boundary: never launch jobs.
        assert Path(connection.execute("PRAGMA database_list").fetchone()[2]) == database_path
        received_caps.append(settings["max_spawn"])
        if len(received_caps) == 1:
            write_config(2, 7)
        else:
            sentinel_path().write_text("fixture pause", encoding="utf-8")
        return kanban_db_dispatch.DispatchResult()

    async def no_startup_delay(_seconds):
        return None

    async def next_tick(interval):
        waits.append(interval)
        if len(waits) == 3:
            runner._running = False

    monkeypatch.setattr(kanban_db_dispatch, "dispatch_once", inert_dispatch)
    monkeypatch.setattr(kanban_db_dispatch, "reap_worker_zombies", lambda: [])
    monkeypatch.setattr(watchers.asyncio, "sleep", no_startup_delay)
    monkeypatch.setattr(runner, "_sleep_between_ticks", next_tick)
    try:
        await asyncio.wait_for(runner._kanban_dispatcher_watcher(), timeout=5)
    finally:
        runner._release_kanban_dispatcher_lock()
    assert received_caps == [1, 2]
    assert waits == [3.0, 7.0, 7.0]
