"""Bounded process-local JSON disk memo, with no copy on cache hits.

The cache key is (Path, st_mtime_ns, st_size). Hits return the same ordinary
dict/list objects as json.load; the consuming registry/catalog paths only read
them. Explicit writers invalidate the memo after atomic replacement.

guard_json_disk_memo_mutations() is a test-only check: it reparses snapshots
as recursively read-only dict/list subclasses, so a newly introduced mutating
consumer fails at the mutation site. Production returns unmodified JSON types.
An external in-place rewrite preserving both file metadata fields is not
detectable by this key.
"""

from __future__ import annotations

import json
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
    """Build read-only JSON containers, preserving isinstance(..., dict/list)."""
    if isinstance(value, dict):
        return _ReadOnlyDict({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return _ReadOnlyList([_freeze_json(item) for item in value])
    return value


_read_lock = Lock()
_mutation_guard = False


@lru_cache(maxsize=4)
def _parse_version(path: Path, mtime_ns: int, size: int) -> Any:
    """Read once per resident file signature; called under _read_lock."""
    with path.open(encoding="utf-8-sig") as stream:
        result = json.load(stream)
    return _freeze_json(result) if _mutation_guard else result


def read_json_disk_memo(path: Path) -> Any:
    """Return a shared JSON object on a hit, without copying any rows."""
    path = Path(path)
    version = path.stat()
    with _read_lock:
        return _parse_version(path, version.st_mtime_ns, version.st_size)


def clear_json_disk_memo() -> None:
    """Drop every resident version after an explicit writer/invalidation."""
    with _read_lock:
        _parse_version.cache_clear()


def json_disk_memo_parse_count() -> int:
    """Cache misses (including failed parse attempts) since the last clear."""
    with _read_lock:
        return _parse_version.cache_info().misses


@contextmanager
def guard_json_disk_memo_mutations() -> Iterator[None]:
    """Make nested cache mutations raise during behavior tests.

    Enter with a cold registry state; each guarded parse uses read-only
    dict/list subclasses. Clear the guarded entries on exit so they never
    escape into normal later reads. The production path never freezes/copies.
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
