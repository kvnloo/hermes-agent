"""Exclusive GPU lease for the 3080 Ti. Host CUDA, not Docker.

Not wired into Hunyuan yet. Call acquire/release around CUDA jobs.
"""
from __future__ import annotations

import os
from pathlib import Path

_DEFAULT = Path(os.environ.get("HERMES_GPU_LOCK") or "/tmp/hermes-gpu-3080ti.lock")


def acquire_gpu_lock(path: Path | None = None, *, blocking: bool = False) -> int | None:
    """Return an open fd holding LOCK_EX, or None if busy and non-blocking."""
    import fcntl

    lock_path = Path(path or _DEFAULT)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    flags = fcntl.LOCK_EX if blocking else (fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        fcntl.flock(fd, flags)
    except BlockingIOError:
        os.close(fd)
        return None
    os.write(fd, b"held\n")
    return fd


def release_gpu_lock(fd: int | None) -> None:
    if fd is None:
        return
    import fcntl

    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
