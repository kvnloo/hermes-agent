"""Adoption must survive a real write lock held through one full busy timeout.

``tests/cron/test_restart_safe_worker.py`` covers the handoff contracts with stubbed
adoption and synthetic clock/boundary variables.  A field occurrence on Linux/WAL showed
the remaining gap: two jobs dispatched in the same tick, both workers reaching the
adoption ``UPDATE`` while a competing connection held the ledger's write lock past
``busy_timeout`` (5000 ms), and both dying before publishing their acknowledgement —
the occurrence is then skipped, not retried (see #135487).

These tests drive the real worker entry point against a real, isolated ledger file and a
second connection that owns the write lock, so the contention is genuine SQLite
contention rather than a mock.  ``requires_wal`` matches the runtime this reproduces:
with ``journal_mode=DELETE`` a writer blocks readers instead and the shape differs.

The ledger and profile home stay isolated: ``EXECUTIONS_FILE`` is repointed per test and
the payload carries a throwaway ``profile_home``, so nothing here touches a real ledger.

Schema initialisation is deliberately excluded from the contention: the schema and the claim
row are created through the production connection, and the factory adoption uses afterwards
carries no ``initialize`` hook — the isolation ``test_worker_adoption_commit_contention.py``
already uses. Merely pre-creating the table would not establish it, because
``executions._connect()`` passes ``initialize=_initialize_schema`` on every call; the traced
statements asserted below show that the contended statement itself is the adoption ``UPDATE``.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from unittest.mock import Mock

import pytest

BUSY_TIMEOUT_SECONDS = 5.0
"""The ledger's own ``busy_timeout``; the retry budget has to outlast one of these."""


@pytest.fixture
def isolated_ledger(tmp_path, monkeypatch):
    from cron import executions

    monkeypatch.setattr(executions, "EXECUTIONS_FILE", tmp_path / "executions.db")
    return executions


def _claim_with_fence(ledger, job_id: str) -> str:
    """A claimed row whose handoff fence is set, exactly as the dispatcher leaves it."""
    record = ledger.create_execution(job_id, source="builtin")
    assert ledger.mark_execution_handoff_pending(record["id"]) is not None
    assert ledger.get_execution(record["id"])["status"] == "claimed"
    return record["id"]


def _write_payload(tmp_path, execution_id: str, deadline: float):
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        json.dumps({
            "job": {"id": "job-busy", "execution_id": execution_id},
            "profile_home": str(tmp_path / "profile"),
            "adoption_deadline": deadline,
        }),
        encoding="utf-8",
    )
    return payload_path


class _HeldWriteLock:
    """A second connection that keeps the ledger's single writer slot occupied.

    ``BEGIN IMMEDIATE`` takes the write lock at once (so the caller can wait for it),
    and the lock is only released when :meth:`release` runs — which the tests call from
    the moment they have observed the first adoption attempt fail.
    """

    def __init__(self, ledger_path):
        self._path = ledger_path
        self._connection = None
        self.taken = threading.Event()
        self._release = threading.Event()
        self._thread = threading.Thread(target=self._hold, name="held-write-lock")

    def _hold(self):
        connection = sqlite3.connect(self._path, isolation_level=None, timeout=0.2)
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._connection = connection
            self.taken.set()
            self._release.wait(timeout=60.0)
            connection.execute("ROLLBACK")
        finally:
            connection.close()

    def __enter__(self):
        self._thread.start()
        assert self.taken.wait(timeout=30.0), "the write lock was never taken"
        return self

    def release(self):
        self._release.set()

    def __exit__(self, *_exc):
        self.release()
        self._thread.join(timeout=30.0)
        assert not self._thread.is_alive()
        return False


def _spying_adoption(ledger, attempts, observations):
    """Record every adoption attempt, and note whether it raised or was refused.

    The wrapper delegates to the real ``adopt_claimed_execution`` so the CAS predicate,
    the busy timeout and the row transition all stay genuine.
    """
    real = ledger.adopt_claimed_execution

    def attempt(execution_id):
        try:
            outcome = real(execution_id)
        except sqlite3.OperationalError as exc:
            attempts.append(f"busy:{exc}")
            raise
        attempts.append("adopted" if outcome is not None else "refused")
        return outcome

    observations["attempt"] = attempt
    return attempt


@pytest.mark.requires_wal
def test_adoption_retries_after_a_write_lock_held_through_one_busy_timeout(
    tmp_path, isolated_ledger, monkeypatch
):
    """The retry inside the handoff budget is what turns this contention into a run.

    Also asserts the two properties that keep the retry safe: no side effect and no
    acknowledgement before adoption has actually succeeded, and the existing CAS still
    refuses a later adoption of the same row (no replay, no second execution).
    """
    from cron import scheduler
    from hermes_cli.sqlite_util import open_db

    ledger_path = isolated_ledger.EXECUTIONS_FILE

    def connect(initialize=None):
        return open_db(
            ledger_path,
            db_label="cron/executions.db",
            synchronous_full=True,
            initialize=initialize,
        )

    # Claim row and schema as production creates them ...
    execution_id = _claim_with_fence(isolated_ledger, "job-busy")
    assert (
        sqlite3.connect(ledger_path).execute("PRAGMA journal_mode").fetchone()[0].lower()
        == "wal"
    )

    # ... then give adoption a factory with no ``initialize`` hook and trace what that
    # connection actually runs, so a BUSY cannot be attributed to schema work.
    traced: list[str] = []

    def traced_connect(initialize=None):
        connection = connect(initialize=None)
        connection.set_trace_callback(traced.append)
        return connection

    monkeypatch.setattr(isolated_ledger, "_connect", traced_connect)

    run = Mock(return_value=True)
    monkeypatch.setattr(scheduler, "run_one_job", run)

    attempts: list[str] = []
    before_adoption_succeeded: dict = {}
    observations: dict = {}
    first_attempt_failed = threading.Event()

    def spying(execution_id_):
        try:
            return observations["attempt"](execution_id_)
        except sqlite3.OperationalError as exc:
            # Snapshot the instant the contended attempt gives up: this is the evidence
            # that nothing ran and nothing was acknowledged while ownership was unclear,
            # plus the statement list that shows which write aborted.
            before_adoption_succeeded["ack"] = ack.exists()
            before_adoption_succeeded["runs"] = run.call_count
            before_adoption_succeeded["trace"] = [sql.strip() for sql in traced]
            before_adoption_succeeded["errorcode"] = getattr(exc, "sqlite_errorcode", None)
            first_attempt_failed.set()
            raise

    _spying_adoption(isolated_ledger, attempts, observations)
    monkeypatch.setattr(isolated_ledger, "adopt_claimed_execution", spying)

    ack = tmp_path / "exec-busy.ready"
    payload_path = _write_payload(tmp_path, execution_id, time.monotonic() + 30.0)

    with _HeldWriteLock(ledger_path) as lock:
        released = False
        result = {}

        def worker():
            # Capture instead of leaking: a thread exception would otherwise surface as
            # PytestUnhandledThreadExceptionWarning and hide the assertion that matters.
            try:
                result["outcome"] = scheduler._run_external_worker_payload(payload_path, ack)
            except BaseException as exc:  # re-raised below, in the test thread
                result["error"] = exc

        thread = threading.Thread(target=worker, name="worker-under-test")
        thread.start()
        try:
            assert first_attempt_failed.wait(timeout=4 * BUSY_TIMEOUT_SECONDS), (
                "no BUSY error observed — the held lock did not reach the adoption UPDATE",
                attempts,
            )
            # Release only now: after the failed attempt, inside the retry budget.
            lock.release()
            released = True
        finally:
            if not released:
                lock.release()
            thread.join(timeout=60.0)
        assert not thread.is_alive()

    assert "error" not in result, result.get("error")
    assert result["outcome"] is True
    assert before_adoption_succeeded["ack"] is False
    assert before_adoption_succeeded["runs"] == 0

    # Evidence for the contended statement itself: the traced connection ran
    # BEGIN -> the adoption UPDATE -> ROLLBACK, and the abort was SQLITE_BUSY. A BUSY raised
    # during schema work would show CREATE TABLE / table_info / ALTER TABLE here instead.
    contended = before_adoption_succeeded["trace"]
    assert before_adoption_succeeded["errorcode"] == sqlite3.SQLITE_BUSY, contended
    assert contended[-1].upper() == "ROLLBACK", contended
    assert contended[-2].startswith("UPDATE executions"), contended[-2]
    assert "handoff_pending=1" in contended[-2], contended[-2]
    assert not [
        sql for sql in contended
        if "CREATE TABLE" in sql or "table_info" in sql or "ALTER TABLE" in sql
    ], contended
    assert len(attempts) == 2 and attempts[0].startswith("busy:"), attempts
    assert attempts[1] == "adopted", attempts
    assert run.call_count == 1
    assert run.call_args.args[0]["id"] == "job-busy"
    assert ack.exists()
    # The existing CAS remains the only authority: the row is no longer claimable.
    assert isolated_ledger.adopt_claimed_execution(execution_id) is None
    assert isolated_ledger.get_execution(execution_id)["status"] in {"running", "completed"}


def test_adoption_fails_closed_when_the_budget_is_already_exhausted(
    tmp_path, isolated_ledger, monkeypatch
):
    """Same lock, no retry budget left: refuse, run nothing, leave the row for recovery.

    This is the failure mode the field occurrence actually hit; asserting both directions
    keeps the retry from quietly widening into "run anyway".
    """
    from cron import scheduler

    execution_id = _claim_with_fence(isolated_ledger, "job-busy")
    ledger_path = isolated_ledger.EXECUTIONS_FILE

    run = Mock(return_value=True)
    monkeypatch.setattr(scheduler, "run_one_job", run)

    attempts: list[str] = []
    observations: dict = {}
    monkeypatch.setattr(
        isolated_ledger,
        "adopt_claimed_execution",
        _spying_adoption(isolated_ledger, attempts, observations),
    )

    ack = tmp_path / "exec-busy.ready"
    # Deadline already elapsed: the first attempt still runs (legacy cold-start behavior),
    # but there is no room left for the five-second busy timeout of a second one.
    payload_path = _write_payload(tmp_path, execution_id, time.monotonic())

    with _HeldWriteLock(ledger_path):
        # Without room for a second attempt the incumbent behaviour is preserved: the
        # worker propagates the ledger error instead of improvising a run. The process
        # then exits non-zero before its acknowledgement — the field occurrence in #135487.
        with pytest.raises(sqlite3.OperationalError, match="database is locked"):
            scheduler._run_external_worker_payload(payload_path, ack)

    assert len(attempts) == 1 and attempts[0].startswith("busy:"), attempts
    assert run.call_count == 0
    assert not ack.exists()
    # Ownership stays with the durable claim, so dead-owner recovery can still adopt it.
    assert isolated_ledger.get_execution(execution_id)["status"] == "claimed"


def test_a_refused_cas_is_never_retried(isolated_ledger, monkeypatch):
    """A row that is not claimable must cost exactly one attempt.

    Retrying a refusal would replay work the CAS deliberately rejected.
    """
    from cron.scheduler_adoption import adopt_with_retry

    record = isolated_ledger.create_execution("job-refused", source="builtin")
    execution_id = record["id"]

    attempts: list[str] = []
    observations: dict = {}
    monkeypatch.setattr(
        isolated_ledger,
        "adopt_claimed_execution",
        _spying_adoption(isolated_ledger, attempts, observations),
    )

    assert adopt_with_retry(execution_id, time.monotonic() + 30.0) is None
    assert attempts == ["refused"]
