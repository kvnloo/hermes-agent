"""Kanban dispatch must throttle on CPU/load, not only RAM."""

from pathlib import Path

import pytest

from hermes_cli import kanban_db as kb


@pytest.fixture
def kanban_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    return home


@pytest.fixture(autouse=True)
def storage_reserve_ok(monkeypatch):
    monkeypatch.setattr(kb, "_storage_pressure_level", lambda path="/workspace": "ok")


def test_compute_pressure_unknown_on_empty_sample():
    assert kb._compute_pressure_level({}) == "unknown"
    assert kb._compute_pressure_level({"nproc": 0, "load1": 1.0}) == "unknown"


def test_compute_pressure_classifies_load_per_cpu():
    assert kb._compute_pressure_level({"nproc": 20, "load1": 4.0}) == "ok"
    assert kb._compute_pressure_level({"nproc": 20, "load1": 18.0}) == "elevated"
    assert kb._compute_pressure_level({"nproc": 20, "load1": 25.0}) == "critical"


def test_dispatch_spawns_nothing_under_critical_compute(
    kanban_home, all_assignees_spawnable, monkeypatch,
):
    monkeypatch.setattr(
        kb, "_system_compute_sample", lambda: {"nproc": 20, "load1": 30.0}
    )
    spawns = []

    def fake_spawn(task, workspace, board=None):
        spawns.append(task.id)
        return 42

    with kb.connect() as conn:
        for title in ("a", "b", "c"):
            kb.create_task(conn, title=title, assignee="alice")
        res = kb.dispatch_once(conn, spawn_fn=fake_spawn)

    assert not spawns
    assert not res.spawned
    assert res.compute_pressure == "critical"


def test_dispatch_elevated_compute_spawns_at_most_one(
    kanban_home, all_assignees_spawnable, monkeypatch,
):
    monkeypatch.setattr(
        kb, "_system_compute_sample", lambda: {"nproc": 20, "load1": 18.0}
    )
    spawns = []

    def fake_spawn(task, workspace, board=None):
        spawns.append(task.id)
        return 42

    with kb.connect() as conn:
        for title in ("a", "b", "c"):
            kb.create_task(conn, title=title, assignee="alice")
        res = kb.dispatch_once(conn, spawn_fn=fake_spawn)

    assert len(spawns) == 1
    assert res.compute_pressure == "elevated"


def test_dispatch_ok_compute_does_not_cap_below_caller_budget(
    kanban_home, all_assignees_spawnable, monkeypatch,
):
    monkeypatch.setattr(
        kb, "_system_compute_sample", lambda: {"nproc": 20, "load1": 2.0}
    )
    spawns = []

    def fake_spawn(task, workspace, board=None):
        spawns.append(task.id)
        return 42

    with kb.connect() as conn:
        for title in ("a", "b", "c"):
            kb.create_task(conn, title=title, assignee="alice")
        res = kb.dispatch_once(conn, spawn_fn=fake_spawn)

    assert len(spawns) == 3
    assert res.compute_pressure is None
