"""Fail-closed lifecycle planning for Kanban git worktrees.

This module deliberately does not run in the background.  ``apply_plan`` is an
operator-invoked transaction which accepts only a freshly generated plan and
uses git's worktree porcelain; ambiguity always preserves the checkout.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
from typing import Any, Iterable, Optional

TERMINAL_TASK_STATES = frozenset({"done", "archived", "failed", "cancelled"})
PROTECTED_TASK_STATES = frozenset({"triage", "todo", "ready", "running", "blocked", "review"})
LIFECYCLE_STATES = (
    "active", "review-held", "captain-gated", "artifact-extracted",
    "completed-retention", "superseded", "gc-eligible", "quarantine",
)


@dataclass
class WorktreeAssessment:
    task_id: str
    path: str
    lifecycle: str = "quarantine"
    eligible: bool = False
    blockers: list[str] = field(default_factory=list)
    task_status: str = "unknown"
    head: Optional[str] = None
    branch: Optional[str] = None
    bytes: int = 0
    inodes: int = 0
    top_consumers: list[dict[str, Any]] = field(default_factory=list)
    artifact_count: int = 0


@dataclass
class CapacitySnapshot:
    path: str
    free_bytes: int
    free_inodes: int
    total_bytes: int
    total_inodes: int
    blocked: bool
    reasons: list[str]


def capacity_snapshot(path: Path, *, min_free_bytes: int, min_free_inodes: int) -> CapacitySnapshot:
    """Measure the filesystem containing *path*; configured zero disables a limit."""
    usage = shutil.disk_usage(path)
    vfs = os.statvfs(path)
    free_inodes = int(vfs.f_favail)
    total_inodes = int(vfs.f_files)
    reasons = []
    if min_free_bytes > 0 and usage.free < min_free_bytes:
        reasons.append(f"free bytes {usage.free} below required {min_free_bytes}")
    if min_free_inodes > 0 and free_inodes < min_free_inodes:
        reasons.append(f"free inodes {free_inodes} below required {min_free_inodes}")
    return CapacitySnapshot(str(path), usage.free, free_inodes, usage.total, total_inodes, bool(reasons), reasons)


def _git(path: Path, *args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(path), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, check=False)


def _tree_usage(root: Path) -> tuple[int, int, list[dict[str, Any]]]:
    total = 0
    inodes = 0
    buckets: dict[str, list[int]] = {}
    for base, dirs, files in os.walk(root, followlinks=False):
        rel = Path(base).relative_to(root)
        bucket = rel.parts[0] if rel.parts else "(checkout-root)"
        for name in [*dirs, *files]:
            p = Path(base) / name
            inodes += 1
            try:
                size = p.lstat().st_size
            except OSError:
                continue
            total += size
            slot = buckets.setdefault(bucket, [0, 0])
            slot[0] += size
            slot[1] += 1
    top = [
        {"name": name, "bytes": values[0], "inodes": values[1]}
        for name, values in sorted(buckets.items(), key=lambda item: item[1][0], reverse=True)[:10]
    ]
    return total, inodes, top


def _processes_using(path: Path) -> list[int]:
    """Return PIDs whose cwd or open fd resolves inside path; unreadable /proc is ambiguity."""
    target = path.resolve(strict=False)
    hits: set[int] = set()
    proc = Path("/proc")
    if not proc.is_dir():
        return [-1]  # unsupported host: fail closed
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        links = [entry / "cwd"]
        fd = entry / "fd"
        try:
            links.extend(fd.iterdir())
        except (OSError, PermissionError):
            pass
        for link in links:
            try:
                resolved = link.resolve(strict=True)
                resolved.relative_to(target)
            except (OSError, ValueError, PermissionError):
                continue
            hits.add(int(entry.name))
            break
    return sorted(hits)


def _artifact_count(conn: sqlite3.Connection, task_id: str) -> int:
    try:
        row = conn.execute("SELECT COUNT(*) FROM task_attachments WHERE task_id = ?", (task_id,)).fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return 0


def assess_worktree(conn: sqlite3.Connection, task_id: str, *, retention_seconds: int = 604800,
                    now: Optional[int] = None) -> WorktreeAssessment:
    now = int(time.time()) if now is None else int(now)
    row = conn.execute(
        "SELECT id,status,workspace_kind,workspace_path,branch_name,completed_at,body FROM tasks WHERE id=?",
        (task_id,),
    ).fetchone()
    path = str(row["workspace_path"] if row else "")
    out = WorktreeAssessment(task_id=task_id, path=path)
    if not row or row["workspace_kind"] != "worktree" or not path:
        out.blockers.append("not a recorded worktree task")
        return out
    out.task_status = str(row["status"])
    wp = Path(path).expanduser()
    if not wp.is_absolute() or not wp.is_dir():
        out.blockers.append("worktree path missing or non-absolute")
        return out
    common = _git(wp, "rev-parse", "--git-common-dir")
    top = _git(wp, "rev-parse", "--show-toplevel")
    if common.returncode or top.returncode or Path(top.stdout.strip()).resolve() != wp.resolve():
        out.blockers.append("path is not the exact git checkout root")
        return out
    out.bytes, out.inodes, out.top_consumers = _tree_usage(wp)
    out.artifact_count = _artifact_count(conn, task_id)
    head = _git(wp, "rev-parse", "HEAD")
    branch = _git(wp, "branch", "--show-current")
    if head.returncode or branch.returncode:
        out.blockers.append("cannot resolve HEAD and branch")
    else:
        out.head, out.branch = head.stdout.strip(), branch.stdout.strip() or None
    status = _git(wp, "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching")
    if status.returncode or status.stdout:
        out.blockers.append("checkout has modified, untracked, or ignored entries")
    if out.task_status in PROTECTED_TASK_STATES:
        out.blockers.append(f"task state {out.task_status} is protected")
    active_children = conn.execute(
        "SELECT 1 FROM task_links l JOIN tasks c ON c.id=l.child_id "
        "WHERE l.parent_id=? AND c.status NOT IN ('done','archived','failed','cancelled') LIMIT 1",
        (task_id,),
    ).fetchone()
    if active_children:
        out.blockers.append("nonterminal child depends on task")
    if conn.execute("SELECT 1 FROM task_runs WHERE task_id=? AND status='running' LIMIT 1", (task_id,)).fetchone():
        out.blockers.append("task has a running worker")
    pids = _processes_using(wp)
    if pids:
        out.blockers.append("live process uses checkout: " + ",".join(map(str, pids[:10])))
    completed = row["completed_at"]
    if not completed or now - int(completed) < max(0, retention_seconds):
        out.blockers.append("completion retention has not elapsed")
    # Completion extracts declared artifacts before changing task state.  A task
    # with no attachments is ambiguous: its checkout may contain the sole copy
    # of an undeclared deliverable even when git-clean.
    if out.artifact_count == 0:
        out.blockers.append("no durable task attachment proves artifact extraction")
    body = (row["body"] or "").lower()
    if "captain-gated" in body or "captain approve" in body:
        out.blockers.append("task is Captain-gated")
    out.eligible = not out.blockers
    if out.eligible:
        out.lifecycle = "gc-eligible"
    elif out.task_status == "running":
        out.lifecycle = "active"
    elif out.task_status == "review":
        out.lifecycle = "review-held"
    elif any("Captain" in b for b in out.blockers):
        out.lifecycle = "captain-gated"
    elif out.task_status in TERMINAL_TASK_STATES and completed:
        out.lifecycle = "completed-retention"
    else:
        out.lifecycle = "quarantine"
    return out


def build_plan(conn: sqlite3.Connection, *, retention_seconds: int = 604800,
               task_ids: Optional[Iterable[str]] = None) -> dict[str, Any]:
    if task_ids is None:
        task_ids = [r[0] for r in conn.execute("SELECT id FROM tasks WHERE workspace_kind='worktree' ORDER BY id")]
    assessments = [assess_worktree(conn, tid, retention_seconds=retention_seconds) for tid in task_ids]
    payload: dict[str, Any] = {
        "schema": 1, "mode": "plan-only", "automatic_deletion": False,
        "created_at": int(time.time()), "retention_seconds": retention_seconds,
        "proven": ["git status includes ignored and all untracked entries", "task/child/run/process gates evaluated"],
        "scope_inferred": [], "irrecoverable": [],
        "worktrees": [asdict(item) for item in assessments],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["plan_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def write_receipt(path: Path, payload: dict[str, Any]) -> None:
    """Atomically persist and fsync a receipt before any mutation."""
    path = path.expanduser().resolve(strict=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        dirfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _content_manifest(root: Path) -> list[dict[str, Any]]:
    """Hash every entry before removal, including mode, type and xattr names."""
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda p: os.fsencode(str(p.relative_to(root)))):
        info = path.lstat()
        kind = "symlink" if stat.S_ISLNK(info.st_mode) else "dir" if stat.S_ISDIR(info.st_mode) else "file"
        item: dict[str, Any] = {"path": path.relative_to(root).as_posix(), "type": kind,
                                "mode": stat.S_IMODE(info.st_mode), "size": info.st_size}
        try:
            item["xattrs"] = sorted(os.listxattr(path, follow_symlinks=False))
        except OSError as exc:
            item["xattrs_error"] = type(exc).__name__
        if kind == "file":
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            item["sha256"] = digest.hexdigest()
        elif kind == "symlink":
            item["target"] = os.readlink(path)
        entries.append(item)
    return entries


def _refs_snapshot(repo_root: Path) -> dict[str, Any]:
    refs = _git(repo_root, "for-each-ref", "--format=%(refname)%00%(objectname)")
    reflogs = _git(repo_root, "reflog", "show", "--all", "--format=%gD%x00%H")
    if refs.returncode or reflogs.returncode:
        raise RuntimeError("cannot snapshot global refs and reflogs")
    return {"refs": refs.stdout.splitlines(), "reflogs": reflogs.stdout.splitlines(),
            "refs_sha256": hashlib.sha256(refs.stdout.encode()).hexdigest(),
            "reflogs_sha256": hashlib.sha256(reflogs.stdout.encode()).hexdigest()}


def apply_plan(conn: sqlite3.Connection, plan: dict[str, Any], *, receipt_path: Path,
               retention_seconds: int = 604800) -> list[str]:
    """Apply a plan after revalidation. Branches/refs/reflogs are never deleted."""
    if plan.get("mode") != "plan-only" or plan.get("automatic_deletion") is not False:
        raise ValueError("refusing malformed or deletion-enabled plan")
    expected = dict(plan)
    supplied_hash = expected.pop("plan_sha256", None)
    actual_hash = hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if not supplied_hash or supplied_hash != actual_hash:
        raise ValueError("plan hash mismatch")
    selected = [w for w in plan.get("worktrees", []) if w.get("eligible")]
    fresh = {w.task_id: w for w in (assess_worktree(conn, item["task_id"], retention_seconds=retention_seconds) for item in selected)}
    for item in selected:
        current = fresh[item["task_id"]]
        if not current.eligible or current.head != item.get("head") or current.path != item.get("path"):
            raise RuntimeError(f"worktree changed or became protected: {item['task_id']}")
    evidence: list[dict[str, Any]] = []
    for item in selected:
        wp = Path(item["path"])
        common_result = _git(wp, "rev-parse", "--git-common-dir")
        if common_result.returncode:
            raise RuntimeError(f"cannot resolve common dir: {item['task_id']}")
        common = Path(common_result.stdout.strip())
        if not common.is_absolute():
            common = (wp / common).resolve()
        evidence.append({"task_id": item["task_id"], "entries": _content_manifest(wp),
                         "global_git": _refs_snapshot(common.parent)})
    receipt = {"schema": 1, "operation": "kanban-worktree-gc", "plan": plan,
               "pre_mutation": [asdict(fresh[item["task_id"]]) for item in selected],
               "evidence": evidence,
               "proven": ["per-entry content/type/hash/mode/xattr manifest captured",
                           "global refs and reflogs snapshot captured",
                           "receipt fsynced before mutation"],
               "scope_inferred": [], "irrecoverable": []}
    write_receipt(receipt_path, receipt)
    removed: list[str] = []
    for item in selected:
        wp = Path(item["path"])
        repo = _git(wp, "rev-parse", "--git-common-dir")
        if repo.returncode:
            raise RuntimeError(f"cannot resolve common dir: {item['task_id']}")
        common = Path(repo.stdout.strip())
        if not common.is_absolute():
            common = (wp / common).resolve()
        root = common.parent
        result = _git(root, "worktree", "remove", str(wp), timeout=60)
        if result.returncode:
            raise RuntimeError(f"git worktree remove failed for {item['task_id']}: {result.stderr.strip()}")
        removed.append(item["task_id"])
    # Prunes only stale administrative records; never branches/refs/reflogs.
    roots = {Path(item["path"]).parent.parent for item in selected}
    for root in roots:
        _git(root, "worktree", "prune")
    # The pre-mutation receipt is immutable. A sibling post receipt proves the
    # operation did not rewrite refs/reflogs; failure is surfaced rather than
    # silently claiming complete evidence.
    post = {"schema": 1, "operation": "kanban-worktree-gc-post",
            "pre_receipt": str(receipt_path), "removed": removed,
            "global_git": {str(root): _refs_snapshot(root) for root in roots},
            "proven": ["post-removal refs and reflogs captured"],
            "scope_inferred": [], "irrecoverable": []}
    post_path = receipt_path.with_name(receipt_path.name + ".post.json")
    write_receipt(post_path, post)
    return removed
