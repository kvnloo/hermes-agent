"""The kanban dispatcher spawns no worker while the disk guard reads critical (disk-full cascade).

Before: workers kept being spawned into a full volume and died with
"No reply: Hermes couldn't save this conversation to disk" after paying for model calls.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from gateway import disk_status
from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc
from hermes_cli import kanban_db_dispatch as kbd


@pytest.fixture
def kanban_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    return home


def _spawner(spawns):
    def fake_spawn(task, workspace, board=None):
        spawns.append(task.id)
        return 42
    return fake_spawn


def test_critical_disk_spawns_nothing_and_keeps_tasks_ready(kanban_home, all_assignees_spawnable, monkeypatch):
    monkeypatch.setattr(disk_status, "new_work_refusal", lambda *a, **k: "disk critical: 100 MB free")
    spawns: list = []
    with kbc.connect() as conn:
        ids = [kb.create_task(conn, title=t, assignee="alice") for t in ("a", "b")]
        res = kbd.dispatch_once(conn, spawn_fn=_spawner(spawns))
        statuses = {r["id"]: r["status"] for r in conn.execute("SELECT id, status FROM tasks")}
    assert spawns == [] and res.spawned == []
    assert res.disk_pressure == "critical"
    assert all(statuses[i] == "ready" for i in ids), statuses
    assert "disk_pressure=critical" in kbd.describe_suppression([res])


def test_healthy_disk_dispatches_normally(kanban_home, all_assignees_spawnable, monkeypatch):
    monkeypatch.setattr(disk_status, "new_work_refusal", lambda *a, **k: None)
    spawns: list = []
    with kbc.connect() as conn:
        kb.create_task(conn, title="a", assignee="alice")
        res = kbd.dispatch_once(conn, spawn_fn=_spawner(spawns))
    assert len(spawns) == 1
    assert res.disk_pressure is None


def test_a_broken_guard_fails_open(kanban_home, all_assignees_spawnable, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("statvfs exploded")
    monkeypatch.setattr(disk_status, "new_work_refusal", boom)
    spawns: list = []
    with kbc.connect() as conn:
        kb.create_task(conn, title="a", assignee="alice")
        kbd.dispatch_once(conn, spawn_fn=_spawner(spawns))
    assert len(spawns) == 1
