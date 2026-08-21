from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hermes_cli import kanban_db as kb


def _router():
    plugin = Path(__file__).resolve().parents[2] / "plugins/kanban/dashboard/plugin_api.py"
    spec = importlib.util.spec_from_file_location("roadmap_plugin_api_test", plugin)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.router


@pytest.fixture
def roadmap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    app = FastAPI()
    app.include_router(_router(), prefix="/api/plugins/kanban")
    return TestClient(app), home


def _write_catalog(scopes: list[dict]) -> None:
    path = kb.boards_root() / "roadmap.v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "scopes": scopes}), encoding="utf-8")


def test_absent_catalog_preserves_board_capability(roadmap):
    client, _ = roadmap
    response = client.get("/api/plugins/kanban/roadmap")
    assert response.status_code == 200
    assert response.json()["capability"] is False
    assert response.json()["state"] == "absent"
    assert response.json()["scopes"] == []


def test_projection_is_board_scoped_and_exposes_raw_provenance(roadmap):
    client, _ = roadmap
    parent = client.post("/api/plugins/kanban/tasks", json={"title": "Plan"}).json()["task"]
    child = client.post(
        "/api/plugins/kanban/tasks",
        json={"title": "Build", "parents": [parent["id"]]},
    ).json()["task"]
    _write_catalog([
        {"id": "company-public", "type": "company", "name": "Public Example"},
        {
            "id": "project-roadmap",
            "type": "project",
            "name": "Roadmap",
            "parent_id": "company-public",
            "board_slugs": ["default"],
        },
        {
            "id": "private-sibling",
            "type": "project",
            "name": "Hidden sibling",
            "parent_id": "company-public",
            "board_slugs": ["other"],
        },
    ])

    data = client.get("/api/plugins/kanban/roadmap").json()
    assert data["state"] == "ready"
    assert [scope["id"] for scope in data["scopes"]] == ["company-public", "project-roadmap"]
    rollup = data["scopes"][-1]["rollup"]
    assert rollup["task_count"] == 2
    assert rollup["status_counts"] == {"ready": 1, "todo": 1}
    assert rollup["critical_path"] == {"state": "ok", "task_ids": [parent["id"], child["id"]]}
    assert rollup["volume_score"] == 0
    assert data["source_revision"]
    assert data["freshness"]["latest_event_id"] > 0


def test_invalid_hierarchy_fails_closed(roadmap):
    client, _ = roadmap
    _write_catalog([
        {
            "id": "project",
            "type": "project",
            "name": "Project",
            "parent_id": "board",
            "board_slugs": ["default"],
        },
        {"id": "board", "type": "board", "name": "Board", "parent_id": "project"},
    ])

    data = client.get("/api/plugins/kanban/roadmap").json()
    assert data["capability"] is True
    assert data["state"] == "invalid"
    assert data["scopes"] == []
    assert any("invalid parent order" in warning for warning in data["warnings"])
    assert any("cycle" in warning for warning in data["warnings"])
