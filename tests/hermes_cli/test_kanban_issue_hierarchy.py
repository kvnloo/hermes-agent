from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from hermes_cli import kanban_db as kb


@pytest.fixture
def board(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    with kb.connect() as conn:
        yield conn


def test_existing_rows_migrate_to_root_task_issues(tmp_path):
    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT, assignee TEXT, status TEXT NOT NULL, priority INTEGER DEFAULT 0, created_by TEXT, created_at INTEGER NOT NULL, started_at INTEGER, completed_at INTEGER, workspace_kind TEXT NOT NULL DEFAULT 'scratch', workspace_path TEXT, claim_lock TEXT, claim_expires INTEGER)")
    conn.execute("CREATE TABLE task_events (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT, created_at INTEGER NOT NULL)")
    conn.execute("INSERT INTO tasks (id, title, status, created_at) VALUES ('legacy', 'Legacy', 'todo', 1)")
    conn.commit()
    conn.close()

    with kb.connect(db) as migrated:
        issue = kb.get_task(migrated, "legacy")
        columns = {row["name"] for row in migrated.execute("PRAGMA table_info(tasks)")}

    assert {"kind", "parent_id", "product_id"} <= columns
    assert issue.kind == "task"
    assert issue.parent_id is None
    assert issue.product_id is None


def test_recursive_hierarchy_is_independent_from_dependencies(board):
    product = kb.create_task(board, title="Hermes", kind="product", product_id="product_hermes")
    project = kb.create_task(board, title="Hierarchy", kind="project", hierarchy_parent_id=product, product_id="product_hermes")
    feature = kb.create_task(board, title="Breadcrumbs", kind="feature", hierarchy_parent_id=project, product_id="product_hermes")

    assert kb.get_task(board, feature).status == "ready"
    assert kb.hierarchy_child_ids(board, product) == [project]
    assert [item.id for item in kb.issue_breadcrumbs(board, feature)] == [product, project, feature]

    blocker = kb.create_task(board, title="Design accepted")
    kb.link_tasks(board, blocker, feature)
    assert kb.get_task(board, feature).status == "todo"


def test_reparent_rejects_cycles_and_preserves_original_parent(board):
    root = kb.create_task(board, title="Root", kind="product")
    child = kb.create_task(board, title="Child", kind="project", hierarchy_parent_id=root)
    leaf = kb.create_task(board, title="Leaf", kind="feature", hierarchy_parent_id=child)

    with pytest.raises(ValueError, match="cycle"):
        kb.reparent_issue(board, root, leaf)

    assert kb.get_task(board, root).parent_id is None
    assert kb.reparent_issue(board, leaf, root) is True
    assert kb.get_task(board, leaf).parent_id == root


def test_hierarchy_validation_fails_closed(board):
    with pytest.raises(ValueError, match="kind"):
        kb.create_task(board, title="Bad", kind="epic")
    with pytest.raises(ValueError, match="unknown hierarchy parent"):
        kb.create_task(board, title="Orphan", hierarchy_parent_id="t_missing")
    with pytest.raises(ValueError, match="product_id"):
        kb.create_task(board, title="Ambiguous", product_id="not qualified")


def test_qualified_issue_references_are_unambiguous():
    ref = kb.qualified_issue_ref("hermes-agent", "t_1234abcd")
    assert ref == "hermes-agent:t_1234abcd"
    assert kb.parse_issue_ref(ref) == ("hermes-agent", "t_1234abcd")
    with pytest.raises(ValueError, match="qualified"):
        kb.parse_issue_ref("t_1234abcd")
    with pytest.raises(ValueError, match="board slug"):
        kb.parse_issue_ref("../other:t_1234abcd")


def test_delete_refuses_to_orphan_hierarchy_children(board):
    parent = kb.create_task(board, title="Parent", kind="feature")
    child = kb.create_task(board, title="Child", hierarchy_parent_id=parent)

    with pytest.raises(ValueError, match="hierarchy children"):
        kb.delete_task(board, parent)

    assert kb.get_task(board, parent) is not None
    assert kb.get_task(board, child).parent_id == parent


def test_issue_filters_use_structured_scope_fields(board):
    root = kb.create_task(board, title="Hermes", kind="product", product_id="product_hermes")
    feature = kb.create_task(
        board,
        title="Hierarchy",
        kind="feature",
        hierarchy_parent_id=root,
        product_id="product_hermes",
    )
    kb.create_task(board, title="Other", kind="defect", product_id="product_other")

    assert [issue.id for issue in kb.list_tasks(board, kind="feature")] == [feature]
    assert {issue.id for issue in kb.list_tasks(board, product_id="product_hermes")} == {
        root,
        feature,
    }
    assert [issue.id for issue in kb.list_tasks(board, hierarchy_parent_id=root)] == [feature]
