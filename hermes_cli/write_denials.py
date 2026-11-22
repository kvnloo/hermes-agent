"""Tell an OS-policy write denial apart from a plain permission error, and remember it.

A macOS Seatbelt profile (``sandbox-exec -f``), TCC, a Linux LSM or a container read-only mount
can refuse a write that the file's POSIX mode and ownership allow. Python sees the same
``PermissionError`` either way, so callers treated a sandbox wall like a flaky write: plugin
hooks logged it once and then went quiet at DEBUG, and agents retried it hundreds of times.

:func:`classify_write_error` names the cause from the error and the nearest existing path's
``stat``. :func:`record_write_denial` keeps one persistent entry per (source, path) in
``<HERMES_HOME>/state/write_denials.json`` with a count and first/last-seen times, so a failure
that later logs are deduplicated away from stays visible to ``hermes doctor`` until it is fixed.
Nothing here raises: diagnostics must never break the caller.
"""

from __future__ import annotations

import errno
import json
import logging
import os
import stat
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

POLICY_DENIED = "os_policy_denied"      # mode bits allow the write; a sandbox/TCC/MAC layer refused it
PERMISSION_DENIED = "permission_denied"  # mode bits, ownership or a BSD immutable flag refuse it
READ_ONLY_FS = "read_only_fs"

_WRITE_ERRNOS = {errno.EPERM, errno.EACCES, errno.EROFS}
_IMMUTABLE_FLAGS = (getattr(stat, "UF_IMMUTABLE", 0) | getattr(stat, "SF_IMMUTABLE", 0)
                    | getattr(stat, "UF_APPEND", 0) | getattr(stat, "SF_APPEND", 0))
_STORE_NAME = "write_denials.json"
_PERSIST_EVERY_S = 60.0  # repeats of a known (source, path) rewrite the store at most this often
_MAX_ENTRIES = 200

_lock = threading.Lock()
_last_persisted: dict[tuple[str, str, str], float] = {}


def _nearest_existing(path: Path, stat_fn: Callable) -> tuple[Optional[Path], Any, bool]:
    """(path, stat, is_target) for *path* or its nearest existing ancestor."""
    probe, is_target = path, True
    for _ in range(64):
        try:
            return probe, stat_fn(probe), is_target
        except OSError:
            if probe.parent == probe:
                break
            probe, is_target = probe.parent, False
    return None, None, False


def _mode_grants_write(st: Any, uid: int, gids: set[int]) -> bool:
    if uid == 0:
        return True  # root passes the POSIX check; only a policy layer can refuse it
    mode = st.st_mode
    if st.st_uid == uid:
        return bool(mode & stat.S_IWUSR)
    if st.st_gid in gids:
        return bool(mode & stat.S_IWGRP)
    return bool(mode & stat.S_IWOTH)


def classify_write_error(exc: BaseException, path: str | os.PathLike | None = None, *,
                         stat_fn: Callable = os.stat, uid: Optional[int] = None,
                         gids: Optional[set[int]] = None) -> Optional[str]:
    """Name the cause of a failed write, or ``None`` when *exc* is not a write denial.

    ``os_policy_denied`` means the POSIX check would have allowed the write (the caller owns the
    target, or the parent it would be created in, and the write bit is set, with no immutable
    flag): an OS policy layer, not the file's permissions, refused it. Retrying will not help and
    neither will ``chmod``; the policy (sandbox profile, TCC grant, mount) has to change.
    """
    if not isinstance(exc, OSError) or exc.errno not in _WRITE_ERRNOS:
        return None
    if exc.errno == errno.EROFS:
        return READ_ONLY_FS
    raw = path if path is not None else getattr(exc, "filename", None)
    if raw is None or not hasattr(os, "getuid"):
        return PERMISSION_DENIED
    try:
        target = Path(os.fspath(raw)).expanduser()
    except TypeError:
        return PERMISSION_DENIED
    found, st, _ = _nearest_existing(target, stat_fn)
    if st is None:
        return PERMISSION_DENIED
    if getattr(st, "st_flags", 0) & _IMMUTABLE_FLAGS:
        return PERMISSION_DENIED
    uid = os.getuid() if uid is None else uid
    if gids is None:
        try:
            gids = {os.getgid(), *os.getgroups()}
        except OSError:
            gids = set()
    if exc.errno == errno.EPERM and stat.S_ISDIR(st.st_mode) and st.st_uid == uid and found == target:
        return POLICY_DENIED  # chmod/utime/mkdir on a dir we own: POSIX never says EPERM here
    return POLICY_DENIED if _mode_grants_write(st, uid, gids) else PERMISSION_DENIED


def describe(kind: Optional[str]) -> str:
    """One sentence an agent or operator can act on."""
    if kind == POLICY_DENIED:
        return ("the OS refused this write although the file permissions allow it (sandbox, TCC or "
                "MAC policy). This is a capability blocker: retrying or chmod will not help; the "
                "sandbox policy must allow this path, or the work must move to an allowed path")
    if kind == READ_ONLY_FS:
        return "the filesystem is mounted read-only"
    if kind == PERMISSION_DENIED:
        return "file ownership or mode bits refuse this write"
    return ""


def _store_path(home: Path | None) -> Path:
    if home is None:
        from hermes_constants import get_hermes_home
        home = get_hermes_home()
    return Path(home) / "state" / _STORE_NAME


def load_write_denials(home: Path | None = None) -> list[dict]:
    """Recorded denials, newest first. Missing or unreadable store reads as empty."""
    try:
        data = json.loads(_store_path(home).read_text(encoding="utf-8"))
        entries = data.get("entries") if isinstance(data, dict) else None
        rows = [e for e in (entries or {}).values() if isinstance(e, dict) and e.get("path")]
    except (OSError, ValueError):
        return []
    return sorted(rows, key=lambda e: e.get("last_seen", 0), reverse=True)


def _write_store(store: Path, entries: dict) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=store.parent, prefix=".tmp_write_denials_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "entries": entries}, fh, indent=1, sort_keys=True)
        os.replace(tmp, store)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def record_write_denial(exc: BaseException, *, source: str, path: str | os.PathLike | None = None,
                        home: Path | None = None, now: Optional[float] = None) -> Optional[str]:
    """Classify *exc*; for a write denial, upsert its persistent entry and return the kind.

    The entry survives log deduplication and process restarts. Repeats only bump ``count`` and
    ``last_seen`` (persisted at most every ``_PERSIST_EVERY_S`` per entry). Never raises.
    """
    try:
        kind = classify_write_error(exc, path)
        if kind is None:
            return None
        raw = path if path is not None else getattr(exc, "filename", None)
        target = os.fspath(raw) if raw is not None else "<unknown>"
        store = _store_path(home)
        key = f"{source}|{target}"
        ts = time.time() if now is None else now
        with _lock:
            memo = (str(store), key, kind)
            entries: dict = {}
            try:
                data = json.loads(store.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("entries"), dict):
                    entries = data["entries"]
            except (OSError, ValueError):
                pass
            entry = entries.get(key)
            if entry and ts - _last_persisted.get(memo, 0.0) < _PERSIST_EVERY_S and entry.get("kind") == kind:
                return kind
            entry = entry or {"path": target, "source": source, "first_seen": ts, "count": 0}
            entry.update(kind=kind, errno=getattr(exc, "errno", None), last_seen=ts,
                         count=int(entry.get("count", 0)) + 1, error=str(exc)[:300])
            entries[key] = entry
            if len(entries) > _MAX_ENTRIES:
                for old in sorted(entries, key=lambda k: entries[k].get("last_seen", 0))[:-_MAX_ENTRIES]:
                    entries.pop(old, None)
            _write_store(store, entries)
            _last_persisted[memo] = ts
        return kind
    except Exception as err:  # health: allow BLE001 -- diagnostics must never break the failing caller
        logger.debug("write_denials: could not record %s: %s", source, err)
        return classify_write_error(exc, path) if isinstance(exc, OSError) else None


def forget_write_denials(rows: list[dict], home: Path | None = None) -> None:
    """Drop entries (as returned by :func:`load_write_denials`) whose path is writable again."""
    drop = {f"{r.get('source')}|{r.get('path')}" for r in rows}
    store = _store_path(home)
    with _lock:
        try:
            data = json.loads(store.read_text(encoding="utf-8"))
            entries = {k: v for k, v in (data.get("entries") or {}).items() if k not in drop}
            _write_store(store, entries)
        except (OSError, ValueError, AttributeError) as err:
            logger.debug("write_denials: could not prune %s: %s", store, err)
        for memo in [m for m in _last_persisted if m[1] in drop]:
            _last_persisted.pop(memo, None)


def probe_write_access(path: str | os.PathLike) -> tuple[bool, Optional[str], str]:
    """Try a real write at *path* without changing it: ``(ok, kind, detail)``.

    A directory gets a temp file created and removed; an existing file is opened for append and
    closed (no bytes written); a missing path probes the nearest existing ancestor directory.
    A real write is the only test a sandbox answers truthfully: ``os.access`` and mode bits do not
    see every policy layer.
    """
    target = Path(os.fspath(path)).expanduser()
    found, st, _ = _nearest_existing(target, os.stat)
    if found is None:
        return False, None, "no existing ancestor"
    try:
        if stat.S_ISDIR(st.st_mode):
            fd, tmp = tempfile.mkstemp(dir=found, prefix=".hermes-write-probe-")
            os.close(fd)
            os.unlink(tmp)
        else:
            with open(found, "a", encoding="utf-8"):
                pass
    except OSError as exc:
        kind = classify_write_error(exc, found)
        return False, kind, f"{exc.strerror or exc} ({found})"
    return True, None, str(found)


def preflight_write_paths(paths: list[str], wrap: list[str], *, runner: Optional[Callable] = None,
                          python: Optional[str] = None) -> list[dict]:
    """Probe every path twice, here and under *wrap* (e.g. ``["sandbox-exec", "-f", "agents.sb"]``).

    Returns one row per path with ``now`` / ``wrapped`` results and ``breaks`` set when the path
    is writable today but would be refused under the candidate policy: the diff to read before
    switching hosts into a sandbox. The wrapped probe runs this module in a child process, so the
    candidate policy itself answers, not a reading of its rules.
    """
    import subprocess
    import sys
    runner = runner or (lambda argv: subprocess.run(argv, capture_output=True, text=True, timeout=60))
    argv = [*wrap, python or sys.executable, "-I", os.path.abspath(__file__), "probe", *paths]
    proc = runner(argv)
    try:
        wrapped = json.loads(proc.stdout or "[]")
    except ValueError:
        wrapped = []
    by_path = {row.get("path"): row for row in wrapped if isinstance(row, dict)}
    rows = []
    for p in paths:
        ok, kind, detail = probe_write_access(p)
        w = by_path.get(p) or {"ok": False, "kind": None,
                               "detail": f"wrapped probe failed (exit {getattr(proc, 'returncode', '?')})"}
        rows.append({"path": p, "now": {"ok": ok, "kind": kind, "detail": detail}, "wrapped": w,
                     "breaks": bool(ok and not w.get("ok"))})
    return rows


def _main(argv: list[str]) -> int:
    if len(argv) >= 1 and argv[0] == "probe":
        out = []
        for p in argv[1:]:
            ok, kind, detail = probe_write_access(p)
            out.append({"path": p, "ok": ok, "kind": kind, "detail": detail})
        print(json.dumps(out))
        return 0
    print("usage: write_denials.py probe PATH...", file=__import__("sys").stderr)
    return 2


if __name__ == "__main__":
    # Run as a file (``python -I write_denials.py probe ...``) inside the candidate sandbox, so the
    # probe needs nothing from the Hermes package to import.
    raise SystemExit(_main(__import__("sys").argv[1:]))
