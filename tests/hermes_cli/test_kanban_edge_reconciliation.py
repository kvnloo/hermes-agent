import hashlib
import json
import sqlite3

from scripts.kanban_edge_reconciliation import generate


def _fixture(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY, status TEXT, assignee TEXT, tenant TEXT,
            created_at INTEGER, completed_at INTEGER, body TEXT, result TEXT
        );
        CREATE TABLE task_links (parent_id TEXT, child_id TEXT, PRIMARY KEY(parent_id, child_id));
        CREATE TABLE task_comments (task_id TEXT, body TEXT);
        INSERT INTO tasks VALUES ('present-parent','done','worker',NULL,1,2,'TOP SECRET','hidden');
        INSERT INTO tasks VALUES ('present-child','todo','reviewer','tenant-a',3,NULL,'PRIVATE','hidden');
        INSERT INTO task_links VALUES ('missing-parent','present-child');
        INSERT INTO task_links VALUES ('present-parent','missing-child');
        INSERT INTO task_links VALUES ('missing-both-a','missing-both-b');
        INSERT INTO task_comments VALUES ('present-parent','DO NOT EXPORT');
        """
    )
    conn.commit()
    conn.close()


def test_generate_is_read_only_redacted_and_conservative(tmp_path):
    db = tmp_path / "kanban.db"
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    seals_path = tmp_path / "seals.json"
    _fixture(db)
    before = hashlib.sha256(db.read_bytes()).hexdigest()

    report = generate(str(db), json_path, markdown_path, seals_path)

    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    assert report["counts"] == {
        "tasks": 2,
        "links": 3,
        "dangling": 3,
        "missing_parent": 1,
        "missing_child": 1,
        "both_missing": 1,
    }
    assert report["logical_sentinel"]["equal"] is True
    assert report["logical_sentinel"]["external_equal"] is True
    assert {edge["structural_class"] for edge in report["edges"]} == {
        "missing_parent", "missing_child", "both_missing"
    }
    assert all(edge["proposal"] == {
        "action": "retain",
        "rationale": "Endpoint absence is proven in this snapshot, but origin and intended dependency are not; retain pending owner review.",
        "confidence": "low",
        "executed": False,
    } for edge in report["edges"])
    rendered = json_path.read_text() + markdown_path.read_text()
    assert "TOP SECRET" not in rendered
    assert "DO NOT EXPORT" not in rendered
    seals = json.loads(seals_path.read_text())
    assert seals["files"][json_path.name] == hashlib.sha256(json_path.read_bytes()).hexdigest()
    assert seals["files"][markdown_path.name] == hashlib.sha256(markdown_path.read_bytes()).hexdigest()


def test_generate_rejects_ambient_relative_db(tmp_path):
    db = tmp_path / "kanban.db"
    _fixture(db)
    try:
        generate("kanban.db", tmp_path / "r.json", tmp_path / "r.md", tmp_path / "s.json")
    except ValueError as error:
        assert "explicit absolute path" in str(error)
    else:
        raise AssertionError("relative DB path was accepted")
