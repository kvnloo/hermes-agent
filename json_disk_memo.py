"""Process-local, bounded memo for JSON disk snapshots.

Each successful parse is identified by (path, st_mtime_ns, st_size).
Callers can mutate nested dictionaries and lists, so every read returns a deep
copy rather than handing out the cached object. This preserves JSON's normal
dict/list shapes at O(items) copy cost per hit. A cache entry holds at most
one of four recently used versions; parsing is single-flight in this process.

Explicit writers and invalidators clear the memo, including for rewrites with
an unchanged stat signature. External same-signature in-place rewrites are
not detectable from this key alone.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any


_read_lock = Lock()


@lru_cache(maxsize=4)
def _parse_version(path: Path, mtime_ns: int, size: int) -> Any:
    """Read a file version. The stat fields distinguish cache keys."""
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def read_json_disk_memo(path: Path) -> Any:
    """Return an independent mutable JSON value; propagate read/parse errors.

    The stat lookup is O(1) in JSON item count. A hit avoids file read and
    JSON decoding, but still deep-copies O(items) to preserve caller isolation.
    """
    path = Path(path)
    stat = path.stat()
    with _read_lock:
        snapshot = _parse_version(path, stat.st_mtime_ns, stat.st_size)
    return copy.deepcopy(snapshot)


def clear_json_disk_memo() -> None:
    """Discard cached versions after an explicit write or invalidation."""
    with _read_lock:
        _parse_version.cache_clear()


def json_disk_memo_parse_count() -> int:
    """Number of successful cache misses since the last clear (benchmark aid)."""
    with _read_lock:
        return _parse_version.cache_info().misses
