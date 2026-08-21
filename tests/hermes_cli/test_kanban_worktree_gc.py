from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest

from hermes_cli import kanban_worktree_gc as gc
from hermes_cli import kanban as kanban_cli


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


def file_snapshot(path: Path) -> tuple[int, int, int, int, int, int, str]:
    st = path.lstat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return (st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns,
            st.st_ctime_ns, st.st_nlink, digest)


def git_metadata_snapshot(repo: Path) -> dict[str, tuple[int, int, int, int, int, int, str]]:
    metadata = repo / ".git"
    roots = [metadata / "index", metadata / "refs", metadata / "logs", metadata / "worktrees"]
    paths = []
    for root in roots:
        if root.is_file():
            paths.append(root)
        elif root.is_dir():
            paths.extend(path for path in root.rglob("*") if path.is_file())
    return {str(path.relative_to(metadata)): file_snapshot(path) for path in sorted(paths)}


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
    plan = gc.build_plan(conn, retention_seconds=0)
    assert plan["automatic_deletion"] is False
    assert wt.exists()
    plan["retention_seconds"] = 999
    with pytest.raises(ValueError, match="hash mismatch"):
        gc.apply_plan(conn, plan, receipt_path=tmp_path / "receipt.json", retention_seconds=0)
    assert wt.exists()


def test_normal_clean_fixture_is_explicitly_plan_ineligible(tmp_path):
    _repo, wt = make_repo(tmp_path)
    conn = make_db(wt)

    item = gc.assess_worktree(conn, "t_one", retention_seconds=0)

    assert item.eligible is False
    assert any("plan-only" in blocker for blocker in item.blockers)
    assert item.head == git(wt, "rev-parse", "HEAD")


def test_plan_disables_optional_locks_and_preserves_git_metadata(monkeypatch, tmp_path):
    repo, wt = make_repo(tmp_path)
    conn = make_db(wt)
    monkeypatch.setattr(gc, "_processes_using", lambda _path: gc.ProcessScan())
    original_run = gc.subprocess.run
    observed = []

    def checked_run(*args, **kwargs):
        observed.append(kwargs.get("env", {}).get("GIT_OPTIONAL_LOCKS"))
        return original_run(*args, **kwargs)

    monkeypatch.setattr(gc.subprocess, "run", checked_run)
    os.utime(wt / "tracked.txt", None)
    before = git_metadata_snapshot(repo)

    plan = gc.build_plan(conn, retention_seconds=0)

    assert plan["worktrees"][0]["eligible"] is False
    assert observed and set(observed) == {"0"}
    assert git_metadata_snapshot(repo) == before


def test_disabled_apply_rejects_before_board_or_filesystem_access(monkeypatch, tmp_path):
    repo, wt = make_repo(tmp_path)
    os.utime(wt / "tracked.txt", None)
    before = git_metadata_snapshot(repo)
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    kanban_cli.build_parser(subparsers)
    args = parser.parse_args(["kanban", "gc", "--apply"])

    monkeypatch.setattr(kanban_cli, "_is_delegated_child_cli_mutation",
                        lambda _args: pytest.fail("delegation inspection attempted"))
    monkeypatch.setattr(kanban_cli.kb, "init_db", lambda: pytest.fail("DB initialization attempted"))
    monkeypatch.setattr(kanban_cli.kb, "workspaces_root",
                        lambda: pytest.fail("scratch discovery attempted"))
    monkeypatch.setattr(gc, "build_plan", lambda *_a, **_k: pytest.fail("plan attempted"))

    assert kanban_cli.kanban_command(args) == 2
    assert git_metadata_snapshot(repo) == before


def test_apply_refuses_raced_ignored_unique_file_without_mutation(tmp_path):
    conn, wt, item = assessment(tmp_path)
    plan = gc.build_plan(conn, retention_seconds=0)
    (wt / ".gitignore").write_text("cache/\n")
    (wt / "cache").mkdir()
    unique = wt / "cache" / "unique.bin"
    unique.write_bytes(b"irreplaceable")
    with pytest.raises(RuntimeError, match="automatic worktree removal is disabled"):
        gc.apply_plan(conn, plan, receipt_path=tmp_path / "receipt.json", retention_seconds=0)
    assert unique.read_bytes() == b"irreplaceable"


def test_apply_never_writes_receipts_or_invokes_git(monkeypatch, tmp_path):
    conn, wt, item = assessment(tmp_path)
    plan = gc.build_plan(conn, retention_seconds=0)
    receipt = wt / "ignored" / "receipt.json"
    monkeypatch.setattr(gc, "_git", lambda *_a, **_k: pytest.fail("git mutation attempted"))
    with pytest.raises(RuntimeError, match="manual Captain action"):
        gc.apply_plan(conn, plan, receipt_path=receipt, retention_seconds=0)
    assert wt.exists()
    assert not receipt.exists()


def test_detached_unique_head_is_not_eligible(tmp_path):
    repo, wt = make_repo(tmp_path)
    git(wt, "checkout", "--detach")
    (wt / "tracked.txt").write_text("unique commit\n")
    git(wt, "commit", "-am", "detached unique")
    conn = make_db(wt)
    item = gc.assess_worktree(conn, "t_one", retention_seconds=0)
    assert not item.eligible
    assert any("durable ref" in blocker for blocker in item.blockers)
    assert wt.exists()


@pytest.mark.parametrize("ambiguities", [["pid:12:identity-disappeared"],
                                         ["pid:12:fd-set-changed", "pid:13:starttime-changed"]])
def test_unreadable_or_disappearing_process_state_fails_closed(monkeypatch, tmp_path, ambiguities):
    conn, wt, _item = assessment(tmp_path)
    monkeypatch.setattr(gc, "_processes_using", lambda _path: gc.ProcessScan(ambiguities=ambiguities))
    item = gc.assess_worktree(conn, "t_one", retention_seconds=0)
    assert not item.eligible
    assert any("process scan ambiguous" in blocker for blocker in item.blockers)
    assert not any("-1" in blocker for blocker in item.blockers)


def _fake_proc_process(root: Path, pid: int, *, uid: int, gid: int,
                       cwd: Path, cmdline: bytes = b"sleep\x0010") -> Path:
    entry = root / str(pid)
    (entry / "fd").mkdir(parents=True)
    (entry / "status").write_text(
        f"Name:\ttest\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n"
        f"Gid:\t{gid}\t{gid}\t{gid}\t{gid}\nGroups:\t{gid}\n"
    )
    # field 22 (starttime) is index 19 after the comm/state split.
    (entry / "stat").write_text(f"{pid} (test process) S " + "0 " * 18 + "42 0\n")
    (entry / "cmdline").write_bytes(cmdline)
    (entry / "cgroup").write_text("0::/user.slice\n")
    (entry / "maps").write_text("")
    (entry / "cwd").symlink_to(cwd, target_is_directory=True)
    (entry / "root").symlink_to("/", target_is_directory=True)
    return entry


@pytest.mark.linux_only
def test_real_linux_proc_scanner_detects_same_uid_cwd_and_fd(tmp_path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    held = candidate / "held"
    held.write_text("bytes")
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; f=open('held'); print('ready', flush=True); time.sleep(30)"],
        cwd=candidate,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    assert proc.stdout.readline().strip() == "ready"
    fixture = tmp_path / "proc"
    fixture.mkdir()
    (fixture / str(proc.pid)).symlink_to(Path("/proc") / str(proc.pid), target_is_directory=True)
    try:
        assert gc._processes_using(candidate, proc_root=fixture) == gc.ProcessScan(pids=[proc.pid])
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.mark.linux_only
def test_actual_linux_proc_scan_never_promotes_clean_fixture(tmp_path):
    _repo, wt = make_repo(tmp_path)
    result = gc._processes_using(wt)
    assert isinstance(result, gc.ProcessScan)
    assert all(pid >= 0 for pid in result.pids)
    assert all(reason.startswith("pid:") for reason in result.ambiguities)
    item = gc.assess_worktree(make_db(wt), "t_one", retention_seconds=0)
    assert item.eligible is False
    assert any("plan-only on Linux" in blocker for blocker in item.blockers)


@pytest.mark.linux_only
def test_unreadable_same_uid_proc_fixture_fails_closed(tmp_path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    entry = _fake_proc_process(proc_root, 123, uid=os.geteuid(), gid=os.getegid(), cwd=tmp_path)
    (entry / "maps").chmod(0)
    try:
        result = gc._processes_using(candidate, proc_root=proc_root)
        assert result.pids == []
        assert result.ambiguities == ["pid:123:process-state-unreadable"]
    finally:
        (entry / "maps").chmod(0o600)


@pytest.mark.linux_only
def test_foreign_uid_dac_scope_is_deterministic(tmp_path):
    candidate = tmp_path / "candidate"
    candidate.mkdir(mode=0o700)
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    foreign = os.geteuid() + 10000
    entry = _fake_proc_process(proc_root, 124, uid=foreign, gid=foreign, cwd=tmp_path)
    # DAC-denied, ordinary foreign process is safely out of scope even if an
    # optional descriptor is unreadable.
    (entry / "maps").chmod(0)
    try:
        assert gc._processes_using(candidate, proc_root=proc_root) == gc.ProcessScan()
        (entry / "cmdline").write_bytes(b"hermes-kanban-service\x00")
        result = gc._processes_using(candidate, proc_root=proc_root)
        assert result.ambiguities == ["pid:124:process-state-unreadable"]
    finally:
        (entry / "maps").chmod(0o600)


def _race_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    held = candidate / "held"
    held.write_text("held")
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    entry = _fake_proc_process(proc_root, 321, uid=os.geteuid(), gid=os.getegid(), cwd=candidate)
    (entry / "fd" / "7").symlink_to(held)
    return candidate, proc_root, entry


def _mutate_on_second_identity(monkeypatch, mutation):
    original = gc._proc_identity
    calls = 0

    def raced(entry):
        nonlocal calls
        calls += 1
        if calls == 2:
            mutation(entry)
        return original(entry)

    monkeypatch.setattr(gc, "_proc_identity", raced)


@pytest.mark.linux_only
def test_pid_absent_before_initial_identity_is_not_enumerated(tmp_path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    (proc_root / "320").symlink_to(tmp_path / "already-exited", target_is_directory=True)
    assert gc._processes_using(candidate, proc_root=proc_root) == gc.ProcessScan()


@pytest.mark.linux_only
def test_starttime_mutation_is_explicitly_ambiguous(monkeypatch, tmp_path):
    candidate, proc_root, entry = _race_fixture(tmp_path)

    def mutate(_entry):
        text = (entry / "stat").read_text()
        (entry / "stat").write_text(text.replace("42 0\n", "43 0\n"))

    _mutate_on_second_identity(monkeypatch, mutate)
    assert gc._processes_using(candidate, proc_root=proc_root) == gc.ProcessScan(
        ambiguities=["pid:321:starttime-changed"])


@pytest.mark.linux_only
def test_proc_inode_replacement_is_explicitly_ambiguous(monkeypatch, tmp_path):
    candidate, proc_root, entry = _race_fixture(tmp_path)

    def mutate(_entry):
        entry.rename(proc_root / "old")
        replacement = _fake_proc_process(proc_root, 321, uid=os.geteuid(), gid=os.getegid(), cwd=candidate)
        (replacement / "fd" / "7").symlink_to(candidate / "held")

    _mutate_on_second_identity(monkeypatch, mutate)
    assert gc._processes_using(candidate, proc_root=proc_root) == gc.ProcessScan(
        ambiguities=["pid:321:proc-inode-changed"])


@pytest.mark.linux_only
def test_enumerated_fd_deletion_is_explicitly_ambiguous(monkeypatch, tmp_path):
    candidate, proc_root, entry = _race_fixture(tmp_path)
    _mutate_on_second_identity(monkeypatch, lambda _entry: (entry / "fd" / "7").unlink())
    assert gc._processes_using(candidate, proc_root=proc_root) == gc.ProcessScan(
        ambiguities=["pid:321:fd-set-changed"])


@pytest.mark.linux_only
def test_fd_target_replacement_is_explicitly_ambiguous(monkeypatch, tmp_path):
    candidate, proc_root, entry = _race_fixture(tmp_path)

    def mutate(_entry):
        link = entry / "fd" / "7"
        link.unlink()
        link.symlink_to(tmp_path)

    _mutate_on_second_identity(monkeypatch, mutate)
    assert gc._processes_using(candidate, proc_root=proc_root) == gc.ProcessScan(
        ambiguities=["pid:321:fd-link-changed"])


@pytest.mark.linux_only
@pytest.mark.parametrize("name", ["cwd", "root"])
def test_cwd_or_root_disappearance_is_explicitly_ambiguous(monkeypatch, tmp_path, name):
    candidate, proc_root, entry = _race_fixture(tmp_path)
    _mutate_on_second_identity(monkeypatch, lambda _entry: (entry / name).unlink())
    assert gc._processes_using(candidate, proc_root=proc_root) == gc.ProcessScan(
        ambiguities=["pid:321:process-state-disappeared"])


@pytest.mark.linux_only
def test_process_exit_after_initial_identity_is_explicitly_ambiguous(monkeypatch, tmp_path):
    candidate, proc_root, entry = _race_fixture(tmp_path)
    _mutate_on_second_identity(monkeypatch, lambda _entry: __import__("shutil").rmtree(entry))
    assert gc._processes_using(candidate, proc_root=proc_root) == gc.ProcessScan(
        ambiguities=["pid:321:process-state-disappeared"])


@pytest.mark.parametrize("failure", ["ENOSPC-pre", "ENOSPC-post", "symlink-substitution", "refs-drift", "concurrent-gc"])
def test_all_apply_boundaries_are_non_mutating_manual_fallback(tmp_path, failure):
    conn, wt, item = assessment(tmp_path)
    before_head = git(wt, "rev-parse", "HEAD")
    before_refs = git(wt, "for-each-ref", "--format=%(refname):%(objectname)")
    plan = gc.build_plan(conn, retention_seconds=0)
    with pytest.raises(RuntimeError, match="manual Captain action"):
        gc.apply_plan(conn, plan, receipt_path=tmp_path / failure, retention_seconds=0)
    assert wt.exists()
    assert git(wt, "rev-parse", "HEAD") == before_head
    assert git(wt, "for-each-ref", "--format=%(refname):%(objectname)") == before_refs
