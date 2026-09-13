"""Regression: ``cron.executions._owner_is_live`` must not fence a live owner
when the start-time fingerprint is missing or unreadable.

The execution-ledger docstring promises an attempt becomes ``unknown`` only
after its exact owner process is *proved* gone, and ``unknown`` is immutable.
The two ``None`` branches of ``_owner_is_live`` -- ``process_started_at IS
NULL`` at creation, and the live re-read of the fingerprint failing at
recovery -- previously treated an unconfirmable identity as "owner proved
dead" while a process still occupied the pid, fencing the row to the
immortal ``unknown`` state and irreversibly losing the owner's real outcome.

These tests assert the "proved gone" contract for the execution ledger:
an occupied pid with an unavailable fingerprint is *not* proof of death and
must not fence. The mismatch/dead-pid tests anchor endorsed behavior so the
fail-open fix cannot over-correct into dropping legitimate fences.

The delivery ledger (``cron.delivery_queue``) has a different, at-most-once
contract: losing a delivery is safer than duplicating a possibly-completed
send, so it keeps its own ``_owner_is_live`` that fences on an unconfirmable
identity. The final two tests verify that contract is preserved -- the
execution-ledger fix must not relax the delivery ledger.
"""

from __future__ import annotations

from unittest.mock import Mock


def _point_ledger(monkeypatch, tmp_path):
    import cron.executions as executions

    monkeypatch.setattr(
        executions, "EXECUTIONS_FILE", tmp_path / "cron" / "executions.db"
    )
    return executions


def _point_delivery(monkeypatch, tmp_path):
    import cron.delivery_queue as queue

    monkeypatch.setattr(queue, "DELIVERY_DB", tmp_path / "deliveries.db")
    monkeypatch.setattr(queue, "_ACTIVE_DELIVERIES", set())
    return queue


def _pretend_replacement_gateway(monkeypatch, executions, owner_pid):
    """Make *executions* view the already-recorded row as external and live."""
    monkeypatch.setattr(executions, "_PROCESS_ID", "replacement-gateway")
    monkeypatch.setattr(executions.os, "getpid", lambda: owner_pid + 7777)
    import gateway.status as status

    monkeypatch.setattr(status, "_pid_exists", lambda _pid: True, raising=False)


def test_live_external_owner_with_null_start_time_is_not_recovered(
    monkeypatch, tmp_path
):
    # process_started_at IS NULL at creation; the owner's pid is occupied at
    # recovery. No fingerprint exists to prove the owner is gone -> must NOT fence.
    executions = _point_ledger(monkeypatch, tmp_path)
    monkeypatch.setattr(executions, "_process_start_time", lambda _pid: None)
    record = executions.create_execution("live-owner-null-start", source="builtin")
    executions.mark_execution_running(record["id"])
    assert record["process_started_at"] is None
    owner_pid = record["pid"]

    _pretend_replacement_gateway(monkeypatch, executions, owner_pid)
    monkeypatch.setattr(executions, "_process_start_time", lambda _pid: None)

    changed = executions.recover_interrupted_executions()
    current = executions.get_execution(record["id"])
    assert changed == 0, f"expected 0 recoveries, got {changed}; owner is alive"
    assert current["status"] == "running", f"expected running, got {current['status']}"


def test_live_external_owner_with_unreadable_start_time_at_recovery(
    monkeypatch, tmp_path
):
    # Fingerprint was recorded fine, but at recovery the live pid's start time
    # can't be re-read. An unreadable fingerprint is an instrument failure, not
    # proof of owner death -> must NOT fence.
    executions = _point_ledger(monkeypatch, tmp_path)
    monkeypatch.setattr(executions, "_process_start_time", lambda _pid: 4242)
    record = executions.create_execution("live-owner-unreadable", source="builtin")
    executions.mark_execution_running(record["id"])
    assert record["process_started_at"] == 4242
    owner_pid = record["pid"]

    _pretend_replacement_gateway(monkeypatch, executions, owner_pid)
    monkeypatch.setattr(executions, "_process_start_time", lambda _pid: None)

    changed = executions.recover_interrupted_executions()
    current = executions.get_execution(record["id"])
    assert changed == 0, f"expected 0 recoveries, got {changed}; owner is alive"
    assert current["status"] == "running", f"expected running, got {current['status']}"


def test_pid_recycled_owner_is_correctly_fenced(monkeypatch, tmp_path):
    # Fingerprint present but mismatches: a *different* live process is at the
    # pid, so the original owner has exited (pid recycled) -> proved gone ->
    # fence is correct. Anchors endorsed behavior so the fail-open fix cannot
    # over-correct into dropping the PID-recycling guard.
    executions = _point_ledger(monkeypatch, tmp_path)
    monkeypatch.setattr(executions, "_process_start_time", lambda _pid: 4242)
    record = executions.create_execution("recycled-owner", source="builtin")
    executions.mark_execution_running(record["id"])
    assert record["process_started_at"] == 4242
    owner_pid = record["pid"]

    _pretend_replacement_gateway(monkeypatch, executions, owner_pid)
    monkeypatch.setattr(executions, "_process_start_time", lambda _pid: 9999)

    changed = executions.recover_interrupted_executions()
    current = executions.get_execution(record["id"])
    assert changed == 1, "mismatched fingerprint + live pid = proved gone -> should fence"
    assert current["status"] == "unknown"


def test_dead_pid_owner_is_still_fenced(monkeypatch, tmp_path):
    # The pid is unoccupied -> the owner is proved gone regardless of the
    # fingerprint. Fence. Guards against an over-broad fail-open regression.
    executions = _point_ledger(monkeypatch, tmp_path)
    record = executions.create_execution("dead-owner", source="builtin")
    executions.mark_execution_running(record["id"])
    owner_pid = record["pid"]

    monkeypatch.setattr(executions, "_PROCESS_ID", "replacement-gateway")
    monkeypatch.setattr(executions.os, "getpid", lambda: owner_pid + 7777)
    import gateway.status as status

    monkeypatch.setattr(status, "_pid_exists", lambda _pid: False, raising=False)

    changed = executions.recover_interrupted_executions()
    current = executions.get_execution(record["id"])
    assert changed == 1
    assert current["status"] == "unknown"


def test_delivery_queue_still_fences_uncertain_identity_owner(
    monkeypatch, tmp_path
):
    # The delivery ledger's contract is at-most-once: losing a delivery is
    # safer than duplicating a possibly-completed send. Even though the
    # execution ledger now fails open on a missing fingerprint, the delivery
    # ledger must keep fencing an unconfirmable owner to unknown and never
    # retry. Ensures the execution-ledger fix does not leak into delivery.
    queue = _point_delivery(monkeypatch, tmp_path)
    monkeypatch.setattr(queue, "_process_start_time", lambda _pid: None)
    queue.enqueue("exec-uncertain", {"id": "job-1"}, "brief")
    claimed = queue.claim_next()
    assert claimed is not None
    assert claimed["owner_started_at"] is None

    monkeypatch.setattr(queue, "_PROCESS_ID", "replacement-gateway")
    import gateway.status as status

    monkeypatch.setattr(status, "_pid_exists", lambda _pid: True, raising=False)

    assert queue.recover_abandoned() == 1
    row = queue.get_status("exec-uncertain")
    assert row is not None
    assert row["status"] == "unknown"
    send = Mock()
    assert queue.drain(send) == 0
    send.assert_not_called()


def test_delivery_queue_fences_unreadable_fingerprint_owner(monkeypatch, tmp_path):
    # Same at-most-once guarantee for the recovery-time None branch: a
    # fingerprint recorded at claim but unreadable at recovery must still fence.
    queue = _point_delivery(monkeypatch, tmp_path)
    monkeypatch.setattr(queue, "_process_start_time", lambda _pid: 4242)
    queue.enqueue("exec-unreadable", {"id": "job-2"}, "brief")
    claimed = queue.claim_next()
    assert claimed is not None
    assert claimed["owner_started_at"] == 4242

    monkeypatch.setattr(queue, "_PROCESS_ID", "replacement-gateway")
    import gateway.status as status

    monkeypatch.setattr(status, "_pid_exists", lambda _pid: True, raising=False)
    monkeypatch.setattr(queue, "_process_start_time", lambda _pid: None)

    assert queue.recover_abandoned() == 1
    row = queue.get_status("exec-unreadable")
    assert row is not None
    assert row["status"] == "unknown"
