"""Bounded, thread-local SQLite leases for hosted-room stores.

A lease keeps sqlite3's context-manager semantics, but close() rolls back
unfinished work and returns the physical connection for the next same-thread
borrow. SQLite still owns all cross-process locking and journal recovery.
"""
from __future__ import annotations

import atexit
import os
import sqlite3
import threading
import time
import weakref
from collections import OrderedDict
from pathlib import Path
from typing import Callable

_MAX_IDLE = 8


def _inode(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return stat.st_dev, stat.st_ino


class _Entry:
    def __init__(self, key: tuple, path: Path, connection: sqlite3.Connection) -> None:
        self.key, self.path, self.connection = key, path, connection
        self.inode = _inode(path)
        self.closed = False

    def dispose(self) -> None:
        if not self.closed:
            self.closed = True
            try:
                self.connection.close()
            except sqlite3.Error:
                # Never mask the original transaction failure during cleanup.
                pass


class _Lease:
    def __init__(self, pool: _Pool, entry: _Entry) -> None:
        self._pool, self._entry = pool, entry
        self._owner = threading.get_ident()
        self._closed = False

    def _check(self) -> None:
        if self._closed or self._entry.closed or self._pool.pid != os.getpid():
            raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
        if self._owner != threading.get_ident():
            raise sqlite3.ProgrammingError("SQLite connection lease belongs to another thread")

    def __getattr__(self, name: str):
        self._check()
        return getattr(self._entry.connection, name)

    def __enter__(self):
        self._check()
        self._entry.connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._check()
        return self._entry.connection.__exit__(exc_type, exc, tb)

    def close(self) -> None:
        if self._closed:
            return
        self._check()
        self._closed = True
        self._pool.release(self, self._entry)

    def __del__(self) -> None:
        if not getattr(self, "_closed", True):
            self._closed = True
            try:
                self._pool.release(self, self._entry)
            except Exception:
                pass


class _Pool:
    def __init__(self) -> None:
        self.pid = os.getpid()
        self.owner = threading.get_ident()
        self.closed = False
        self.idle: OrderedDict[tuple, _Entry] = OrderedDict()
        self.active: weakref.WeakSet[_Lease] = weakref.WeakSet()

    def acquire(
        self, path: Path, *, db_label: str, busy_timeout_ms: int,
        foreign_keys: bool, wal_lock_retries: int,
        initialize: Callable[[sqlite3.Connection], None] | None,
    ) -> _Lease:
        key = (str(path), db_label, busy_timeout_ms, foreign_keys, wal_lock_retries)
        entry = self.idle.pop(key, None)
        if entry is not None and (entry.inode is None or entry.inode != _inode(path)):
            entry.dispose()
            entry = None
        if entry is None:
            # Physical opens retain the canonical busy-timeout, WAL fallback
            # (including DELETE refusal), and first-opener lock retry gates.
            from hermes_cli.sqlite_util import open_db

            connection = open_db(
                path, db_label=db_label, busy_timeout_ms=busy_timeout_ms,
                foreign_keys=foreign_keys, wal_lock_retries=wal_lock_retries,
                check_same_thread=False, initialize=initialize)
            entry = _Entry(key, path, connection)
        else:
            try:
                entry.connection.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
                from hermes_state_wal import apply_wal_with_fallback

                # Journal mode is configuration-sensitive; do not assume the
                # previous lease's WAL/DELETE result is still valid.
                for attempt in range(wal_lock_retries):
                    try:
                        apply_wal_with_fallback(entry.connection, db_label=db_label)
                        break
                    except sqlite3.OperationalError as exc:
                        if str(exc).lower() != "database is locked" or attempt + 1 == wal_lock_retries:
                            raise
                        time.sleep(0.01 * (2**attempt))
                if foreign_keys:
                    entry.connection.execute("PRAGMA foreign_keys=ON")
                # Preserve cross-process schema readiness checks on each call.
                if initialize is not None:
                    initialize(entry.connection)
            except BaseException:
                entry.dispose()
                raise
        lease = _Lease(self, entry)
        self.active.add(lease)
        return lease

    def release(self, lease: _Lease, entry: _Entry) -> None:
        self.active.discard(lease)
        if entry.closed:
            return
        if self.closed or self.pid != os.getpid() or threading.get_ident() != self.owner:
            entry.dispose()
            return
        try:
            if entry.connection.in_transaction:
                entry.connection.rollback()
            if entry.inode is None or entry.inode != _inode(entry.path):
                entry.dispose()
                return
        except sqlite3.Error:
            entry.dispose()
            return
        previous = self.idle.pop(entry.key, None)
        if previous is not None:
            previous.dispose()
        self.idle[entry.key] = entry
        while len(self.idle) > _MAX_IDLE:
            _, victim = self.idle.popitem(last=False)
            victim.dispose()

    def close(self) -> None:
        self.closed = True
        for entry in self.idle.values():
            entry.dispose()
        self.idle.clear()
        for lease in tuple(self.active):
            lease._entry.dispose()


_thread_state = threading.local()
_registry: weakref.WeakSet[_Pool] = weakref.WeakSet()
_lock = threading.Lock()


def _pool() -> _Pool:
    pool = getattr(_thread_state, "pool", None)
    if pool is None or pool.closed or pool.pid != os.getpid():
        pool = _Pool()
        _thread_state.pool = pool
        with _lock:
            _registry.add(pool)
    return pool


def open_reused(
    path: Path | str, *, db_label: str, busy_timeout_ms: int = 10_000,
    foreign_keys: bool = False, wal_lock_retries: int = 1,
    initialize: Callable[[sqlite3.Connection], None] | None = None,
) -> _Lease:
    """Borrow a thread-owned connection. The caller must close the lease.

    The physical connection disables SQLite's thread check only to allow
    fork/exit cleanup of idle handles. Leases remain strictly thread-affine.
    """
    path = Path(os.path.abspath(os.fspath(path)))
    return _pool().acquire(
        path, db_label=db_label, busy_timeout_ms=busy_timeout_ms,
        foreign_keys=foreign_keys, wal_lock_retries=wal_lock_retries,
        initialize=initialize)


def close_all() -> None:
    """Dispose idle and active connections at shutdown or test cleanup."""
    with _lock:
        for pool in tuple(_registry):
            pool.close()


def _after_fork() -> None:
    # Inherited SQLite handles must never be borrowed by a child.
    global _thread_state, _registry, _lock
    for pool in tuple(_registry):
        pool.close()
    _thread_state = threading.local()
    _registry = weakref.WeakSet()
    _lock = threading.Lock()


atexit.register(close_all)
if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_after_fork)
