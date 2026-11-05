"""Remember a positive default currency probe by the files it read.

``venv_is_current()`` with no arguments runs on every cold launch and costs a PM
worker round-trip (YAML for every profile and plugin manifest). The worker records
every path the probe stats, lists or opens for reading; the caller answers True
without a worker only while each of those paths still stats the same (mtime_ns,
size, inode, mode, or still missing). Any change, a subprocess, an environment
difference or an unreadable record falls back to the full probe. Only True is
remembered: a stale venv always reaches the real check.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from contextlib import contextmanager
from pathlib import Path

_ENV_PREFIXES = ("HERMES_", "XDG_", "UV_")
_ENV_NAMES = ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA")
_recording: dict[str, object] | None = None
_poisoned = False
_hooked = False
_real_stat, _real_lstat = os.stat, os.lstat
_GIT_HEAD = "git-head:"


def cache_path(project_root: Path) -> Path:
    from pm.environments import install_state_dir

    return install_state_dir(project_root) / "probe-cache.json"


def key(project_root: Path, lockfile: Path, environment) -> str:
    """What the probe depends on beyond files: checkout, pins file, platform, worker environment."""
    env = sorted((k, v) for k, v in environment.items() if k.startswith(_ENV_PREFIXES) or k in _ENV_NAMES)
    data = json.dumps([str(Path(project_root).absolute()), str(lockfile), sys.platform, env])
    return hashlib.sha256(data.encode()).hexdigest()


def _fingerprint(path: str, listed: bool = True):
    """What a path is now, None when missing. A link adds its own inode, so retargeting it
    misses. A directory that was only probed (never listed) is just "a directory", so
    unrelated entries -- this cache's own file -- do not invalidate it."""
    try:
        st, link = _real_stat(path), _real_lstat(path)
    except OSError:
        return None
    link_id = link.st_ino if stat.S_ISLNK(link.st_mode) else 0
    if not listed and stat.S_ISDIR(st.st_mode):
        return ["dir", link_id]
    return [st.st_mtime_ns, st.st_size, st.st_ino, st.st_mode, link_id]


def _probed_only(value) -> bool:
    return isinstance(value, list) and value[:1] == ["dir"]


def _note(path, listed: bool = False) -> None:
    if _recording is None or isinstance(path, int):
        return
    try:
        name = os.path.abspath(os.fsdecode(path))
    except (TypeError, ValueError):
        return
    if name not in _recording or (listed and _probed_only(_recording[name])):
        _recording[name] = _fingerprint(name, listed)


def _audit(event: str, args) -> None:
    global _poisoned
    if _recording is None:
        return
    if event == "open":
        path, mode, flags = args
        writing = (any(c in mode for c in "wax+") if isinstance(mode, str)
                   else bool(flags & (os.O_WRONLY | os.O_RDWR | getattr(os, "O_APPEND", 0))))
        if writing:
            _poisoned = True  # A probe that writes is not a pure function of what it read.
        else:
            _note(path)
    elif event in ("os.listdir", "os.scandir"):
        _note(args[0] if args and args[0] is not None else ".", listed=True)
    elif event == "subprocess.Popen" and _is_head_query(args):
        _recording.setdefault(f"{_GIT_HEAD}{os.path.abspath(args[2] or '.')}", None)
    elif event in ("subprocess.Popen", "os.exec", "os.posix_spawn", "os.spawn", "os.system"):
        _poisoned = True


def _is_head_query(args) -> bool:
    """``git rev-parse HEAD`` (the version stamp's live-commit check) is re-asked, not poison."""
    executable, argv, cwd = args[0], args[1], args[2]
    return (isinstance(argv, (list, tuple)) and list(argv[1:]) == ["rev-parse", "HEAD"]
            and os.path.basename(os.fsdecode(executable or argv[0])) in ("git", "git.exe")
            and (cwd is None or isinstance(cwd, (str, os.PathLike))))


def _git_head(directory: str):
    import subprocess

    try:
        done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=directory, capture_output=True, text=True,
                              timeout=10, stdin=subprocess.DEVNULL, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return [done.returncode, done.stdout.strip()]


def _current(name: str, value):
    if name.startswith(_GIT_HEAD):
        return _git_head(name[len(_GIT_HEAD):])
    return _fingerprint(name, listed=not _probed_only(value))


@contextmanager
def recording():
    """Collect the read set of the enclosed probe into the yielded dict (left empty when poisoned)."""
    global _recording, _poisoned, _hooked
    if not _hooked:
        sys.addaudithook(_audit)
        _hooked = True
    real_stat, real_lstat = os.stat, os.lstat

    def probed_stat(path, *args, **kwargs):
        _note(path)
        return real_stat(path, *args, **kwargs)

    def probed_lstat(path, *args, **kwargs):
        _note(path)
        return real_lstat(path, *args, **kwargs)

    seen: dict[str, object] = {}
    result: dict[str, object] = {}
    _recording, _poisoned = seen, False
    os.stat, os.lstat = probed_stat, probed_lstat
    try:
        yield result
    finally:
        os.stat, os.lstat = real_stat, real_lstat
        _recording = None
        for name in [name for name in seen if name.startswith(_GIT_HEAD)]:
            seen[name] = _git_head(name[len(_GIT_HEAD):])
        if not _poisoned:
            # Code that ran the probe is an input too: an update that changes the check misses.
            for module in list(sys.modules.values()):
                name = getattr(module, "__file__", None)
                if isinstance(name, str):
                    seen.setdefault(os.path.abspath(name), _fingerprint(name))
            result.update(seen)


def remember(project_root: Path, probe_key: str, read_set: dict) -> None:
    if not read_set:
        return
    path = cache_path(project_root)
    temporary = path.with_name(f".{path.name}.{os.getpid()}")
    try:
        temporary.write_text(json.dumps({"key": probe_key, "paths": read_set}), encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)


def known_current(project_root: Path, probe_key: str) -> bool:
    try:
        record = json.loads(cache_path(project_root).read_text(encoding="utf-8"))
        if record["key"] != probe_key or not record["paths"]:
            return False
        return all(_current(name, value) == value for name, value in record["paths"].items())
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False
