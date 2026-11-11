"""Bounded process-local, read-only JSON cache keyed by file identity and version.

Warm hits return the same recursively read-only dict/list subclasses without
copying rows. These retain isinstance(value, dict/list) for existing consumers.
Each miss checks the open descriptor and path both before and after reading;
an external replacement or rewrite observed during a read is retried. This
cannot detect a same-inode in-place rewrite which deliberately preserves all
four metadata fields, or make an external writer's updates transactional.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, Iterator


class _ReadOnlyDict(dict):
    def _reject(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("shared JSON disk cache is read-only")

    __setitem__ = __delitem__ = __ior__ = _reject
    clear = pop = popitem = setdefault = update = _reject


class _ReadOnlyList(list):
    def _reject(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("shared JSON disk cache is read-only")

    __setitem__ = __delitem__ = __iadd__ = __imul__ = _reject
    append = extend = insert = pop = remove = clear = reverse = sort = _reject


def _freeze_json(value: Any) -> Any:
    """Freeze a newly parsed JSON tree once; preserve dict/list isinstance."""
    if isinstance(value, dict):
        return _ReadOnlyDict({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return _ReadOnlyList([_freeze_json(item) for item in value])
    return value


def _file_version(metadata: os.stat_result) -> tuple[int, int, int, int]:
    return (metadata.st_dev, metadata.st_ino, metadata.st_mtime_ns, metadata.st_size)


class _FileChangedDuringRead(Exception):
    """A file descriptor or pathname no longer names the sampled generation."""


_read_lock = Lock()
_mutation_guard = False
_MAX_READ_ATTEMPTS = 4


@lru_cache(maxsize=4)
def _parse_version(path: Path, dev: int, ino: int, mtime_ns: int, size: int) -> Any:
    """Decode a stable file version; only successful decodes enter the LRU."""
    expected = (dev, ino, mtime_ns, size)
    with path.open(encoding="utf-8-sig") as stream:
        fd = stream.fileno()
        if _file_version(os.fstat(fd)) != expected:
            raise _FileChangedDuringRead
        try:
            source = stream.read()
        except UnicodeError as exc:
            if _file_version(os.fstat(fd)) != expected:
                raise _FileChangedDuringRead from exc
            raise
        if _file_version(os.fstat(fd)) != expected:
            raise _FileChangedDuringRead
    try:
        parsed = json.loads(source)
    except ValueError as exc:
        if _file_version(path.stat()) != expected:
            raise _FileChangedDuringRead from exc
        raise
    if _file_version(path.stat()) != expected:
        raise _FileChangedDuringRead
    return _freeze_json(parsed)


def read_json_disk_memo(path: Path) -> Any:
    """Read a stable generation and return a shared production read-only tree.

    All stat, open, parse and final stat checks are serialized with local
    clear_json_disk_memo callers. An external process is detected by matching
    both descriptor and pathname metadata; it does not share this lock.
    """
    path = Path(path)
    with _read_lock:
        for _attempt in range(_MAX_READ_ATTEMPTS):
            try:
                before = _file_version(path.stat())
            except FileNotFoundError:
                # Prevent delete/recreate from resurrecting an old signature.
                _parse_version.cache_clear()
                raise
            try:
                result = _parse_version(path, *before)
            except (_FileChangedDuringRead, FileNotFoundError):
                continue
            try:
                after = _file_version(path.stat())
            except FileNotFoundError:
                _parse_version.cache_clear()
                raise
            if after == before:
                return result
        raise OSError(f"JSON disk cache changed during repeated reads: {path}")


def clear_json_disk_memo() -> None:
    """Discard resident generations after a local write or invalidation."""
    with _read_lock:
        _parse_version.cache_clear()


def json_disk_memo_parse_count() -> int:
    """Number of LRU misses, including failed attempts, since last clear."""
    with _read_lock:
        return _parse_version.cache_info().misses


@contextmanager
def guard_json_disk_memo_mutations() -> Iterator[None]:
    """Legacy test helper; production now has the same mutation protection.

    Clear on entry/exit to isolate the test's parse accounting. This no longer
    changes the type or mutability of objects returned by normal reads.
    """
    global _mutation_guard
    with _read_lock:
        if _mutation_guard:
            raise RuntimeError("JSON disk memo mutation guard is already active")
        _mutation_guard = True
        _parse_version.cache_clear()
    try:
        yield
    finally:
        with _read_lock:
            _parse_version.cache_clear()
            _mutation_guard = False
