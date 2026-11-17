"""Behavior contracts for the one-off Kanban fixture quarantine packet."""

import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[2]
QUARANTINE_SQL = ROOT / "kanban-fixture-quarantine.sql"
BENCHMARK_SCRIPT = ROOT / "scripts" / "benchmark_kanban_fixture_quarantine.py"


def _build_incident_copy(path: Path) -> str:
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            tenant TEXT,
            created_by TEXT,
            created_at INTEGER NOT NULL,
            claim_lock TEXT,
            claim_expires INTEGER,
            worker_pid INTEGER,
            current_run_id INTEGER
        );
        WITH RECURSIVE n(i) AS (
            VALUES(0) UNION ALL SELECT i + 1 FROM n WHERE i < 26634
        )
        INSERT INTO tasks (id, title, status, tenant, created_at)
        SELECT printf('bench-%05d', i), printf('bench %d', i), 'ready', 'bench', 1787333949
        FROM n;
        WITH RECURSIVE n(i) AS (
            VALUES(0) UNION ALL SELECT i + 1 FROM n WHERE i < 9
        )
        INSERT INTO tasks (id, title, status, created_by, created_at)
        SELECT printf('desktop-%02d', i), printf('Synthetic desktop %d', i), 'ready',
               'desktop-e2e', 1787014905
        FROM n;
        WITH RECURSIVE n(i) AS (
            VALUES(0) UNION ALL SELECT i + 1 FROM n WHERE i < 5
        )
        INSERT INTO tasks (id, title, status, created_by, created_at)
        SELECT printf('preview-%02d', i), printf('Synthetic preview %d', i), 'ready',
               'preview-fixture', 1787025204
        FROM n;
        WITH RECURSIVE n(i) AS (
            VALUES(0) UNION ALL SELECT i + 1 FROM n WHERE i < 7
        )
        INSERT INTO tasks (id, title, status, created_at)
        SELECT printf('long-%02d', i), printf('Long card %d detail hostile', i), 'ready',
               1787030032
        FROM n;
        INSERT INTO tasks (id, title, status, created_by, created_at)
        VALUES ('unrelated', 'Real customer task', 'ready', 'human', 1787000000);
        CREATE TABLE incident_20260824_fixture_quarantine (
            task_id TEXT PRIMARY KEY,
            original_status TEXT NOT NULL,
            claim_lock TEXT,
            claim_expires INTEGER,
            worker_pid INTEGER,
            current_run_id INTEGER,
            quarantined_at INTEGER NOT NULL
        );
        INSERT INTO incident_20260824_fixture_quarantine
        VALUES ('unrelated', 'ready', NULL, NULL, NULL, NULL, 1787000000);
        """
    )
    db.commit()
    db.close()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_dry_run_ignores_stale_persistent_snapshot_ids(tmp_path):
    copied_db = tmp_path / "kanban-copy.db"
    before_hash = _build_incident_copy(copied_db)

    result = subprocess.run(
        ["sqlite3", str(copied_db)],
        input=QUARANTINE_SQL.read_text(),
        text=True,
        capture_output=True,
        check=True,
    )

    assert "dry-run fixture rows|26659" in result.stdout
    assert hashlib.sha256(copied_db.read_bytes()).hexdigest() == before_hash
    with sqlite3.connect(copied_db) as db:
        assert db.execute("SELECT status FROM tasks WHERE id = 'unrelated'").fetchone() == ("ready",)


def test_benchmark_packet_records_reproducible_provenance(tmp_path):
    source = tmp_path / "source.db"
    _build_incident_copy(source)
    copied_db = tmp_path / "copy.db"
    output = tmp_path / "performance.json"

    subprocess.run(
        [
            "python",
            str(BENCHMARK_SCRIPT),
            "--source",
            str(source),
            "--copy",
            str(copied_db),
            "--output",
            str(output),
            "--warmups",
            "1",
            "--runs",
            "2",
        ],
        check=True,
    )

    evidence = json.loads(output.read_text())
    assert evidence["copy_creation_method"] == "sqlite3.Connection.backup"
    assert evidence["warmup_runs"] == 1
    assert evidence["measured_runs"] == 2
    assert evidence["sqlite_version"]
    assert evidence["source_sha256_before"] == evidence["source_sha256_after"]
    assert evidence["copy_sha256_before"] == evidence["copy_sha256_after"]
    assert evidence["classified_before"] == 26659
    assert evidence["classified_active_after"] == 0
    assert all(item["sql"] for item in evidence["queries"].values())
