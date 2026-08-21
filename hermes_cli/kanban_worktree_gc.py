"""Fail-closed lifecycle planning for Kanban git worktrees.

This module deliberately does not run in the background.  Worktree removal is
plan-only: a portable validation-to-removal transaction cannot prevent a
concurrent writer from adding unique bytes immediately before Git recursively
removes the checkout.  ``apply_plan`` therefore always fails closed and leaves
manual removal to the Captain.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
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


def _readonly_git_env() -> dict[str, str]:
    """Return an environment which forbids Git's optional housekeeping writes."""
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def _git(path: Path, *args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    # Keep every planning command on this single, explicitly read-only path.
    # In particular, `git status` otherwise refreshes and may replace the index
    # even when its reported content is unchanged.
    command = [
        "git", "-c", "core.fsmonitor=false", "-c", "maintenance.auto=false",
        "-c", "gc.auto=0", "-C", str(path), *args,
    ]
    return subprocess.run(command, capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, check=False, env=_readonly_git_env())


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


def _proc_identity(entry: Path) -> tuple[int, int, frozenset[int], int, int]:
    """Read stable process identity: effective uid/gids, starttime and proc inode."""
    inode = entry.stat().st_ino
    status = (entry / "status").read_text(errors="strict")
    values: dict[str, list[int]] = {}
    for line in status.splitlines():
        name, sep, raw = line.partition(":")
        if sep and name in {"Uid", "Gid", "Groups"}:
            values[name] = [int(part) for part in raw.split()]
    if len(values.get("Uid", [])) != 4 or len(values.get("Gid", [])) != 4:
        raise OSError("incomplete proc credentials")
    stat = (entry / "stat").read_text(errors="strict")
    close = stat.rfind(")")
    fields = stat[close + 2:].split() if close >= 0 else []
    if len(fields) <= 19:
        raise OSError("incomplete proc stat")
    groups = frozenset([values["Gid"][1], *values.get("Groups", [])])
    return values["Uid"][1], values["Gid"][1], groups, int(fields[19]), inode


@dataclass
class ProcessScan:
    pids: list[int] = field(default_factory=list)
    ambiguities: list[str] = field(default_factory=list)


def _proc_link_snapshot(link: Path) -> tuple[int, str]:
    """Capture both link identity and target without following the target."""
    return link.lstat().st_ino, os.readlink(link)


def _dac_can_traverse(path: Path, uid: int, gids: frozenset[int]) -> bool:
    """Conservatively model ordinary DAC traversal to an owned checkout."""
    if uid == 0:
        return True
    current = path
    while True:
        st = current.stat()
        shift = 6 if st.st_uid == uid else 3 if st.st_gid in gids else 0
        if not ((st.st_mode >> shift) & 1):
            return False
        if current.parent == current:
            return True
        current = current.parent


def _associated_process(entry: Path) -> bool:
    """Identify foreign Hermes/Kanban/service processes without trusting names."""
    data = b""
    for name in ("cmdline", "cgroup"):
        try:
            data += (entry / name).read_bytes().lower()
        except (FileNotFoundError, ProcessLookupError):
            raise
        except OSError:
            # Association is an additional scope signal. Credential/access
            # rules below remain fail-closed when these optional files hide.
            pass
    return any(token in data for token in (b"hermes", b"kanban"))


def _inside(candidate: Path, raw: Path) -> bool:
    try:
        raw.resolve(strict=True).relative_to(candidate)
        return True
    except ValueError:
        return False


def _processes_using(path: Path, *, proc_root: Path = Path("/proc")) -> ProcessScan:
    """Return using PIDs and explicit, deterministic scan ambiguities.

    Linux threat model: the candidate must be owned by our effective UID. We
    inspect every same-effective-UID process and every foreign process which is
    privileged, can traverse the candidate under ordinary DAC, or is explicitly
    associated with Hermes/Kanban. Unreadable cwd/root/fd/maps for an in-scope
    process is ambiguous. A foreign process is skipped only when current DAC
    proves it cannot traverse the candidate and it is not service-associated.

    PID directory inode and /proc stat starttime are checked before and after
    inspection to reject PID reuse. Linux capabilities, ACLs, namespaces,
    ptrace policy and already-open descriptors cannot be proven from an
    unprivileged scan; consequently assessment remains plan-ineligible (see
    ``assess_worktree``). Non-Linux hosts are likewise plan-only.
    """
    if sys.platform != "linux" or not proc_root.is_dir():
        return ProcessScan(ambiguities=["proc-root-unavailable"])
    target = path.resolve(strict=True)
    if target.stat().st_uid != os.geteuid():
        return ProcessScan(ambiguities=["candidate-owner-mismatch"])
    hits: set[int] = set()
    ambiguities: set[str] = set()
    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return ProcessScan(ambiguities=["proc-root-enumeration-failed"])
    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            # Absence before this first inode capture means the listed PID was
            # never admitted to this scan generation and is safe to omit.
            initial_inode = entry.stat().st_ino
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError:
            ambiguities.add(f"pid:{pid}:initial-identity-unreadable")
            continue
        try:
            before = _proc_identity(entry)
        except (FileNotFoundError, ProcessLookupError):
            ambiguities.add(f"pid:{pid}:identity-disappeared")
            continue
        except (OSError, ValueError, UnicodeError):
            ambiguities.add(f"pid:{pid}:identity-unreadable")
            continue
        if before[4] != initial_inode:
            ambiguities.add(f"pid:{pid}:proc-inode-changed")
            continue
        uid, _gid, groups, _start, _inode = before
        try:
            in_scope = (uid == os.geteuid() or uid == 0 or
                        _associated_process(entry) or _dac_can_traverse(target, uid, groups))
        except (FileNotFoundError, ProcessLookupError):
            ambiguities.add(f"pid:{pid}:process-state-disappeared")
            continue
        except OSError:
            ambiguities.add(f"pid:{pid}:process-state-unreadable")
            continue
        if not in_scope:
            try:
                excluded_after = _proc_identity(entry)
            except (FileNotFoundError, ProcessLookupError):
                ambiguities.add(f"pid:{pid}:identity-disappeared")
                continue
            except (OSError, ValueError, UnicodeError):
                ambiguities.add(f"pid:{pid}:identity-unreadable")
                continue
            if before[3:] != excluded_after[3:]:
                reason = "starttime-changed" if before[3] != excluded_after[3] else "proc-inode-changed"
                ambiguities.add(f"pid:{pid}:{reason}")
            continue
        try:
            fd_dir = entry / "fd"
            fd_entries = sorted(fd_dir.iterdir(), key=lambda item: item.name)
            links = [entry / "cwd", entry / "root", *fd_entries]
            snapshots = {link: _proc_link_snapshot(link) for link in links}
            used = any(_inside(target, link) for link in links)
            maps = (entry / "maps").read_text(errors="replace")
            used = used or any(
                line.rsplit(None, 1)[-1].startswith(str(target) + os.sep)
                for line in maps.splitlines() if "/" in line
            )
            after = _proc_identity(entry)
            after_fd_entries = sorted(fd_dir.iterdir(), key=lambda item: item.name)
            if [item.name for item in fd_entries] != [item.name for item in after_fd_entries]:
                ambiguities.add(f"pid:{pid}:fd-set-changed")
                continue
            after_snapshots = {link: _proc_link_snapshot(link) for link in links}
        except (FileNotFoundError, ProcessLookupError):
            ambiguities.add(f"pid:{pid}:process-state-disappeared")
            continue
        except (OSError, ValueError, UnicodeError):
            ambiguities.add(f"pid:{pid}:process-state-unreadable")
            continue
        if before[3:] != after[3:]:
            reason = "starttime-changed" if before[3] != after[3] else "proc-inode-changed"
            ambiguities.add(f"pid:{pid}:{reason}")
            continue
        changed_links = [link for link in links if snapshots[link] != after_snapshots[link]]
        if changed_links:
            label = changed_links[0].name
            kind = "fd-link-changed" if changed_links[0].parent == fd_dir else f"{label}-link-changed"
            ambiguities.add(f"pid:{pid}:{kind}")
            continue
        if used:
            hits.add(pid)
    return ProcessScan(pids=sorted(hits), ambiguities=sorted(ambiguities))


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
        durable = _git(
            wp, "for-each-ref", "--contains", out.head,
            "--format=%(refname)", "refs/heads", "refs/tags", "refs/remotes",
        )
        if durable.returncode or not durable.stdout.strip():
            out.blockers.append("HEAD is not reachable from an allowed durable ref")
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
    process_scan = _processes_using(wp)
    if process_scan.pids:
        out.blockers.append("live process uses checkout: " + ",".join(map(str, process_scan.pids[:10])))
    if process_scan.ambiguities:
        out.blockers.append("process scan ambiguous: " + ",".join(process_scan.ambiguities[:10]))
    # Unprivileged /proc inspection cannot exclude privileged/capability/ACL or
    # namespace access, nor an unreadable process retaining an already-open fd.
    # Since apply is disabled, report useful process telemetry but never promote
    # a candidate to deletion eligibility on any platform.
    out.blockers.append(
        "safe process exclusion is unavailable; worktree GC is plan-only on "
        + ("Linux" if sys.platform == "linux" else sys.platform)
    )
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


def apply_plan(conn: sqlite3.Connection, plan: dict[str, Any], *, receipt_path: Path,
               retention_seconds: int = 604800) -> list[str]:
    """Reject automatic removal because portable race-free deletion is impossible."""
    if plan.get("mode") != "plan-only" or plan.get("automatic_deletion") is not False:
        raise ValueError("refusing malformed or deletion-enabled plan")
    expected = dict(plan)
    supplied_hash = expected.pop("plan_sha256", None)
    actual_hash = hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if not supplied_hash or supplied_hash != actual_hash:
        raise ValueError("plan hash mismatch")
    raise RuntimeError(
        "automatic worktree removal is disabled: concurrent unique-byte preservation "
        "cannot be proven portably; manual Captain action is required"
    )
