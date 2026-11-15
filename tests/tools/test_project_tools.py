import json
import os

from hermes_cli import projects_db
from tools import project_tools


def test_project_create_without_path_reports_that_chat_was_not_moved(monkeypatch, tmp_path):
    monkeypatch.setattr(projects_db, "projects_db_path", lambda: tmp_path / "projects.db")
    callback_calls = []
    project_tools.set_project_workspace_callback(lambda *args: callback_calls.append(args) or True)

    result = json.loads(project_tools.project_create("Empty", task_id="session-1"))

    assert result["success"] is True
    assert result["moved"] is False
    assert "not moved" in result["warning"].lower()
    assert callback_calls == []


def test_project_switch_to_empty_project_reports_that_chat_was_not_moved(monkeypatch, tmp_path):
    monkeypatch.setattr(projects_db, "projects_db_path", lambda: tmp_path / "projects.db")
    callback_calls = []
    project_tools.set_project_workspace_callback(lambda *args: callback_calls.append(args) or True)
    with projects_db.connect_closing() as conn:
        projects_db.create_project(conn, name="Empty")

    result = json.loads(project_tools.project_switch("empty", task_id="session-1"))

    assert result["success"] is True
    assert result["moved"] is False
    assert "not moved" in result["warning"].lower()
    assert callback_calls == []


def test_project_create_reports_successful_workspace_move(monkeypatch, tmp_path):
    monkeypatch.setattr(projects_db, "projects_db_path", lambda: tmp_path / "projects.db")
    callback_calls = []
    project_tools.set_project_workspace_callback(lambda *args: callback_calls.append(args) or True)
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = json.loads(project_tools.project_create("Anchored", path=str(workspace), task_id="session-1"))

    assert result["success"] is True
    assert result["moved"] is True
    assert "warning" not in result
    assert callback_calls == [("session-1", str(workspace), "Anchored")]


def test_missing_primary_folder_reports_gateway_host_for_create_and_switch(monkeypatch, tmp_path):
    monkeypatch.setattr(projects_db, "projects_db_path", lambda: tmp_path / "projects.db")
    missing = tmp_path / "container-only-repo"
    # Model the gateway callback's host-side isdir guard, not a container filesystem.
    project_tools.set_project_workspace_callback(
        lambda _task_id, path, _name: os.path.isdir(path)
    )

    created = json.loads(project_tools.project_create(
        "Unreachable", path=str(missing), task_id="session-1"
    ))
    switched = json.loads(project_tools.project_switch("Unreachable", task_id="session-1"))

    for result in (created, switched):
        assert result["success"] is True  # The project DB operation did succeed.
        assert result["moved"] is False
        assert "gateway host" in result["warning"]
        assert str(missing) in result["warning"]
