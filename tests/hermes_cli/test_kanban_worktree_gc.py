from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time

import pytest

from hermes_cli import kanban_worktree_gc as gc


def git(path: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def make_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "tracked.txt").write_text("tracked\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "base")
    wt = repo / ".worktrees" / "t_one"
    git(repo, "worktree", "add", "-b", "wt/t_one", str(wt), "HEAD")
    return repo, wt


def make_db(wt: Path, *, status: str = "done", attachments: int = 1) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
      CREATE TABLE tasks (id TEXT PRIMARY KEY,status TEXT,workspace_kind TEXT,
        workspace_path TEXT,branch_name TEXT,completed_at INTEGER,body TEXT);
      CREATE TABLE task_links (parent_id TEXT,child_id TEXT);
      CREATE TABLE task_runs (task_id TEXT,status TEXT);
      CREATE TABLE task_attachments (task_id TEXT);
    """)
    conn.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?)",
                 ("t_one", status, "worktree", str(wt), "wt/t_one", int(time.time()) - 1000, ""))
    for _ in range(attachments):
        conn.execute("INSERT INTO task_attachments VALUES (?)", ("t_one",))
    return conn


def assessment(tmp_path: Path, **kwargs):
    _repo, wt = make_repo(tmp_path)
    conn = make_db(wt, **kwargs)
    return conn, wt, gc.assess_worktree(conn, "t_one", retention_seconds=0)


@pytest.mark.parametrize("status", ["triage", "todo", "ready", "running", "blocked", "review"])
def test_protected_task_states_are_never_eligible(tmp_path, status):
    _conn, _wt, item = assessment(tmp_path, status=status)
    assert not item.eligible
    assert any("protected" in blocker for blocker in item.blockers)


def test_dirty_untracked_and_ignored_entries_are_never_eligible(tmp_path):
    for name, setup in [
        ("dirty", lambda wt: (wt / "tracked.txt").write_text("changed\n")),
        ("untracked", lambda wt: (wt / "unique.bin").write_bytes(b"unique")),
        ("ignored", lambda wt: ((wt / ".gitignore").write_text("cache/\n"),
                                (wt / "cache").mkdir(), (wt / "cache" / "x").write_text("x"))),
    ]:
        case = tmp_path / name
        case.mkdir()
        _repo, wt = make_repo(case)
        setup(wt)
        conn = make_db(wt)
        item = gc.assess_worktree(conn, "t_one", retention_seconds=0)
        assert not item.eligible, name
        assert any("modified, untracked, or ignored" in b for b in item.blockers)


def test_child_running_worker_and_missing_artifact_gate(tmp_path):
    _repo, wt = make_repo(tmp_path)
    conn = make_db(wt, attachments=0)
    conn.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?)",
                 ("child", "ready", "scratch", None, None, None, ""))
    conn.execute("INSERT INTO task_links VALUES (?,?)", ("t_one", "child"))
    conn.execute("INSERT INTO task_runs VALUES (?,?)", ("t_one", "running"))
    item = gc.assess_worktree(conn, "t_one", retention_seconds=0)
    assert not item.eligible
    assert any("child" in b for b in item.blockers)
    assert any("running worker" in b for b in item.blockers)
    assert any("attachment" in b for b in item.blockers)


def test_path_traversal_or_non_worktree_is_quarantined(tmp_path):
    conn = make_db(tmp_path)
    conn.execute("UPDATE tasks SET workspace_path='../outside'")
    item = gc.assess_worktree(conn, "t_one", retention_seconds=0)
    assert item.lifecycle == "quarantine"
    assert not item.eligible


def test_capacity_guard_simulates_full_filesystem(monkeypatch, tmp_path):
    monkeypatch.setattr(gc.shutil, "disk_usage", lambda _p: os.stat_result((0,)*10) if False else type("U", (), {"free": 0, "total": 100})())
    monkeypatch.setattr(gc.os, "statvfs", lambda _p: type("V", (), {"f_favail": 0, "f_files": 100})())
    snap = gc.capacity_snapshot(tmp_path, min_free_bytes=1, min_free_inodes=1)
    assert snap.blocked
    assert len(snap.reasons) == 2


def test_plan_is_dry_run_and_hash_tampering_fails(tmp_path):
    conn, wt, item = assessment(tmp_path)
    assert item.eligible
    plan = gc.build_plan(conn, retention_seconds=0)
    assert plan["automatic_deletion"] is False
    assert wt.exists()
    plan["retention_seconds"] = 999
    with pytest.raises(ValueError, match="hash mismatch"):
        gc.apply_plan(conn, plan, receipt_path=tmp_path / "receipt.json", retention_seconds=0)
    assert wt.exists()


def test_apply_revalidates_race_before_mutation(tmp_path):
    conn, wt, item = assessment(tmp_path)
    assert item.eligible
    plan = gc.build_plan(conn, retention_seconds=0)
    (wt / "race.txt").write_text("arrived after plan")
    with pytest.raises(RuntimeError, match="changed or became protected"):
        gc.apply_plan(conn, plan, receipt_path=tmp_path / "receipt.json", retention_seconds=0)
    assert wt.exists()


def test_receipt_failure_prevents_git_removal(monkeypatch, tmp_path):
    conn, wt, item = assessment(tmp_path)
    assert item.eligible
    plan = gc.build_plan(conn, retention_seconds=0)
    monkeypatch.setattr(gc, "write_receipt", lambda *_a, **_k: (_ for _ in ()).throw(OSError("ENOSPC")))
    with pytest.raises(OSError, match="ENOSPC"):
        gc.apply_plan(conn, plan, receipt_path=tmp_path / "receipt.json", retention_seconds=0)
    assert wt.exists()


def test_apply_uses_git_preserves_branch_and_writes_manifest(tmp_path):
    repo, wt = make_repo(tmp_path)
    conn = make_db(wt)
    plan = gc.build_plan(conn, retention_seconds=0)
    receipt = tmp_path / "receipt.json"
    assert gc.apply_plan(conn, plan, receipt_path=receipt, retention_seconds=0) == ["t_one"]
    assert not wt.exists()
    assert git(repo, "show-ref", "--verify", "refs/heads/wt/t_one")
    data = json.loads(receipt.read_text())
    assert data["scope_inferred"] == [] and data["irrecoverable"] == []
    assert data["evidence"][0]["entries"]
    assert data["evidence"][0]["global_git"]["refs_sha256"]
    post = json.loads(receipt.with_name(receipt.name + ".post.json").read_text())
    assert post["removed"] == ["t_one"]
    assert post["global_git"]
