"""Retry behaviour of ``adopt_claimed_execution`` under transient lock contention.

Regression for #135487: ``cron/executions.db`` queues ``synchronous=FULL``
commits during batch-fire ticks, so an external restart-safe worker whose adopt
hit the 5 s busy timeout died with ``sqlite3.OperationalError: database is
locked`` and the whole dispatch was lost before the acknowledgement was written.

These tests pin:

1. Transient ``database is locked`` errors are retried with backoff and the
   adoption succeeds instead of killing the dispatch.
2. ``rowcount == 0`` (another winner, or the claim is gone) returns ``None``
   without retrying.
3. Non-contention errors (e.g. ``no such table``) surface immediately.
"""

import sqlite3

import pytest

import cron.executions as ex


class _FakeCursor:
    def __init__(self, rowcount, row=None):
        self.rowcount = rowcount
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConn:
    def __init__(self, script):
        self._script = list(script) if script is not None else []
        self._fetch = None

    def execute(self, *a, **k):
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def fetchone(self):
        return self._fetch

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch(monkeypatch, script, fetch_row=(("id", "x"),)):
    conns = []
    # One stack shared by every connection: each retry opens a fresh connection.
    queue = list(script)

    class _SharedConn(_FakeConn):
        def __init__(self):
            super().__init__(None)
            self._script = queue  # shared, not a copy

    def fake_transaction():
        conns.append(_SharedConn())
        conns[-1]._fetch = fetch_row
        return conns[-1]

    monkeypatch.setattr(ex, "_transaction", fake_transaction)
    monkeypatch.setattr(ex, "_emit_execution_state", lambda *a, **k: None)
    sleeps = []
    monkeypatch.setattr(ex.time, "sleep", lambda s: sleeps.append(s))
    return conns, sleeps


def test_adopt_retries_transient_lock_and_succeeds(monkeypatch):
    locked = sqlite3.OperationalError("database is locked")
    script = [locked, locked, _FakeCursor(1), _FakeCursor(0, {"id": "x"})]
    conns, sleeps = _patch(monkeypatch, script)
    rec = ex.adopt_claimed_execution("deadbeef")
    assert rec is not None, "adopt must still succeed after transient lock contention"
    assert len(conns) == 3, "3 attempts (2x locked, 1x success)"
    assert sleeps == [0.25, 0.5], "backoff 0.25 s then 0.5 s"


def test_adopt_lost_race_returns_none_without_retry(monkeypatch):
    script = [_FakeCursor(0), _FakeCursor(0, {"id": "x"})]
    conns, sleeps = _patch(monkeypatch, script)
    assert ex.adopt_claimed_execution("deadbeef") is None
    assert len(conns) == 1, "rowcount 0 = another winner, no retry"
    assert sleeps == []


def test_adopt_non_contention_error_raises_immediately(monkeypatch):
    broken = sqlite3.OperationalError("no such table: executions")
    script = [broken]
    conns, _sleeps = _patch(monkeypatch, script)
    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        ex.adopt_claimed_execution("deadbeef")
    assert len(conns) == 1, "schema errors are not retried"


def test_adopt_recovers_after_four_busy_timeouts_within_grace(monkeypatch):
    """A writer releasing at about 24 seconds must not lose the occurrence.

    Each injected error represents one exhausted five-second SQLite busy timeout.
    The timing check is arithmetic; there is no wall-clock delay or live database.
    Regression for mrwick1's skipped cron runs (#135487).
    """
    locked = sqlite3.OperationalError("database is locked")
    script = [locked] * 4 + [_FakeCursor(1), _FakeCursor(0, {"id": "x"})]
    conns, sleeps = _patch(monkeypatch, script)
    record = ex.adopt_claimed_execution("deadbeef")
    assert record == {"id": "x"}
    assert len(conns) == 5
    assert sleeps == [0.25, 0.5, 1.0, 2.0]
    # Fifth attempt starts at 23.75s and can adopt after a 24s lock release.
    assert 4 * 5.0 + sum(sleeps) < 24.0 < ex.HANDOFF_ADOPTION_GRACE_SECONDS


def test_adopt_gives_up_after_budget_and_raises(monkeypatch):
    locked = sqlite3.OperationalError("database is locked")
    script = [locked] * ex._ADOPT_LOCK_RETRY_ATTEMPTS
    conns, sleeps = _patch(monkeypatch, script)
    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        ex.adopt_claimed_execution("deadbeef")
    assert len(conns) == ex._ADOPT_LOCK_RETRY_ATTEMPTS
    assert sleeps == [0.25, 0.5, 1.0, 2.0], "backoff capped at 2.0 s"
    # The budget from adoption entry: busy (5 x 5 s) + sleeps < 30 s.
    busy_budget = ex._ADOPT_LOCK_RETRY_ATTEMPTS * 5.0
    assert busy_budget + sum(sleeps) < ex.HANDOFF_ADOPTION_GRACE_SECONDS


def test_lock_classifier(monkeypatch):
    assert ex._is_lock_contention(sqlite3.OperationalError("database is locked"))
    assert ex._is_lock_contention(sqlite3.OperationalError("database is busy"))
    assert not ex._is_lock_contention(
        sqlite3.OperationalError("database disk image is malformed")
    )
    assert not ex._is_lock_contention(ValueError("database is locked"))
