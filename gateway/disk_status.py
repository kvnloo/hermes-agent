"""Disk-usage rollup for ``/api/status``.

Companion to :mod:`gateway.memory_status`: a hosted agent can fill its data
volume (SQLite writes failing, config saves lost) while its dashboard looks
healthy.  Sampled live via one ``statvfs`` call, so there is no ``sampled_at``.
``/api/status`` is unauthenticated: only coarse numbers (MB, one-decimal
percent) and an enum.  Best-effort: an unreadable filesystem degrades to
``pressure="unknown"`` rather than raising into the status endpoint.
"""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from gateway.memory_status import _nonneg_int

logger = logging.getLogger(__name__)

# Percent alone misleads both ways: 90% used on 100 GB leaves 10 GB, while 50% on a tiny
# volume is one download from write failures.  So percent triggers are gated on absolute
# headroom also being low, and a hard floor applies regardless of size (below it SQLite
# journaling / config writes are at risk).  Rows: (level, free floor, used-%, headroom); worst first.
_PRESSURE_TIERS = (
    ("critical", 256, 95.0, 1024),  # < 256 MB free, or >= 95% used AND < 1 GB free
    ("elevated", 512, 85.0, 4096),  # < 512 MB free, or >= 85% used AND < 4 GB free
)
_BYTES_PER_MB = 1024 * 1024


def classify_disk_pressure(free_mb: Any, total_mb: Any) -> str:
    """``ok``/``elevated``/``critical`` from free/total MB; ``unknown`` when the sample
    is missing/malformed — "could not read it" must never read as "fine"."""
    free, total = _nonneg_int(free_mb), _nonneg_int(total_mb)
    if free is None or not total:
        return "unknown"
    used_percent = (1 - free / total) * 100.0
    for level, free_floor, percent_floor, headroom in _PRESSURE_TIERS:
        if free < free_floor or (used_percent >= percent_floor and free < headroom):
            return level
    return "ok"


def collect_disk_status(home: Optional[Path] = None) -> dict[str, Any]:
    """``disk`` block for ``/api/status`` (same ``home`` contract as ``memory``).
    Never raises — an unreadable/unmounted filesystem yields ``pressure="unknown"``."""
    status: dict[str, Any] = {"pressure": "unknown", "total_mb": None, "free_mb": None, "used_percent": None}
    try:
        if home is None:
            from hermes_constants import get_hermes_home

            home = get_hermes_home()
        usage = shutil.disk_usage(home)
    except Exception:
        return status
    if usage.total <= 0:
        return status
    total_mb, free_mb = usage.total // _BYTES_PER_MB, usage.free // _BYTES_PER_MB
    status.update(total_mb=total_mb, free_mb=free_mb, used_percent=round((usage.used / usage.total) * 100, 1),
                  pressure=classify_disk_pressure(free_mb, total_mb))
    return status


# ---------------------------------------------------------------------------
# Write-path guard: one shared verdict for "may Hermes start new work?"
# ---------------------------------------------------------------------------
# A full volume does not fail one write: it fails every write (transcripts, turn leases,
# admission settlement, runtime status, sessions.json, jobs.json, logs, provider temp files) and
# each layer reports its own error. Starting a turn, a kanban worker or a cron run into a
# critical volume spends a model call whose result cannot be saved. So the producers of new
# work ask this one guard first and defer (never drop) while it reads ``critical``.
# ``unknown`` (statvfs failed) never blocks: a broken probe must not brick the host.

_GUARD_TTL_SECONDS = 5.0
_guard_cache: Dict[tuple, tuple] = {}
_guard_state: Dict[str, str] = {}
_LEVEL_RANK = {"unknown": 0, "ok": 1, "elevated": 2, "critical": 3}
GUARD_DISABLE_ENV = "HERMES_DISK_GUARD"


def _guard_paths() -> list:
    """The volumes a turn writes to: HERMES_HOME (state.db, sessions, cron, logs) and the
    temp root (provider SDK spool files; an observed disk-full cascade began there)."""
    paths = []
    with contextlib.suppress(Exception):
        from hermes_constants import get_hermes_home

        paths.append(Path(get_hermes_home()))
    with contextlib.suppress(Exception):
        paths.append(Path(tempfile.gettempdir()))
    return paths


def _volume_sample(path: Path) -> Optional[tuple]:
    """``(st_dev, free_mb, total_mb)`` for *path*'s volume, ``None`` when unreadable."""
    try:
        dev = os.stat(path).st_dev
        usage = shutil.disk_usage(path)
    except OSError:
        return None
    if usage.total <= 0:
        return None
    return dev, usage.free // _BYTES_PER_MB, usage.total // _BYTES_PER_MB


def storage_pressure(paths: Optional[list] = None, *, now: Optional[float] = None) -> dict[str, Any]:
    """Worst disk pressure across the volumes in *paths* (default: HERMES_HOME + temp root).

    Returns ``{"pressure", "free_mb", "total_mb", "path"}`` for the worst volume. Cached for a
    few seconds so per-admission callers cost one dict lookup. Never raises. Setting
    ``HERMES_DISK_GUARD=off`` reports ``unknown`` (the guard's escape hatch).
    """
    verdict: dict[str, Any] = {"pressure": "unknown", "free_mb": None, "total_mb": None, "path": None}
    if os.environ.get(GUARD_DISABLE_ENV, "").strip().lower() in {"0", "off", "false", "no"}:
        return verdict
    if paths is None:
        paths = _guard_paths()
    key = tuple(str(p) for p in paths)
    clock = time.monotonic() if now is None else now
    cached = _guard_cache.get(key)
    if cached is not None and clock - cached[0] < _GUARD_TTL_SECONDS:
        return dict(cached[1])
    seen = set()
    for path in paths:
        sample = _volume_sample(Path(path))
        if sample is None:
            continue
        dev, free_mb, total_mb = sample
        if dev in seen:
            continue
        seen.add(dev)
        level = classify_disk_pressure(free_mb, total_mb)
        if _LEVEL_RANK.get(level, 0) > _LEVEL_RANK.get(verdict["pressure"], 0):
            verdict = {"pressure": level, "free_mb": free_mb, "total_mb": total_mb, "path": str(path)}
    _guard_cache[key] = (clock, dict(verdict))
    _note_transition(verdict)
    return verdict


def _note_transition(verdict: dict[str, Any]) -> None:
    """One WARNING when the host enters ``critical`` and one INFO when it leaves: the degraded
    state is announced once instead of surfacing as a dozen downstream write errors."""
    level = str(verdict.get("pressure") or "unknown")
    if level == "unknown":
        return
    previous = _guard_state.get("level")
    _guard_state["level"] = level
    if level == "critical" and previous != "critical":
        logger.warning(
            "Disk guard: %s has %s MB free (critical); new turns, kanban workers and cron runs are "
            "deferred until space is freed", verdict.get("path"), verdict.get("free_mb"))
    elif previous == "critical" and level != "critical":
        logger.info("Disk guard: %s recovered to %s (%s MB free); new work resumes",
                    verdict.get("path"), level, verdict.get("free_mb"))


def new_work_refusal(paths: Optional[list] = None) -> Optional[str]:
    """``None`` when new work may start, else a one-line reason (critical disk only)."""
    verdict = storage_pressure(paths)
    if verdict["pressure"] != "critical":
        return None
    return f"disk critical: {verdict['free_mb']} MB free on the volume holding {verdict['path']}"


def reset_guard_cache() -> None:
    """Test seam: forget cached samples and the announced state."""
    _guard_cache.clear()
    _guard_state.clear()
