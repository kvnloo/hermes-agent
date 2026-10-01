"""#108480: cron recovery must not fence a live owner whose start-time fingerprint is missing.

A real child interpreter owns an execution row and its delivery row in a temporary
profile's SQLite ledgers; real PID probing stays active. Only the OS start-time read
is faulted: in the child before it claims (fingerprint never recorded), or in the
recovering parent (fingerprint unreadable now). A dead owner and a recycled PID
(known fingerprint mismatch) must still be fenced.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_OWNER = """
import json, sys
from cron import executions, delivery_queue
import gateway.status
mode = sys.argv[1]
if mode in ('recorded', 'dead'):
    gateway.status.get_process_start_time = lambda pid: None
row = executions.create_execution('live-job', source='builtin')
executions.mark_execution_running(row['id'])
delivery_queue.enqueue(row['id'], {'id': 'live-job'}, 'result')
delivery_queue.claim_next()
print(json.dumps(row), flush=True)
if mode == 'dead':
    sys.exit(0)  # owner exits without recording an outcome
sys.stdin.read(1)
finished = executions.finish_execution(row['id'], success=True)
delivered = delivery_queue._finish(row['id'], error=None)
print(json.dumps({'execution': finished, 'delivered': delivered}), flush=True)
"""


@pytest.fixture
def ledgers(tmp_path, monkeypatch):
    from cron import delivery_queue, executions

    home = tmp_path / "home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(executions, "EXECUTIONS_FILE", None)
    monkeypatch.setattr(delivery_queue, "DELIVERY_DB", None)
    return dict(os.environ, HERMES_HOME=str(home))


def _spawn_owner(env, mode):
    repo = Path(__file__).resolve().parents[2]
    owner = subprocess.Popen(
        [sys.executable, "-c", _OWNER, mode], cwd=repo, env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    line = owner.stdout.readline()
    assert line, owner.stderr.read()
    return owner, json.loads(line)


def _recover():
    from cron import delivery_queue, executions

    return executions.recover_interrupted_executions(), delivery_queue.recover_abandoned()


@pytest.mark.parametrize("missing", ["recorded", "current"])
def test_live_owner_without_fingerprint_finishes_both_ledgers(ledgers, monkeypatch, missing):
    from cron import delivery_queue
    import gateway.status

    owner, row = _spawn_owner(ledgers, missing)
    try:
        assert owner.poll() is None and gateway.status._pid_exists(owner.pid)
        if missing == "recorded":
            assert row["process_started_at"] is None
        else:
            assert row["process_started_at"] is not None
            monkeypatch.setattr(gateway.status, "get_process_start_time", lambda pid: None)
        recovered = _recover()
        output, error = owner.communicate("x", timeout=30)
        assert owner.returncode == 0, error
        outcome = json.loads(output)
        assert recovered == (0, 0), f"live owner fenced: {outcome}"
        assert outcome["execution"]["status"] == "completed"
        assert outcome["delivered"] is True
        assert delivery_queue.get_status(row["id"])["status"] == "delivered"
    finally:
        if owner.poll() is None:
            owner.communicate("x", timeout=30)


def test_dead_owner_without_recorded_fingerprint_is_still_fenced(ledgers):
    from cron import delivery_queue, executions

    owner, row = _spawn_owner(ledgers, "dead")
    owner.communicate(timeout=30)
    assert row["process_started_at"] is None
    assert _recover() == (1, 1)
    assert executions.get_execution(row["id"])["status"] == "unknown"
    assert delivery_queue.get_status(row["id"])["status"] == "unknown"


def test_recycled_pid_with_known_mismatch_is_still_fenced(ledgers):
    from cron import delivery_queue, executions
    from gateway.status import START_TIME_DRIFT_TOLERANCE

    owner, row = _spawn_owner(ledgers, "current")
    try:
        assert row["process_started_at"] is not None
        # The row now names an earlier incarnation of this PID: a known mismatch beyond drift.
        stale = int(row["process_started_at"]) + 50 * START_TIME_DRIFT_TOLERANCE
        with executions._transaction() as conn:
            conn.execute("UPDATE executions SET process_started_at=? WHERE id=?", (stale, row["id"]))
        with delivery_queue._transaction() as conn:
            conn.execute("UPDATE deliveries SET owner_started_at=? WHERE execution_id=?", (stale, row["id"]))
        assert _recover() == (1, 1)
        assert executions.get_execution(row["id"])["status"] == "unknown"
        assert delivery_queue.get_status(row["id"])["status"] == "unknown"
    finally:
        if owner.poll() is None:
            owner.communicate("x", timeout=30)
