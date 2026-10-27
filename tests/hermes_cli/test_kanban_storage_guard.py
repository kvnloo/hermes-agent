"""Byte-and-inode reserve guard for kanban dispatch."""

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


def sample(*, free_gib=31, free_inodes=6, total_inodes=100):
    return {
        "free_bytes": free_gib * 1024**3,
        "free_inodes": free_inodes,
        "total_inodes": total_inodes,
    }


def test_storage_probe_requires_both_reserves():
    assert kb._storage_pressure_level(sample=sample()) == "ok"
    assert kb._storage_pressure_level(sample=sample(free_gib=29)) == "critical"
    assert kb._storage_pressure_level(sample=sample(free_inodes=4)) == "critical"
    assert kb._storage_pressure_level(sample={}) == "unknown"


def test_dispatch_defers_without_claiming_when_storage_is_critical(
    kanban_home, all_assignees_spawnable, monkeypatch,
):
    monkeypatch.setattr(kb, "_memory_pressure_level", lambda: "ok")
    monkeypatch.setattr(kb, "_storage_pressure_level", lambda path="/workspace": "critical")
    spawns = []
    with kb.connect() as conn:
        task_id = kb.create_task(conn, title="defer", assignee="alice")
        result = kb.dispatch_once(
            conn, spawn_fn=lambda task, workspace, board=None: spawns.append(task.id)
        )
        task = kb.get_task(conn, task_id)
    assert spawns == []
    assert result.storage_pressure == "critical"
    assert task is not None and task.status == "ready"


def test_dispatch_spawns_after_both_reserves_recover(
    kanban_home, all_assignees_spawnable, monkeypatch,
):
    monkeypatch.setattr(kb, "_memory_pressure_level", lambda: "ok")
    monkeypatch.setattr(kb, "_storage_pressure_level", lambda path="/workspace": "ok")
    spawns = []
    with kb.connect() as conn:
        task_id = kb.create_task(conn, title="run", assignee="alice")
        result = kb.dispatch_once(
            conn,
            spawn_fn=lambda task, workspace, board=None: spawns.append(task.id) or 42,
        )
    assert spawns == [task_id]
    assert result.storage_pressure is None


def test_dispatch_checks_the_task_workspace_filesystem_not_global_workspace(
    kanban_home, all_assignees_spawnable, monkeypatch, tmp_path,
):
    """A healthy off-volume task must not be blocked by /workspace pressure."""
    monkeypatch.setattr(kb, "_memory_pressure_level", lambda: "ok")
    healthy_workspace = tmp_path / "healthy-volume" / "repo"
    healthy_workspace.mkdir(parents=True)
    probes = []

    def pressure(path="/workspace"):
        resolved = Path(path).resolve()
        probes.append(resolved)
        return "ok" if resolved == healthy_workspace.resolve() else "critical"

    monkeypatch.setattr(kb, "_storage_pressure_level", pressure)
    spawns = []
    with kb.connect() as conn:
        task_id = kb.create_task(
            conn,
            title="off-volume",
            assignee="alice",
            workspace_kind="dir",
            workspace_path=str(healthy_workspace),
        )
        result = kb.dispatch_once(
            conn,
            spawn_fn=lambda task, workspace, board=None: spawns.append(task.id) or 42,
        )
        task = kb.get_task(conn, task_id)

    assert spawns == [task_id]
    assert probes == [healthy_workspace.resolve()]
    assert result.storage_pressure is None
    assert task is not None and task.status == "running"
