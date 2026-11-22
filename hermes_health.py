"""Persistent, per-home health ledger: "still failing" conditions and once-per-day notices.

Two problems this fixes, both measured on a multi-profile install:

* **Per-process dedupe does not survive per-turn processes.** ``skill_utils`` warned about a
  shadowed skill "once" — but per *process*; a kanban worker or TUI turn that runs in a fresh
  process re-warned every time (7 skills x ~1,030 workers = 7,200 WARNING lines in 2 days,
  73% of errors.log). :func:`warn_once` keys the notice on disk under ``<HERMES_HOME>/logs``
  so it reaches errors.log once per *ttl* per profile, however many processes start.
* **Real failures were demoted to DEBUG and then invisible.** A plugin hook failing with
  EPERM on every call warns once and then logs at DEBUG "from now on"; nothing records that it is
  *still* failing. :func:`record` keeps ``count`` / ``first_seen`` / ``last_seen`` per condition
  so ``hermes doctor`` (and any owner-facing surface) can show it, and :func:`resolve` clears it
  when the condition heals.

The ledger is best-effort: every public function swallows ``OSError`` / ``ValueError`` (a full
disk must not turn a log call into a crash) and the file is bounded to :data:`MAX_ENTRIES`.
Writes are throttled per condition (:data:`WRITE_THROTTLE_S`) so a condition that recurs on
every tool call costs one small file write per minute, not one per call.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Iterator, Optional

LEDGER_NAME = "health.json"
MAX_ENTRIES = 256
SUMMARY_CHARS = 500
KEY_CHARS = 300
NOTICE_TTL_S = 24 * 3600
WRITE_THROTTLE_S = 60.0
ACTIVE_WINDOW_S = 24 * 3600

# Severity of a ledger entry. ``notice`` = configuration noise (shadowed skill, ignored plugin
# registration) the owner may act on but nothing is broken; ``failure`` = a harness path that is
# not working (hook raising, cron job erroring, disk full) and must stay visible until resolved.
NOTICE, FAILURE = "notice", "failure"

_lock = threading.Lock()
# id -> [pending count delta, monotonic time of last write]; per process, bounded by MAX_ENTRIES.
_pending: dict[str, list[float]] = {}


def ledger_path(home: Optional[Path | str] = None) -> Path:
    if home is None:
        from hermes_constants import get_hermes_home
        home = get_hermes_home()
    return Path(home) / "logs" / LEDGER_NAME


def _cond_id(kind: str, key: str) -> str:
    return hashlib.sha256(f"{kind}\0{key}".encode("utf-8", "replace")).hexdigest()[:20]


@contextlib.contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    """Cross-process exclusive lock on ``<ledger>.lock`` (no-op where fcntl is unavailable)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import fcntl
    except ImportError:  # Windows: the in-process lock still serializes threads
        yield
        return
    fd = os.open(str(path.with_suffix(".lock")), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    conds = data.get("conditions") if isinstance(data, dict) else None
    return conds if isinstance(conds, dict) else {}


def _save(path: Path, conds: dict[str, Any]) -> None:
    if len(conds) > MAX_ENTRIES:
        keep = sorted(conds.items(), key=lambda kv: kv[1].get("last_seen", 0), reverse=True)[:MAX_ENTRIES]
        conds.clear()
        conds.update(keep)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"version": 1, "conditions": conds}, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _upsert(kind: str, key: str, summary: str, severity: str, *, report_ttl: Optional[float],
            home: Optional[Path | str], now: Optional[float], force_write: bool) -> tuple[Optional[dict], bool]:
    """Record one occurrence. Returns ``(entry, should_report)``; ``(None, True)`` when the ledger
    could not be used (callers then fall back to plain logging). ``entry`` is None too when the
    write was throttled — the occurrence is counted in memory and flushed with the next write."""
    now = time.time() if now is None else now
    cid = _cond_id(kind, key)
    mono = time.monotonic()
    with _lock:
        slot = _pending.setdefault(cid, [0, float("-inf")])
        slot[0] += 1
        if not force_write and report_ttl is None and mono - slot[1] < WRITE_THROTTLE_S:
            return None, False
        delta, slot[0], slot[1] = int(slot[0]), 0, mono
        if len(_pending) > MAX_ENTRIES:
            _pending.clear()
    try:
        path = ledger_path(home)
        with _file_lock(path):
            conds = _load(path)
            entry = conds.get(cid) or {"kind": kind, "key": key[:KEY_CHARS], "first_seen": now, "count": 0}
            entry.update(summary=summary[:SUMMARY_CHARS], severity=severity, last_seen=now,
                         count=int(entry.get("count", 0)) + delta)
            entry.pop("resolved_at", None)
            report = False
            if report_ttl is not None:
                last = entry.get("last_reported")
                report = last is None or now - float(last) >= report_ttl
                if report:
                    entry["last_reported"] = now
            conds[cid] = entry
            _save(path, conds)
            return dict(entry), report
    except (OSError, ValueError, TypeError):
        return None, True


def record(kind: str, key: str, summary: str, *, severity: str = FAILURE,
           home: Optional[Path | str] = None, now: Optional[float] = None) -> Optional[dict]:
    """Note that condition ``(kind, key)`` happened (again). Never raises.

    Repeats of one condition within :data:`WRITE_THROTTLE_S` are counted in memory and written
    with the next flush, so this is safe to call on every tool call."""
    entry, _ = _upsert(kind, key, summary, severity, report_ttl=None, home=home, now=now, force_write=False)
    return entry


def resolve(kind: str, key: str, *, home: Optional[Path | str] = None, now: Optional[float] = None) -> bool:
    """Mark a condition healed (kept, with ``resolved_at``, so the owner can see it recovered)."""
    cid = _cond_id(kind, key)
    with _lock:
        _pending.pop(cid, None)
    try:
        path = ledger_path(home)
        if not path.exists():
            return False
        with _file_lock(path):
            conds = _load(path)
            entry = conds.get(cid)
            if not entry or entry.get("resolved_at"):
                return False
            entry["resolved_at"] = time.time() if now is None else now
            _save(path, conds)
            return True
    except (OSError, ValueError, TypeError):
        return False


def conditions(*, home: Optional[Path | str] = None, include_resolved: bool = False) -> list[dict]:
    """Ledger entries, most recently seen first."""
    rows = [dict(v, id=k) for k, v in _load(ledger_path(home)).items()
            if include_resolved or not v.get("resolved_at")]
    return sorted(rows, key=lambda r: r.get("last_seen", 0), reverse=True)


def active_failures(*, home: Optional[Path | str] = None, window_s: float = ACTIVE_WINDOW_S,
                    now: Optional[float] = None) -> list[dict]:
    """Unresolved ``failure`` entries seen within *window_s* — the "still failing" list."""
    now = time.time() if now is None else now
    return [r for r in conditions(home=home)
            if r.get("severity") == FAILURE and now - float(r.get("last_seen", 0)) <= window_s]


def warn_once(logger: logging.Logger, kind: str, key: str, msg: str, *args: Any,
              ttl: float = NOTICE_TTL_S, severity: str = NOTICE,
              home: Optional[Path | str] = None, now: Optional[float] = None) -> bool:
    """WARNING at most once per *ttl* per Hermes home for ``(kind, key)``, across processes;
    DEBUG otherwise. Every occurrence is counted in the ledger. Returns True when it warned.

    Use this for conditions that are stable facts about the configuration (they recur on every
    process start or skill scan until the owner changes config), not for transient failures."""
    entry, report = _upsert(kind, key, (msg % args) if args else msg, severity,
                            report_ttl=ttl, home=home, now=now, force_write=True)
    if report:
        suffix = "" if entry is None else (
            f" [reported once per {int(ttl // 3600) or 1}h per profile; seen {entry['count']}x — `hermes doctor` lists it]")
        logger.warning(msg + suffix, *args)
        return True
    logger.debug(msg, *args)
    return False


def _reset_for_tests() -> None:
    with _lock:
        _pending.clear()
