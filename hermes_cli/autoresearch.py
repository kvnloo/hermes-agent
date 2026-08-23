"""Hermes-native ``/autoresearch`` — autonomous benchmark-optimization loop.

Port of the MIT-licensed OMP autoresearch extension
(``/workspace/omp/packages/coding-agent/src/autoresearch``, Copyright
2025 Mario Zechner; 2025-2026 Can Bölück, MIT license). Substantially
copied portions (state math, storage schema, git branch handling, metric
line parsing) retain their behavioral contracts; this file is the
attribution notice for the port.

Deliberate Hermes adaptations:
  * No dynamic tool-schema mutation. OMP toggles four experiment tools in
    and out of the live toolset; that violates Hermes prompt-cache
    invariants. Here the slash command injects a *static* instruction
    message and the agent drives experiments through the existing
    ``terminal``/file tools. The system prompt and tool schemas are never
    rebuilt mid-conversation.
  * State is profile-safe: SQLite WAL DB under
    ``$HERMES_HOME/autoresearch/<project-key>.db`` (OMP uses ~/.omp).
  * Fail-closed security: KEEP with scope/off-limits deviations is
    refused without an explicit justification; discard resets only on a
    dedicated ``autoresearch/*`` branch; a committed fixed harness
    (``./autoresearch.sh``) is required before iteration.

CLI surface (rung 2 of the footprint ladder — CLI command, no new model
tools): ``hermes autoresearch {status,on,off,clear,log,runs}`` plus the
shared ``/autoresearch`` slash string parser.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from hermes_constants import get_hermes_home

# ---------------------------------------------------------------------------
# Constants (ported from helpers.ts / git.ts / init-experiment.ts)
# ---------------------------------------------------------------------------

AUTORESEARCH_BRANCH_PREFIX = "autoresearch/"
BRANCH_NAME_MAX_LENGTH = 48
HARNESS_FILENAME = "autoresearch.sh"
DEFAULT_HARNESS_COMMAND = f"bash {HARNESS_FILENAME}"
DEFAULT_RUN_TIMEOUT_SECONDS = 600
SCHEMA_VERSION = 1

METRIC_LINE_PREFIX = "METRIC"
ASI_LINE_PREFIX = "ASI"

# Prototype-pollution keys are denied when parsing untrusted harness output
# (ported from DENIED_KEY_NAMES in helpers.ts).
DENIED_KEY_NAMES = {"__proto__", "constructor", "prototype"}

STATUS_KEEP = "keep"
STATUS_DISCARD = "discard"
STATUS_CRASH = "crash"
STATUS_CHECKS_FAILED = "checks_failed"
EXPERIMENT_STATUSES = (STATUS_KEEP, STATUS_DISCARD, STATUS_CRASH, STATUS_CHECKS_FAILED)

# Canary model pin — fail closed on mismatch. The autoresearch worker must
# record exactly this provider/model on every run.
CANARY_PROVIDER = "nous"
CANARY_MODEL = "stealth/ox-alpha"


# ---------------------------------------------------------------------------
# Metric / ASI line parsing (ported from parseMetricLines / parseAsiLines)
# ---------------------------------------------------------------------------

_METRIC_RE = re.compile(rf"^{METRIC_LINE_PREFIX}\s+([\w.\u00b5-]+)=(\S+)\s*$", re.M)
_ASI_RE = re.compile(rf"^{ASI_LINE_PREFIX}\s+([\w.-]+)=(.+)\s*$", re.M)


def parse_metric_lines(output: str) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for match in _METRIC_RE.finditer(output):
        name = match.group(1)
        if name in DENIED_KEY_NAMES:
            continue
        try:
            value = float(match.group(2))
        except ValueError:
            continue
        if value == value and value not in (float("inf"), float("-inf")):
            metrics[name] = value
    return metrics


def _parse_asi_value(raw: str) -> Any:
    value = raw.strip()
    if value == "true":
        return True
    if value == "false":
        return False
    if value == "null":
        return None
    if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        try:
            num = float(value)
        except ValueError:
            return value
        if num.is_integer() and "." not in value:
            return int(num)
        return num
    if value[:1] in ("{", "[", '"'):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def parse_asi_lines(output: str) -> Optional[dict[str, Any]]:
    asi: dict[str, Any] = {}
    for match in _ASI_RE.finditer(output):
        key = match.group(1)
        if key in DENIED_KEY_NAMES:
            continue
        asi[key] = _parse_asi_value(match.group(2))
    return asi or None


def sanitize_metrics(value: Optional[dict]) -> dict[str, float]:
    """Keep only finite numeric entries under non-denied keys."""
    out: dict[str, float] = {}
    if not value:
        return out
    for key, entry in value.items():
        if key in DENIED_KEY_NAMES:
            continue
        if isinstance(entry, bool):
            continue
        if isinstance(entry, (int, float)):
            num = float(entry)
            if num == num and num not in (float("inf"), float("-inf")):
                out[key] = num
    return out


def sanitize_asi(value: Optional[dict]) -> Optional[dict]:
    """Recursively drop denied keys from free-form ASI metadata."""
    if not value:
        return None
    result: dict[str, Any] = {}
    for key, entry in value.items():
        if key in DENIED_KEY_NAMES:
            continue
        cleaned = _sanitize_asi_value(entry)
        if cleaned is not None:
            result[key] = cleaned
    return result or None


def _sanitize_asi_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, list):
        items = [_sanitize_asi_value(item) for item in value]
        return [item for item in items if item is not None]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, entry in value.items():
            if key in DENIED_KEY_NAMES:
                continue
            cleaned = _sanitize_asi_value(entry)
            if cleaned is not None:
                out[key] = cleaned
        return out
    return None


def is_better(current: float, best: float, direction: str) -> bool:
    return current < best if direction == "lower" else current > best


def path_matches_spec(path_value: str, spec_value: str) -> bool:
    def normalize(value: str) -> str:
        trimmed = value.strip().replace("\\", "/")
        collapsed = re.sub(r"^\./+", "", trimmed).rstrip("/")
        return collapsed or "."

    normalized_path = normalize(path_value)
    normalized_spec = normalize(spec_value)
    if normalized_spec == ".":
        return True
    return normalized_path == normalized_spec or normalized_path.startswith(f"{normalized_spec}/")


def slugify_goal(goal: Optional[str]) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", (goal or "").lower()).strip("-")
    trimmed = normalized[:BRANCH_NAME_MAX_LENGTH].rstrip("-")
    return trimmed or "session"


def date_stamp() -> str:
    return time.strftime("%Y%m%d")


# ---------------------------------------------------------------------------
# Git helpers (subprocess shelling out — ported from git.ts behavior)
# ---------------------------------------------------------------------------


class AutoresearchGitError(RuntimeError):
    pass


def _run_git(cwd: str, *args: str, check: bool = True) -> "subprocess.CompletedProcess[str]":
    proc = subprocess.run(
        ["git", "-C", cwd, *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if check and proc.returncode != 0:
        raise AutoresearchGitError(
            f"git {' '.join(args)} failed (exit {proc.returncode}): {proc.stderr.strip()}"
        )
    return proc


def git_repo_root(cwd: str) -> Optional[str]:
    proc = _run_git(cwd, "rev-parse", "--show-toplevel", check=False)
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def git_current_branch(cwd: str) -> Optional[str]:
    proc = _run_git(cwd, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    if proc.returncode != 0:
        return None
    branch = proc.stdout.strip()
    return branch or None


def git_head_sha(cwd: str) -> Optional[str]:
    proc = _run_git(cwd, "rev-parse", "HEAD", check=False)
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def is_pure_jj_repo(cwd: str) -> bool:
    """True when the workspace is pure Jujutsu (``.jj/`` without colocated .git)."""
    if not (Path(cwd) / ".jj").is_dir():
        return False
    return not (Path(cwd) / ".git").exists()


def git_dirty_paths(cwd: str) -> list[dict[str, Any]]:
    """Parse ``git status --porcelain=v1 -z -uall`` into [{path, untracked}].

    Paths under the autoresearch state directory (``$HERMES_HOME``) are
    excluded — our own SQLite WAL traffic must never read as user dirt.
    """
    proc = _run_git(cwd, "status", "--porcelain=v1", "-z", "-uall", check=False)
    if proc.returncode != 0:
        raise AutoresearchGitError("unable to inspect git status")
    output = proc.stdout
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    index = 0
    while index + 3 <= len(output):
        status_token = output[index : index + 3]
        index += 3
        path_end = output.find("\0", index)
        if path_end < 0:
            break
        first_path = output[index:path_end]
        index = path_end + 1
        untracked = status_token.strip().startswith("??")
        rename_or_copy = status_token.strip()[:1] in ("R", "C")
        paths = [first_path]
        if rename_or_copy:
            second_end = output.find("\0", index)
            if second_end < 0:
                break
            paths.append(output[index:second_end])
            index = second_end + 1
        for raw in paths:
            normalized = raw.strip().strip('"')
            if not normalized or normalized in seen:
                continue
            if _is_state_path(cwd, normalized):
                continue
            seen.add(normalized)
            entries.append({"path": normalized, "untracked": untracked})
    return entries


def _is_state_path(cwd: str, rel_path: str) -> bool:
    try:
        hermes_home = get_hermes_home().resolve()
    except Exception:
        return False
    candidate = (Path(cwd) / rel_path).resolve()
    try:
        candidate.relative_to(hermes_home)
        return True
    except ValueError:
        return False


def ensure_autoresearch_branch(
    cwd: str, goal: Optional[str]
) -> tuple[bool, Optional[str], Optional[str], bool]:
    """Ensure the worktree sits on an ``autoresearch/*`` branch.

    Returns ``(ok, branch_name, error_or_warning, created)``. Refuses to
    continue unisolated on pure-jj repos, dirty non-autoresearch trees, or
    git failures — fail closed rather than running unisolated.
    """
    if is_pure_jj_repo(cwd):
        return (
            False,
            None,
            "Autoresearch needs a Git checkout for branch isolation and baseline "
            "commits, but this workspace is pure Jujutsu (`.jj/` without a "
            "colocated `.git/`). Run `jj git init --colocate` before starting.",
            False,
        )

    repo_root = git_repo_root(cwd)
    if not repo_root:
        return (
            False,
            None,
            "Not inside a git repository — autoresearch refuses to run without "
            "branch isolation.",
            False,
        )

    try:
        dirty = git_dirty_paths(repo_root)
    except AutoresearchGitError as exc:
        return False, None, str(exc), False

    current = git_current_branch(repo_root)
    if current and current.startswith(AUTORESEARCH_BRANCH_PREFIX):
        return True, current, None, False

    if dirty:
        preview = ", ".join(e["path"] for e in dirty[:5])
        more = f" (+{len(dirty) - 5} more)" if len(dirty) > 5 else ""
        return (
            False,
            None,
            f"Worktree is dirty ({preview}{more}). Commit or stash these changes "
            "before starting autoresearch — a fresh autoresearch/* branch needs a "
            "clean baseline.",
            False,
        )

    base = f"{AUTORESEARCH_BRANCH_PREFIX}{slugify_goal(goal)}-{date_stamp()}"
    candidate = base
    suffix = 2
    while (
        _run_git(
            repo_root, "show-ref", "--verify", "--quiet", f"refs/heads/{candidate}", check=False
        ).returncode
        == 0
    ):
        candidate = f"{base}-{suffix}"
        suffix += 1

    proc = _run_git(repo_root, "checkout", "-b", candidate, check=False)
    if proc.returncode != 0:
        return False, None, f"Failed to create autoresearch branch {candidate}: {proc.stderr.strip()}", False
    return True, candidate, None, True


# ---------------------------------------------------------------------------
# Storage — profile-safe SQLite under $HERMES_HOME/autoresearch/
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
	id INTEGER PRIMARY KEY,
	name TEXT NOT NULL,
	goal TEXT,
	primary_metric TEXT NOT NULL,
	metric_unit TEXT NOT NULL DEFAULT '',
	direction TEXT NOT NULL DEFAULT 'lower',
	preferred_command TEXT,
	branch TEXT,
	baseline_commit TEXT,
	current_segment INTEGER NOT NULL DEFAULT 0,
	max_iterations INTEGER,
	scope_paths_json TEXT NOT NULL DEFAULT '[]',
	off_limits_json TEXT NOT NULL DEFAULT '[]',
	constraints_json TEXT NOT NULL DEFAULT '[]',
	secondary_metrics_json TEXT NOT NULL DEFAULT '[]',
	notes TEXT NOT NULL DEFAULT '',
	provider TEXT NOT NULL DEFAULT '',
	model TEXT NOT NULL DEFAULT '',
	created_at INTEGER NOT NULL,
	closed_at INTEGER
);
CREATE TABLE IF NOT EXISTS runs (
	id INTEGER PRIMARY KEY,
	session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
	segment INTEGER NOT NULL,
	command TEXT NOT NULL,
	started_at INTEGER NOT NULL,
	completed_at INTEGER,
	duration_ms INTEGER,
	exit_code INTEGER,
	timed_out INTEGER NOT NULL DEFAULT 0,
	parsed_primary REAL,
	parsed_metrics_json TEXT,
	parsed_asi_json TEXT,
	pre_run_dirty_paths_json TEXT NOT NULL DEFAULT '[]',
	log_path TEXT NOT NULL,
	status TEXT,
	description TEXT,
	metric REAL,
	metrics_json TEXT,
	asi_json TEXT,
	commit_hash TEXT,
	confidence REAL,
	modified_paths_json TEXT,
	scope_deviations_json TEXT,
	justification TEXT,
	flagged INTEGER NOT NULL DEFAULT 0,
	flagged_reason TEXT,
	logged_at INTEGER,
	abandoned_at INTEGER
);
CREATE INDEX IF NOT EXISTS runs_session_segment_idx ON runs(session_id, segment);
CREATE INDEX IF NOT EXISTS runs_pending_idx ON runs(session_id, status, abandoned_at);
"""


def encode_project_key(repo_root: str) -> str:
    return f"--{repo_root.replace('/', '-').replace(':', '-').lstrip('-')}--"


def autoresearch_db_path(cwd: str) -> Path:
    repo_root = git_repo_root(cwd) or cwd
    return get_hermes_home() / "autoresearch" / f"{encode_project_key(repo_root)}.db"


class AutoresearchStorage:
    def __init__(self, db_path: Path, project_dir: Path):
        self.db_path = db_path
        self.project_dir = project_dir
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(db_path), timeout=5.0)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA busy_timeout=5000")
        self._db.executescript(SCHEMA_SQL)
        version = self._db.execute("PRAGMA user_version").fetchone()[0]
        if version < SCHEMA_VERSION:
            self._db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    # -- sessions -----------------------------------------------------------

    def get_active_session(self) -> Optional[sqlite3.Row]:
        row = self._db.execute(
            "SELECT * FROM sessions WHERE closed_at IS NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row

    def get_active_session_for_branch(self, branch: Optional[str]) -> Optional[sqlite3.Row]:
        if branch is None:
            row = self._db.execute(
                "SELECT * FROM sessions WHERE closed_at IS NULL AND branch IS NULL "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
        else:
            row = self._db.execute(
                "SELECT * FROM sessions WHERE closed_at IS NULL AND branch = ? "
                "ORDER BY id DESC LIMIT 1",
                (branch,),
            ).fetchone()
        return row

    def get_session_by_id(self, session_id: int) -> Optional[sqlite3.Row]:
        return self._db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()

    def open_session(
        self,
        *,
        name: str,
        goal: Optional[str],
        primary_metric: str,
        metric_unit: str,
        direction: str,
        preferred_command: Optional[str],
        branch: Optional[str],
        baseline_commit: Optional[str],
        max_iterations: Optional[int],
        scope_paths: list[str],
        off_limits: list[str],
        constraints: list[str],
        secondary_metrics: list[str],
        provider: str,
        model: str,
    ) -> int:
        cur = self._db.execute(
            """INSERT INTO sessions (
                name, goal, primary_metric, metric_unit, direction,
                preferred_command, branch, baseline_commit, max_iterations,
                scope_paths_json, off_limits_json, constraints_json,
                secondary_metrics_json, provider, model, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name, goal, primary_metric, metric_unit, direction,
                preferred_command, branch, baseline_commit, max_iterations,
                json.dumps(scope_paths), json.dumps(off_limits),
                json.dumps(constraints), json.dumps(secondary_metrics),
                provider, model, int(time.time() * 1000),
            ),
        )
        self._db.commit()
        return int(cur.lastrowid)

    def update_session(self, session_id: int, **updates: Any) -> None:
        column_map = {
            "goal": "goal",
            "preferred_command": "preferred_command",
            "max_iterations": "max_iterations",
            "scope_paths": "scope_paths_json",
            "off_limits": "off_limits_json",
            "constraints": "constraints_json",
            "secondary_metrics": "secondary_metrics_json",
            "primary_metric": "primary_metric",
            "metric_unit": "metric_unit",
            "direction": "direction",
            "branch": "branch",
            "baseline_commit": "baseline_commit",
            "notes": "notes",
            "provider": "provider",
            "model": "model",
        }
        json_columns = {"scope_paths", "off_limits", "constraints", "secondary_metrics"}
        sets: list[str] = []
        values: list[Any] = []
        for key, value in updates.items():
            column = column_map.get(key)
            if column is None:
                raise KeyError(key)
            sets.append(f"{column} = ?")
            values.append(json.dumps(list(value)) if key in json_columns else value)
        if not sets:
            return
        values.append(session_id)
        self._db.execute(f"UPDATE sessions SET {', '.join(sets)} WHERE id=?", values)
        self._db.commit()

    def bump_segment(self, session_id: int) -> None:
        self._db.execute(
            "UPDATE sessions SET current_segment = current_segment + 1 WHERE id=?", (session_id,)
        )
        self._db.commit()

    def close_session(self, session_id: int) -> None:
        self._db.execute(
            "UPDATE sessions SET closed_at=? WHERE id=?", (int(time.time() * 1000), session_id)
        )
        self._db.commit()

    # -- runs ---------------------------------------------------------------

    def insert_run(
        self,
        *,
        session_id: int,
        segment: int,
        command: str,
        log_path: str,
        pre_run_dirty_paths: list[str],
    ) -> int:
        cur = self._db.execute(
            "INSERT INTO runs (session_id, segment, command, started_at, log_path, "
            "pre_run_dirty_paths_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                session_id, segment, command, int(time.time() * 1000), log_path,
                json.dumps(pre_run_dirty_paths),
            ),
        )
        self._db.commit()
        return int(cur.lastrowid)

    def update_run_log_path(self, run_id: int, log_path: str) -> None:
        self._db.execute("UPDATE runs SET log_path=? WHERE id=?", (log_path, run_id))
        self._db.commit()

    def mark_run_completed(
        self,
        run_id: int,
        *,
        exit_code: Optional[int],
        timed_out: bool,
        duration_ms: int,
        parsed_primary: Optional[float],
        parsed_metrics: Optional[dict],
        parsed_asi: Optional[dict],
    ) -> None:
        self._db.execute(
            """UPDATE runs SET completed_at=?, duration_ms=?, exit_code=?, timed_out=?,
               parsed_primary=?, parsed_metrics_json=?, parsed_asi_json=? WHERE id=?""",
            (
                int(time.time() * 1000), duration_ms, exit_code, 1 if timed_out else 0,
                parsed_primary,
                json.dumps(parsed_metrics) if parsed_metrics is not None else None,
                json.dumps(parsed_asi) if parsed_asi is not None else None,
                run_id,
            ),
        )
        self._db.commit()

    def mark_run_logged(
        self,
        run_id: int,
        *,
        status: str,
        description: str,
        metric: float,
        metrics: dict,
        asi: Optional[dict],
        commit_hash: Optional[str],
        confidence: Optional[float],
        modified_paths: list[str],
        scope_deviations: list[str],
        justification: Optional[str],
    ) -> None:
        self._db.execute(
            """UPDATE runs SET status=?, description=?, metric=?, metrics_json=?, asi_json=?,
               commit_hash=?, confidence=?, modified_paths_json=?, scope_deviations_json=?,
               justification=?, logged_at=? WHERE id=?""",
            (
                status, description, metric, json.dumps(metrics),
                json.dumps(asi) if asi is not None else None,
                commit_hash, confidence, json.dumps(modified_paths),
                json.dumps(scope_deviations), justification,
                int(time.time() * 1000), run_id,
            ),
        )
        self._db.commit()

    def flag_run(self, run_id: int, reason: str) -> None:
        self._db.execute(
            "UPDATE runs SET flagged=1, flagged_reason=? WHERE id=?", (reason, run_id)
        )
        self._db.commit()

    def abandon_pending_runs(self, session_id: int) -> int:
        cur = self._db.execute(
            "UPDATE runs SET abandoned_at=? WHERE session_id=? AND status IS NULL "
            "AND abandoned_at IS NULL",
            (int(time.time() * 1000), session_id),
        )
        self._db.commit()
        return cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0

    def get_pending_run(self, session_id: int) -> Optional[sqlite3.Row]:
        return self._db.execute(
            "SELECT * FROM runs WHERE session_id=? AND status IS NULL AND abandoned_at "
            "IS NULL ORDER BY id DESC LIMIT 1",
            (session_id,),
        ).fetchone()

    def get_run_by_id(self, run_id: int) -> Optional[sqlite3.Row]:
        return self._db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()

    def list_runs(self, session_id: int) -> list[sqlite3.Row]:
        return self._db.execute(
            "SELECT * FROM runs WHERE session_id=? ORDER BY id ASC", (session_id,)
        ).fetchall()

    def list_logged_runs(self, session_id: int) -> list[sqlite3.Row]:
        return self._db.execute(
            "SELECT * FROM runs WHERE session_id=? AND status IS NOT NULL ORDER BY id ASC",
            (session_id,),
        ).fetchall()


_storage_cache: dict[str, AutoresearchStorage] = {}


def open_storage(cwd: str) -> AutoresearchStorage:
    db_path = autoresearch_db_path(cwd)
    cached = _storage_cache.get(str(db_path))
    if cached:
        return cached
    project_dir = db_path.parent / encode_project_key(git_repo_root(cwd) or cwd)
    storage = AutoresearchStorage(db_path, project_dir)
    _storage_cache[str(db_path)] = storage
    return storage


def open_storage_if_exists(cwd: str) -> Optional[AutoresearchStorage]:
    db_path = autoresearch_db_path(cwd)
    cached = _storage_cache.get(str(db_path))
    if cached:
        return cached
    if not db_path.exists():
        return None
    project_dir = db_path.parent / encode_project_key(git_repo_root(cwd) or cwd)
    storage = AutoresearchStorage(db_path, project_dir)
    _storage_cache[str(db_path)] = storage
    return storage


# ---------------------------------------------------------------------------
# Experiment state math (ported from state.ts)
# ---------------------------------------------------------------------------


def current_results(results: list[sqlite3.Row], segment: int) -> list[sqlite3.Row]:
    return [r for r in results if r["segment"] == segment]


def find_baseline_result(results: list[sqlite3.Row], segment: int) -> Optional[sqlite3.Row]:
    for r in current_results(results, segment):
        if r["status"] == STATUS_KEEP and not r["flagged"]:
            return r
    return None


def find_baseline_metric(results: list[sqlite3.Row], segment: int) -> Optional[float]:
    baseline = find_baseline_result(results, segment)
    return baseline["metric"] if baseline else None


def find_best_kept_metric(
    results: list[sqlite3.Row], segment: int, direction: str
) -> Optional[float]:
    best: Optional[float] = None
    for r in current_results(results, segment):
        if r["status"] != STATUS_KEEP or r["flagged"]:
            continue
        if best is None or is_better(r["metric"], best, direction):
            best = r["metric"]
    return best


def sorted_median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 0:
        return (ordered[midpoint - 1] + ordered[midpoint]) / 2
    return ordered[midpoint]


def compute_confidence(
    results: list[sqlite3.Row], segment: int, direction: str
) -> Optional[float]:
    usable = [
        r
        for r in current_results(results, segment)
        if not r["flagged"] and (r["metric"] or 0) > 0
    ]
    if len(usable) < 3:
        return None
    values = [r["metric"] for r in usable]
    median = sorted_median(values)
    mad = sorted_median([abs(v - median) for v in values])
    if mad == 0:
        return None
    baseline = find_baseline_metric(results, segment)
    if baseline is None:
        return None
    best_kept: Optional[float] = None
    for r in usable:
        if r["status"] != STATUS_KEEP or (r["metric"] or 0) <= 0:
            continue
        if best_kept is None or is_better(r["metric"], best_kept, direction):
            best_kept = r["metric"]
    if best_kept is None or best_kept == baseline:
        return None
    return abs(best_kept - baseline) / mad


# ---------------------------------------------------------------------------
# Experiment execution — frozen harness, process-tree timeout/cleanup
# ---------------------------------------------------------------------------


def resolve_harness_command(cwd: str) -> tuple[Optional[str], Optional[str]]:
    """Return the frozen harness command, or an error.

    The harness entrypoint is the project-defined ``./autoresearch.sh``
    compatibility shim (task contract). It must exist at run time; identity
    was frozen at init by committing it on the autoresearch branch.
    """
    harness = Path(cwd) / HARNESS_FILENAME
    if not harness.is_file():
        return None, f"./{HARNESS_FILENAME} does not exist — call init first."
    return DEFAULT_HARNESS_COMMAND, None


def run_experiment_process(
    command: str,
    cwd: str,
    log_path: Path,
    timeout_seconds: int = DEFAULT_RUN_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run the harness with process-tree timeout/cleanup.

    POSIX-only start-new-session kill (matches OMP's killTree semantics).
    Returns {exit_code, killed(timed_out), duration_ms}.
    """
    import signal as signal_module

    started = time.monotonic()
    timed_out = False
    proc: Optional[subprocess.Popen] = None
    try:
        with open(log_path, "wb") as log_file:
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                proc.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_process_tree(proc.pid, signal_module.SIGKILL)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
    finally:
        duration_ms = int((time.monotonic() - started) * 1000)

    exit_code = proc.returncode if proc is not None else None
    return {
        "exit_code": exit_code,
        "timed_out": timed_out or (exit_code is not None and exit_code == -signal_module.SIGKILL),
        "duration_ms": duration_ms,
    }


def _kill_process_tree(pid: int, sig: int) -> None:
    """Kill the whole process group (start_new_session made pid the leader)."""
    import signal as signal_module
    import errno

    try:
        os.killpg(pid, sig)
        return
    except OSError as exc:
        if exc.errno not in (errno.EPERM, errno.ESRCH):
            pass
    try:
        os.kill(pid, signal_module.SIGKILL)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# High-level operations used by both CLI and slash handler
# ---------------------------------------------------------------------------


def cmd_status(cwd: str) -> str:
    storage = open_storage_if_exists(cwd)
    if not storage:
        return "No autoresearch session for this project."
    branch = git_current_branch(cwd)
    session = storage.get_active_session_for_branch(branch)
    if not session:
        active = storage.get_active_session()
        if active:
            return (
                f"Active session #{active['id']} '{active['name']}' exists but is bound "
                f"to branch '{active['branch']}' (current: {branch}). Switch branches to resume."
            )
        return "No active autoresearch session."
    runs = storage.list_runs(session["id"])
    logged = [r for r in runs if r["status"]]
    pending = storage.get_pending_run(session["id"])
    lines = [
        f"Session #{session['id']}: {session['name']}",
        f"Goal: {session['goal'] or '(unset)'}",
        f"Metric: {session['primary_metric']} ({session['metric_unit'] or 'unitless'}, "
        f"{session['direction']} is better)",
        f"Branch: {session['branch']}  Segment: {session['current_segment']}",
    ]
    if json.loads(session["off_limits_json"]):
        lines.append(f"Off limits: {session['off_limits_json']}")
    if session["max_iterations"]:
        seg_count = len(current_results(logged, session["current_segment"]))
        lines.append(f"Progress: {seg_count}/{session['max_iterations']} runs this segment")
    baseline = find_baseline_metric([r for r in logged], session["current_segment"])
    best = find_best_kept_metric([r for r in logged], session["current_segment"], session["direction"])
    lines.append(f"Baseline: {baseline if baseline is not None else '-'}  Best kept: {best if best is not None else '-'}")
    lines.append(f"Runs logged: {len(logged)}  Pending: #{pending['id']}" if pending else f"Runs logged: {len(logged)}")
    if session["model"]:
        lines.append(f"Pinned model: {session['provider']}/{session['model']}")
    return "\n".join(lines)


def require_canary_model(provider: Optional[str], model: Optional[str]) -> Optional[str]:
    """Fail closed unless the session runs the pinned canary model."""
    expected_provider = os.environ.get("HERMES_AUTORESEARCH_EXPECT_PROVIDER", CANARY_PROVIDER)
    expected_model = os.environ.get("HERMES_AUTORESEARCH_EXPECT_MODEL", CANARY_MODEL)
    if provider and model:
        if provider.lower() != expected_provider.lower() or model.lower() != expected_model.lower():
            return (
                f"Model mismatch: autoresearch canary requires "
                f"{expected_provider}/{expected_model}, got {provider}/{model}. Failing closed."
            )
    return None


def cmd_init(
    cwd: str,
    name: str,
    primary_metric: str,
    *,
    goal: Optional[str] = None,
    metric_unit: str = "",
    direction: str = "lower",
    secondary_metrics: Optional[list[str]] = None,
    scope_paths: Optional[list[str]] = None,
    off_limits: Optional[list[str]] = None,
    constraints: Optional[list[str]] = None,
    max_iterations: Optional[int] = None,
    new_segment: bool = False,
    provider: str = "",
    model: str = "",
) -> str:
    mismatch = require_canary_model(provider or None, model or None)
    if mismatch:
        return mismatch

    ok, branch_name, error, _created = ensure_autoresearch_branch(cwd, goal)
    if not ok:
        return error or "Failed to secure autoresearch branch."

    storage = open_storage(cwd)
    existing = storage.get_active_session_for_branch(branch_name)
    requires_harness = existing is None or new_segment

    harness_path = Path(cwd) / HARNESS_FILENAME
    if requires_harness and not harness_path.is_file():
        return (
            f"./{HARNESS_FILENAME} does not exist. Phase 1 of autoresearch is harness "
            f"setup — write `./{HARNESS_FILENAME}` so it exits 0 and prints "
            f"`METRIC <name>=<value>`, validate it via `bash {HARNESS_FILENAME}`, commit it, "
            "then init again."
        )
    if requires_harness:
        dirty = [e["path"] for e in git_dirty_paths(cwd)]
        if dirty:
            return (
                "Harness must be committed before iteration. Uncommitted changes: "
                f"{', '.join(dirty[:8])}. Commit them and retry."
            )

    baseline_commit = git_head_sha(cwd)
    if requires_harness and not baseline_commit:
        return "Cannot read HEAD — refusing to record a baseline without a commit."

    if existing is None:
        session_id = storage.open_session(
            name=name,
            goal=goal,
            primary_metric=primary_metric,
            metric_unit=metric_unit,
            direction=direction,
            preferred_command=DEFAULT_HARNESS_COMMAND,
            branch=branch_name,
            baseline_commit=baseline_commit,
            max_iterations=max_iterations,
            scope_paths=[p.strip() for p in (scope_paths or []) if p.strip()],
            off_limits=[p.strip() for p in (off_limits or []) if p.strip()],
            constraints=[c.strip() for c in (constraints or []) if c.strip()],
            secondary_metrics=[m.strip() for m in (secondary_metrics or []) if m.strip()],
            provider=provider,
            model=model,
        )
        verb = "Started"
    else:
        storage.abandon_pending_runs(existing["id"])
        storage.update_session(
            existing["id"],
            goal=goal,
            primary_metric=primary_metric,
            metric_unit=metric_unit,
            direction=direction,
            max_iterations=max_iterations,
            scope_paths=[p.strip() for p in (scope_paths or []) if p.strip()] or json.loads(existing["scope_paths_json"]),
            off_limits=[p.strip() for p in (off_limits or []) if p.strip()] or json.loads(existing["off_limits_json"]),
            constraints=[c.strip() for c in (constraints or []) if c.strip()] or json.loads(existing["constraints_json"]),
            secondary_metrics=[m.strip() for m in (secondary_metrics or []) if m.strip()] or json.loads(existing["secondary_metrics_json"]),
            branch=branch_name,
            provider=provider or existing["provider"],
            model=model or existing["model"],
        )
        if new_segment:
            storage.update_session(existing["id"], baseline_commit=baseline_commit)
            storage.bump_segment(existing["id"])
        session_id = existing["id"]
        verb = "Updated" if not new_segment else "New segment for"

    session = storage.get_session_by_id(session_id)
    lines = [
        f"{verb} session #{session_id}: {name}",
        f"Metric: {primary_metric} ({metric_unit or 'unitless'}, {direction} is better)",
        f"Benchmark entrypoint: {DEFAULT_HARNESS_COMMAND}",
    ]
    if off_limits:
        lines.append(f"Off limits: {', '.join(off_limits)}")
    if scope_paths:
        lines.append(f"In scope: {', '.join(scope_paths)}")
    if max_iterations:
        lines.append(f"Max iterations per segment: {max_iterations}")
    lines.append(f"Branch: {branch_name}")
    if baseline_commit:
        lines.append(f"Baseline commit: {baseline_commit[:12]}")
    lines.append("Phase 2: run `bash autoresearch.sh`, then log the outcome via `hermes autoresearch log ...` or the /autoresearch flow.")
    return "\n".join(lines)


def cmd_off(cwd: str) -> str:
    storage = open_storage_if_exists(cwd)
    if not storage:
        return "No autoresearch state for this project."
    branch = git_current_branch(cwd)
    session = storage.get_active_session_for_branch(branch)
    if not session:
        return "No active autoresearch session."
    pending = storage.get_pending_run(session["id"])
    note = ""
    if pending:
        storage.abandon_pending_runs(session["id"])
        note = f" Abandoned pending run #{pending['id']}."
    return f"Autoresearch mode off (session #{session['id']} stays open for resume).{note}"


def cmd_clear(cwd: str, keep_tree: bool = False, reset_tree_force: bool = False) -> str:
    storage = open_storage_if_exists(cwd)
    if not storage:
        return "No autoresearch state for this project."
    branch = git_current_branch(cwd) or ""
    session = storage.get_active_session()
    notes: list[str] = []
    should_reset = not keep_tree and (
        branch.startswith(AUTORESEARCH_BRANCH_PREFIX) or reset_tree_force
    )
    if should_reset:
        if session and session["baseline_commit"]:
            # Safety: refuse to destroy user dirt on --reset-tree outside our branch.
            if reset_tree_force and not branch.startswith(AUTORESEARCH_BRANCH_PREFIX):
                dirty = [e["path"] for e in git_dirty_paths(cwd)]
                if dirty:
                    return (
                        "Refusing --reset-tree: worktree has uncommitted changes "
                        f"({', '.join(dirty[:5])}) and you are not on an autoresearch/* branch. "
                        "Commit/stash first or use --keep-tree."
                    )
            _run_git(cwd, "reset", "--hard", session["baseline_commit"])
            _run_git(cwd, "clean", "-fd")
            notes.append(f"Reset worktree to baseline {session['baseline_commit'][:12]}")
        elif session:
            notes.append("No baseline commit recorded — skipped worktree reset.")
    if session:
        storage.abandon_pending_runs(session["id"])
        storage.close_session(session["id"])
        notes.append(f"Closed session #{session['id']}.")
    return "\n".join(notes) or "Autoresearch cleared."


def cmd_run(cwd: str, timeout_seconds: int = DEFAULT_RUN_TIMEOUT_SECONDS) -> str:
    """Execute the frozen harness once and record the pending run."""
    storage = open_storage_if_exists(cwd)
    branch = git_current_branch(cwd)
    session = storage.get_active_session_for_branch(branch) if storage else None
    if not storage or not session:
        return "Error: no active autoresearch session for the current branch."

    abandoned = storage.abandon_pending_runs(session["id"])

    command, err = resolve_harness_command(cwd)
    if not command:
        return f"Error: {err}"

    pre_run_dirty = [e["path"] for e in git_dirty_paths(cwd)]
    run_id = storage.insert_run(
        session_id=session["id"],
        segment=session["current_segment"],
        command=command,
        log_path="",
        pre_run_dirty_paths=pre_run_dirty,
    )
    run_dir = storage.project_dir / "runs" / f"{run_id:04d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "benchmark.log"
    storage.update_run_log_path(run_id, str(log_path))

    result = run_experiment_process(command, cwd, log_path, timeout_seconds)
    log_text = log_path.read_text(errors="replace") if log_path.exists() else ""

    parsed_metrics = parse_metric_lines(log_text)
    parsed_primary = parsed_metrics.get(session["primary_metric"])
    parsed_asi = parse_asi_lines(log_text)

    storage.mark_run_completed(
        run_id,
        exit_code=result["exit_code"],
        timed_out=result["timed_out"],
        duration_ms=result["duration_ms"],
        parsed_primary=parsed_primary,
        parsed_metrics=parsed_metrics or None,
        parsed_asi=parsed_asi,
    )

    passed = result["exit_code"] == 0 and not result["timed_out"]
    lines = [
        f"Run #{run_id} directory: {run_dir}",
        (
            f"TIMEOUT after {result['duration_ms'] / 1000:.1f}s"
            if result["timed_out"]
            else (
                f"FAILED with exit code {result['exit_code']} in {result['duration_ms'] / 1000:.1f}s"
                if not passed
                else f"PASSED in {result['duration_ms'] / 1000:.1f}s"
            )
        ),
    ]
    if abandoned:
        lines.insert(1, f"Note: abandoned prior pending run(s) before this run.")
    if parsed_primary is not None:
        lines.append(f"Parsed {session['primary_metric']}: {parsed_primary}")
    secondary = {k: v for k, v in parsed_metrics.items() if k != session["primary_metric"]}
    if secondary:
        lines.append(f"Secondary metrics: {secondary}")
    if parsed_asi:
        lines.append(f"ASI keys: {', '.join(parsed_asi)}")
    tail = "\n".join(log_text.splitlines()[-10:])
    if tail.strip():
        lines.append("")
        lines.append(tail)
    lines.append(
        "Pending run recorded — log it with `hermes autoresearch log <keep|discard|crash|checks_failed>` "
        "before the next run."
    )
    return "\n".join(lines)


def compute_scope_deviations(modified_paths: list[str], session: sqlite3.Row) -> list[str]:
    deviations: list[str] = []
    off_limits = json.loads(session["off_limits_json"])
    scope_paths = json.loads(session["scope_paths_json"])
    for file_path in modified_paths:
        if any(path_matches_spec(file_path, spec) for spec in off_limits):
            deviations.append(file_path)
            continue
        if scope_paths and not any(path_matches_spec(file_path, spec) for spec in scope_paths):
            deviations.append(file_path)
    return deviations


def cmd_log(
    cwd: str,
    status: str,
    description: str,
    metric: float,
    *,
    metrics: Optional[dict] = None,
    justification: Optional[str] = None,
    flags: Optional[list[tuple[int, str]]] = None,
) -> str:
    """Log the pending run: KEEP commits modified files, others revert safely.

    Security contract (fail closed):
      * scope/off-limits deviations block KEEP unless ``justification`` given;
      * discard reverts only on dedicated autoresearch/* branches (reset to
        HEAD so prior KEEP commits survive); off-branch it restores only
        run-modified tracked paths and removes only run-created untracked files.
    """
    if status not in EXPERIMENT_STATUSES:
        return f"Invalid status '{status}'. Use one of: {', '.join(EXPERIMENT_STATUSES)}."

    storage = open_storage_if_exists(cwd)
    branch = git_current_branch(cwd)
    session = storage.get_active_session_for_branch(branch) if storage else None
    if not storage or not session:
        return "Error: no active autoresearch session for the current branch."

    pending = storage.get_pending_run(session["id"])
    if not pending:
        return "Error: no pending run available. Run the experiment first (`hermes autoresearch run`)."

    warnings: list[str] = []

    for flag_run_id, reason in flags or []:
        target = storage.get_run_by_id(flag_run_id)
        if not target or target["session_id"] != session["id"]:
            warnings.append(f"Ignored flag for unknown run #{flag_run_id}")
            continue
        storage.flag_run(flag_run_id, reason)
        warnings.append(f"Flagged run #{flag_run_id}: {reason}")

    on_autoresearch_branch = bool(branch and branch.startswith(AUTORESEARCH_BRANCH_PREFIX))
    all_modified = [e["path"] for e in git_dirty_paths(cwd)]
    scope_deviations = compute_scope_deviations(all_modified, session)

    commit_hash = git_head_sha(cwd)
    git_note: Optional[str] = None

    if status == STATUS_KEEP:
        # Fail closed on scope violations: refuse the KEEP entirely rather than
        # logging it with a warning (OMP's permissive behavior is not acceptable
        # for autonomous Hermes use).
        if scope_deviations and not justification:
            return (
                "REFUSED: run modifies out-of-scope/off-limits paths "
                f"({', '.join(scope_deviations)}) without justification. Revert these "
                "files, or pass an explicit --justification explaining why the deviation "
                "is safe. Nothing was logged or committed."
            )
        if on_autoresearch_branch and all_modified:
            add = _run_git(cwd, "add", "--", *all_modified, check=False)
            if add.returncode != 0:
                return f"Error: git add failed: {add.stderr.strip()}"
            diff = _run_git(cwd, "diff", "--cached", "--quiet", check=False)
            if diff.returncode == 0:
                git_note = "nothing to commit"
            else:
                payload: dict[str, Any] = {"status": status, session["primary_metric"]: metric}
                for k, v in (metrics or {}).items():
                    payload[k] = v
                message = f"{description}\n\nResult: {json.dumps(payload)}"
                commit = _run_git(cwd, "commit", "-m", message, check=False)
                if commit.returncode != 0:
                    return f"Error: git commit failed: {commit.stderr.strip()}"
                git_note = "committed"
                commit_hash = git_head_sha(cwd)
        elif not on_autoresearch_branch:
            return (
                "REFUSED: KEEP auto-commit requires a dedicated autoresearch/* branch. "
                "Nothing logged. Restart `/autoresearch <goal>` from a clean tree."
            )
        else:
            git_note = "nothing to commit"
    else:
        if on_autoresearch_branch:
            # Reset to HEAD only — prior KEEP commits survive.
            _run_git(cwd, "reset", "--hard", "HEAD")
            _run_git(cwd, "clean", "-fd")
            git_note = "worktree reset to HEAD"
        else:
            # Off-branch: revert only paths this run modified relative to pre-run
            # snapshot; never touch user pre-existing dirt.
            pre_set = set(json.loads(pending["pre_run_dirty_paths_json"]))
            current_entries = git_dirty_paths(cwd)
            revert_tracked = [e["path"] for e in current_entries if not e["untracked"] and e["path"] not in pre_set]
            remove_untracked = [e["path"] for e in current_entries if e["untracked"] and e["path"] not in pre_set]
            if revert_tracked:
                _run_git(cwd, "restore", "--source=HEAD", "--staged", "--worktree", "--", *revert_tracked)
            for rel in remove_untracked:
                target = (Path(cwd) / rel).resolve()
                try:
                    if target.is_dir():
                        import shutil

                        shutil.rmtree(target)
                    elif target.exists():
                        target.unlink()
                except OSError:
                    pass
            total = len(revert_tracked) + len(remove_untracked)
            git_note = f"reverted {total} file(s)" if total else "nothing to revert"

    parsed_pending_metrics = json.loads(pending["parsed_metrics_json"]) if pending["parsed_metrics_json"] else {}
    merged_metrics = {k: v for k, v in parsed_pending_metrics.items() if k != session["primary_metric"]}
    merged_metrics.update(sanitize_metrics(metrics))
    merged_asi = json.loads(pending["parsed_asi_json"]) if pending["parsed_asi_json"] else None

    if pending["parsed_primary"] is not None and metric != pending["parsed_primary"]:
        warnings.append(
            f"Logged metric {metric} differs from parsed primary {pending['parsed_primary']}. Both stored."
        )

    logged_runs_before = storage.list_logged_runs(session["id"])
    storage.mark_run_logged(
        pending["id"],
        status=status,
        description=description,
        metric=metric,
        metrics=merged_metrics,
        asi=merged_asi,
        commit_hash=commit_hash,
        confidence=None,
        modified_paths=all_modified,
        scope_deviations=scope_deviations,
        justification=(justification.strip() or None) if justification else None,
    )

    refreshed = storage.get_session_by_id(session["id"])
    logged_runs = storage.list_logged_runs(session["id"])
    confidence = compute_confidence(logged_runs, refreshed["current_segment"], refreshed["direction"])
    if confidence is not None:
        storage._db.execute(
            "UPDATE runs SET confidence=? WHERE id=?", (confidence, pending["id"])
        )
        storage._db.commit()

    seg_count = len(current_results(logged_runs, refreshed["current_segment"]))
    lines = [f"Logged run #{pending['id']}: {status} - {description}"]
    baseline = find_baseline_metric(logged_runs, refreshed["current_segment"])
    if baseline is not None:
        lines.append(f"Baseline {refreshed['primary_metric']}: {baseline}")
    lines.append(f"This run: {metric}")
    if confidence is not None:
        quality = "likely real" if confidence >= 2 else ("marginal" if confidence >= 1 else "within noise")
        lines.append(f"Confidence: {confidence:.1f}x noise floor ({quality})")
    if scope_deviations and justification:
        lines.append(f"Kept with justified scope deviations: {', '.join(scope_deviations)}")
    if git_note:
        lines.append(f"Git: {git_note}")
    if refreshed["max_iterations"]:
        lines.append(f"Progress: {seg_count}/{refreshed['max_iterations']} runs this segment")
        if seg_count >= refreshed["max_iterations"]:
            lines.append(
                f"Maximum experiments reached ({refreshed['max_iterations']}). Autoresearch mode is now off."
            )
            storage.close_session(refreshed["id"])
    for w in warnings:
        lines.append(f"Warning: {w}")

    # Baseline sanity: the first KEEP in a segment defines the baseline; a later
    # KEEP whose metric equals the baseline with zero modifications would be a
    # no-op — surface it honestly instead of gaming the ledger.
    if (
        status == STATUS_KEEP
        and baseline is not None
        and metric == baseline
        and find_baseline_result(logged_runs_before, refreshed["current_segment"]) is not None
    ):
        lines.append("Note: kept run matches existing baseline with identical metric — verify this edit is real.")
    return "\n".join(lines)


def cmd_runs(cwd: str, limit: int = 20) -> str:
    storage = open_storage_if_exists(cwd)
    if not storage:
        return "No autoresearch state for this project."
    branch = git_current_branch(cwd)
    session = storage.get_active_session_for_branch(branch) if storage else None
    if not session:
        return "No active autoresearch session."
    runs = storage.list_runs(session["id"])
    if not runs:
        return "No runs yet."
    lines = [f"{'run':>4}  {'status':<14} {'metric':>10}  description"]
    for run in runs[-limit:]:
        status = run["status"] or ("PENDING" if not run["abandoned_at"] else "abandoned")
        metric = "-" if run["metric"] is None else f"{run['metric']:g}"
        lines.append(f"#{run['id']:<3} {status:<14} {metric:>10}  {run['description'] or ''}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Slash-string parsing shared by CLI / gateway (/autoresearch ...)
# ---------------------------------------------------------------------------


def run_slash(rest: str, cwd: Optional[str] = None) -> str:
    """Handle the ``/autoresearch …`` argument string; returns display text.

    Contract:
      * ``/autoresearch <goal>`` enters/resumes (static instruction message);
      * bare toggle turns mode off when a session is active on this branch;
      * ``off``, ``clear [--keep-tree|--reset-tree]`` per OMP.
    """
    cwd = cwd or os.getcwd()
    tokens = rest.split(maxsplit=1)
    head = tokens[0] if tokens else ""
    arg = tokens[1].strip() if len(tokens) > 1 else ""

    if head == "clear":
        keep_tree = "--keep-tree" in arg
        reset_tree = "--reset-tree" in arg
        return cmd_clear(cwd, keep_tree=keep_tree, reset_tree_force=reset_tree)
    if head == "off":
        return cmd_off(cwd)
    if head == "status":
        return cmd_status(cwd)
    if head == "runs":
        return cmd_runs(cwd)

    goal = rest.strip()
    storage = open_storage_if_exists(cwd)
    branch = git_current_branch(cwd)
    session = storage.get_active_session_for_branch(branch) if storage else None

    if not goal:
        if session:
            # Bare toggle off when active.
            return cmd_off(cwd)
        return cmd_status(cwd)

    if session:
        # Resume: refresh goal, hand back resume instructions.
        if session["goal"] != goal:
            storage.update_session(session["id"], goal=goal)
        return (
            f"Resuming autoresearch session #{session['id']} on branch {session['branch']}.\n"
            f"Goal: {goal}\n\n{resume_instructions(cwd)}"
        )

    return (
        "Entering autoresearch mode.\n\n"
        f"Goal: {goal}\n\n"
        "Setup checklist (phase 1):\n"
        f"1. Write `./{HARNESS_FILENAME}` — a committed, deterministic benchmark harness "
        "that exits 0 and prints `METRIC <name>=<value>` lines (plus optional "
        "`ASI key=value` metadata).\n"
        "2. Validate it: `bash autoresearch.sh`.\n"
        "3. Commit it, then initialize:\n"
        "   `hermes autoresearch init <name> --metric <name> [--direction lower|higher] "
        "[--off-limits p1,p2] [--scope p1,p2] [--max N]`\n\n"
        "Iteration (phase 2): `hermes autoresearch run` → inspect → "
        "`hermes autoresearch log keep|discard|crash|checks_failed --description \"...\" --metric N`.\n"
        "Scope/off-limits violations block KEEP without an explicit justification. "
        "Discard reverts only this experiment's changes; prior keeps survive."
    )


def resume_instructions(cwd: str) -> str:
    return (
        "Continue the loop: propose one change within scope, `hermes autoresearch run`, "
        "then `hermes autoresearch log ...` before any further run. Stop at "
        "max iterations, or `/autoresearch clear` to roll back."
    )


# ---------------------------------------------------------------------------
# argparse surface — `hermes autoresearch …`
# ---------------------------------------------------------------------------


def build_parser(parent_subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = parent_subparsers.add_parser(
        "autoresearch",
        help="Autonomous benchmark-optimization loop (OMP autoresearch port)",
        description=(
            "Durable autonomous research loop over a frozen benchmark harness. "
            "State lives in $HERMES_HOME/autoresearch/<project-key>.db; experiments "
            "run on dedicated autoresearch/* git branches."
        ),
    )
    sub = parser.add_subparsers(dest="autoresearch_action")

    sub.add_parser("status", help="Show active session summary")

    p_init = sub.add_parser("init", help="Initialize/reconfigure the experiment session")
    p_init.add_argument("name")
    p_init.add_argument("--metric", required=True, dest="primary_metric")
    p_init.add_argument("--unit", default="")
    p_init.add_argument("--direction", choices=("lower", "higher"), default="lower")
    p_init.add_argument("--goal", default=None)
    p_init.add_argument("--secondary-metrics", default="", help="comma-separated")
    p_init.add_argument("--scope", default="", help="comma-separated in-scope paths")
    p_init.add_argument("--off-limits", default="", help="comma-separated protected paths")
    p_init.add_argument("--constraints", default="", help="semicolon-separated")
    p_init.add_argument("--max-iterations", type=int, default=None)
    p_init.add_argument("--new-segment", action="store_true")

    sub.add_parser("off", help="Leave autoresearch mode (session stays resumable)")

    p_clear = sub.add_parser("clear", help="Close the session; optionally roll back the worktree")
    p_clear.add_argument("--keep-tree", action="store_true")
    p_clear.add_argument("--reset-tree", action="store_true")

    p_run = sub.add_parser("run", help="Run the frozen harness once (records a pending run)")
    p_run.add_argument("--timeout", type=int, default=DEFAULT_RUN_TIMEOUT_SECONDS)

    p_log = sub.add_parser("log", help="Log the pending run outcome")
    p_log.add_argument("status", choices=EXPERIMENT_STATUSES)
    p_log.add_argument("--metric", type=float, required=True)
    p_log.add_argument("--description", required=True)
    p_log.add_argument("--metrics", default="", help="k=v,k=v secondaries")
    p_log.add_argument("--justification", default=None)
    p_log.add_argument("--flag", action="append", nargs=2, metavar=("RUN_ID", "REASON"), default=[])

    p_runs = sub.add_parser("runs", help="List runs")
    p_runs.add_argument("--limit", type=int, default=20)

    return parser


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def autoresearch_command(args: argparse.Namespace) -> int:
    cwd = os.getcwd()
    action = getattr(args, "autoresearch_action", None) or "status"
    if action == "status":
        print(cmd_status(cwd))
    elif action == "init":
        print(
            cmd_init(
                cwd,
                args.name,
                args.primary_metric,
                goal=args.goal,
                metric_unit=args.unit,
                direction=args.direction,
                secondary_metrics=_split_csv(args.secondary_metrics),
                scope_paths=_split_csv(args.scope),
                off_limits=_split_csv(args.off_limits),
                constraints=[c.strip() for c in args.constraints.split(";") if c.strip()],
                max_iterations=args.max_iterations,
                new_segment=args.new_segment,
                provider=os.environ.get("HERMES_AUTORESEARCH_PROVIDER", CANARY_PROVIDER),
                model=os.environ.get("HERMES_AUTORESEARCH_MODEL", CANARY_MODEL),
            )
        )
    elif action == "off":
        print(cmd_off(cwd))
    elif action == "clear":
        print(cmd_clear(cwd, keep_tree=args.keep_tree, reset_tree_force=args.reset_tree))
    elif action == "run":
        print(cmd_run(cwd, timeout_seconds=args.timeout))
    elif action == "log":
        metrics: dict[str, float] = {}
        for pair in _split_csv(args.metrics):
            if "=" not in pair:
                print(f"Invalid --metrics entry (expected k=v): {pair}")
                return 1
            key, _, raw = pair.partition("=")
            try:
                metrics[key.strip()] = float(raw)
            except ValueError:
                print(f"Invalid numeric value for {key}: {raw}")
                return 1
        flags = [(int(run_id), reason) for run_id, reason in args.flag]
        print(
            cmd_log(
                cwd,
                args.status,
                args.description,
                args.metric,
                metrics=metrics,
                justification=args.justification,
                flags=flags,
            )
        )
    elif action == "runs":
        print(cmd_runs(cwd, limit=args.limit))
    return 0
