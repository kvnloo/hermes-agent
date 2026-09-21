"""A dead Kanban worker is booked the same way whichever process notices it.

``_recent_worker_exits`` is filled by ``os.waitpid`` and so only knows children of
the process running the sweep; a per-tick ``hermes kanban dispatch`` process finds it
empty. The worker's own exit trailer in its log is the durable witness the sweep reads
instead, and a tripped protocol-violation budget must hold the card until an operator
unblocks it.

The worker log is append-mode across re-runs, so the trailer carries a `` run=<run_id>``
stamp and ``_worker_log_exit_code`` scopes the read to the run being reclaimed: a
stale trailer from an earlier run surviving in the last 4000 bytes is rejected, and a
worker that died without its own trailer (OOM/SIGKILL) stays a plain crash instead of
being misbooked against that stale trailer.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc
from hermes_cli import kanban_db_dispatch as kbd
from hermes_cli.quiet_single_query import KANBAN_WORKER_EXIT_TRAILER, exit_single_query


@pytest.fixture
def kanban_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_KANBAN_CRASH_GRACE_SECONDS", "0")
    monkeypatch.setattr(kb, "_pid_alive", lambda _pid: False)
    kbd._recent_worker_exits.clear()
    kb.init_db()
    return home


def _dead_worker_with_log(conn, tid: str, pid: int, rc: int) -> None:
    """Claim ``tid`` for a worker that already exited ``rc`` and wrote its log — never reaped here.

    Writes the legacy UNSTAMPED trailer form, so a reclaim with a ``run_id`` accepts it
    via the mixed-version fallback.
    """
    host = kb._claimer_id().split(":", 1)[0]
    kb.claim_task(conn, tid, claimer=f"{host}:w{pid}")
    conn.execute(
        "UPDATE tasks SET worker_pid=?, worker_started_at=NULL, started_at=? WHERE id=?",
        (pid, int(time.time()) - 120, tid),
    )
    conn.commit()
    log = kb.worker_log_path(tid)
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"the model said something\n\nResume this session with:\n  hermes --resume x\n\n{KANBAN_WORKER_EXIT_TRAILER}{rc}\n")


def _claim_dead_worker(conn, tid: str, pid: int) -> int:
    """Claim ``tid`` for a never-reaped dead worker (``started_at = now - 120``); returns the run id."""
    host = kb._claimer_id().split(":", 1)[0]
    claimed = kb.claim_task(conn, tid, claimer=f"{host}:w{pid}")
    assert claimed is not None and claimed.current_run_id is not None, "claim did not open a run"
    conn.execute(
        "UPDATE tasks SET worker_pid=?, worker_started_at=NULL, started_at=? WHERE id=?",
        (pid, int(time.time()) - 120, tid),
    )
    conn.commit()
    return int(claimed.current_run_id)


def _append_stamped_trailer(tid: str, rc: int, run_id: int) -> None:
    """Append a run-stamped trailer (the form a fixed worker emits) to ``tid``'s worker log."""
    log = kb.worker_log_path(tid)
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(
            f"the model said something\n\nResume this session with:\n  hermes --resume x\n\n"
            f"{KANBAN_WORKER_EXIT_TRAILER}{rc} run={run_id}\n"
        )


@pytest.mark.parametrize(
    "rc, event, failure_counted",
    [(0, "protocol_violation", False), (kb.KANBAN_RATE_LIMIT_EXIT_CODE, "rate_limited", False)],
)
def test_fresh_process_sweep_books_the_logged_exit_code(kanban_home, rc, event, failure_counted):
    """Empty reap registry + exit trailer in the log: a clean exit is the protocol violation
    (marker, streak, no unified-budget hit) and a 75 is a rate-limit requeue — not a bare
    ``pid N not alive`` crash that counts a failure."""
    with kbc.connect() as conn:
        tid = kb.create_task(conn, title="t", assignee="a")
        _dead_worker_with_log(conn, tid, 70001, rc)

        kbd.detect_crashed_workers(conn)

        ev = conn.execute(
            "SELECT kind FROM task_events WHERE task_id=? ORDER BY id DESC LIMIT 1", (tid,)).fetchone()
        run = conn.execute(
            "SELECT outcome, error, metadata FROM task_runs WHERE task_id=? ORDER BY id DESC LIMIT 1",
            (tid,)).fetchone()
        task = kb.get_task(conn, tid)
        assert ev["kind"] == event
        assert "not alive" not in (run["error"] or "")
        assert task.status == "ready"
        assert task.consecutive_failures == (1 if failure_counted else 0)
        # The decoded rc lands in the run row so quota (75) vs crash stays tellable after
        # the fact even though the worker_output tail is trimmed (#113611).
        assert kb._json_dict(run["metadata"]).get("exit_code") == rc
        if rc == 0:
            assert kb._json_dict(run["metadata"]).get("protocol_violation") is True
            assert kbd._protocol_violation_streak(conn, tid) == 1
            assert KANBAN_WORKER_EXIT_TRAILER not in (run["error"] or "")
        else:
            assert run["outcome"] == "rate_limited"


def test_violation_budget_trip_holds_until_operator_unblock(kanban_home):
    """The third consecutive clean exit trips the violation budget and ``recompute_ready``
    must not promote the card back the same tick (``consecutive_failures`` is still below
    ``failure_limit``); ``unblock_task`` lifts the hold."""
    with kbc.connect() as conn:
        tid = kb.create_task(conn, title="loop", assignee="a")
        for i in range(kbd._PROTOCOL_VIOLATION_FAILURE_LIMIT):
            _dead_worker_with_log(conn, tid, 71000 + i, 0)
            kbd.detect_crashed_workers(conn)
            kb.recompute_ready(conn, failure_limit=10)
        task = kb.get_task(conn, tid)
        assert task.status == "blocked"
        assert task.consecutive_failures < 10

        kb.unblock_task(conn, tid)
        assert kb.get_task(conn, tid).status == "ready"
        kb.recompute_ready(conn, failure_limit=10)
        assert kb.get_task(conn, tid).status == "ready"


def test_plain_budget_trip_still_auto_recovers(kanban_home):
    """A unified-budget trip carries no ``sticky`` marker, so the two recovery paths on main
    survive: raising the dispatcher ``failure_limit`` past the counter promotes the card, and
    ``assign_task`` to a fresh profile (counter reset by design) promotes it too."""
    with kbc.connect() as conn:
        tids = [kb.create_task(conn, title=t, assignee="a") for t in ("raise-limit", "reassign")]
        for tid in tids:
            for i in range(2):
                kbd._record_task_failure(
                    conn, tid, error=f"boom{i}", outcome="crashed", failure_limit=2,
                    release_claim=False, end_run=False,
                )
            assert kb.get_task(conn, tid).status == "blocked"
        assert kb.recompute_ready(conn, failure_limit=2) == 0

        assert kb.recompute_ready(conn, failure_limit=5) == 2
        assert kb.get_task(conn, tids[0]).status == "ready"

        for i in range(2):
            kbd._record_task_failure(
                conn, tids[1], error=f"again{i}", outcome="crashed", failure_limit=2,
                release_claim=False, end_run=False,
            )
        assert kb.get_task(conn, tids[1]).status == "blocked"
        kb.assign_task(conn, tids[1], "other-profile")
        assert kb.recompute_ready(conn, failure_limit=2) == 1
        assert kb.get_task(conn, tids[1]).status == "ready"


def test_exit_single_query_writes_trailer_only_for_kanban_workers(monkeypatch, capsys):
    monkeypatch.delenv("HERMES_KANBAN_TASK", raising=False)
    with pytest.raises(SystemExit) as exc:
        exit_single_query(1)
    assert exc.value.code == 1
    assert KANBAN_WORKER_EXIT_TRAILER not in capsys.readouterr().err

    monkeypatch.setenv("HERMES_KANBAN_TASK", "t_1")
    with pytest.raises(SystemExit) as exc:
        exit_single_query(kb.KANBAN_RATE_LIMIT_EXIT_CODE)
    assert exc.value.code == kb.KANBAN_RATE_LIMIT_EXIT_CODE
    assert f"{KANBAN_WORKER_EXIT_TRAILER}{kb.KANBAN_RATE_LIMIT_EXIT_CODE}" in capsys.readouterr().err


def test_exit_single_query_stamps_trailer_with_run_id(monkeypatch, capsys):
    """A worker with ``HERMES_KANBAN_RUN_ID`` in its env stamps the trailer so a later
    reclaim by a different process can tell this run's trailer apart from a prior run's."""
    monkeypatch.setenv("HERMES_KANBAN_TASK", "t_1")
    monkeypatch.setenv("HERMES_KANBAN_RUN_ID", "7")
    with pytest.raises(SystemExit) as exc:
        exit_single_query(kb.KANBAN_RATE_LIMIT_EXIT_CODE)
    assert exc.value.code == kb.KANBAN_RATE_LIMIT_EXIT_CODE
    assert (
        f"{KANBAN_WORKER_EXIT_TRAILER}{kb.KANBAN_RATE_LIMIT_EXIT_CODE} run=7"
        in capsys.readouterr().err
    )


def test_worker_log_exit_code_scopes_trailer_to_current_run(kanban_home):
    """``_worker_log_exit_code`` only honours a trailer stamped for the run being reclaimed.

    A stale stamped trailer from an earlier run is rejected so a trailless death (OOM/SIGKILL)
    falls through to a plain crash; an unstamped trailer is a mixed-version fallback; a legacy
    caller with no ``run_id`` keeps the last-trailer-in-window behaviour.
    """
    with kbc.connect() as conn:
        tid = kb.create_task(conn, title="scope", assignee="a")
        log = kb.worker_log_path(tid)
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"{KANBAN_WORKER_EXIT_TRAILER}75 run=41\n")
            f.write(f"{KANBAN_WORKER_EXIT_TRAILER}0 run=42\n")

        # Legacy caller (no run_id): last trailer in the tail window wins.
        assert kbd._worker_log_exit_code(tid) == 0
        # The current run's own stamped trailer is honoured.
        assert kbd._worker_log_exit_code(tid, run_id=42) == 0
        # A different run with no trailer of its own is NOT misbooked against run 42's stamp.
        assert kbd._worker_log_exit_code(tid, run_id=43) is None

        # An old-version worker's unstamped trailer (mixed fleet) is a fallback for any run,
        # and as the newest trailer it wins over the older stamped ones.
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"{KANBAN_WORKER_EXIT_TRAILER}{kb.KANBAN_TERMINAL_PROVIDER_EXIT_CODE}\n")
        fallback_rc = kb.KANBAN_TERMINAL_PROVIDER_EXIT_CODE
        assert kbd._worker_log_exit_code(tid, run_id=99) == fallback_rc
        assert kbd._worker_log_exit_code(tid) == fallback_rc


def test_stale_trailer_from_prior_run_misclassifies_trailless_death(kanban_home):
    """A prior run's stamped trailer still in the tail window must not book a trailless
    death (OOM/SIGKILL) on the current run as ``rate_limited``.

    Two per-tick dispatcher sweeps of the same task (in-process reap registry cleared each
    tick, modelling a fresh ``hermes kanban dispatch`` process):
      * run 1 exits rate-limited and logs a stamped trailer for its OWN run -> requeued
        without counting a failure (correct);
      * run 2 dies without writing any trailer; run 1's trailer is still inside the last
        4000 bytes, so without run-scoping the stale trailer misbooks run 2 as
        ``rate_limited`` and ``consecutive_failures`` stays 0. With run-scoping run 2 is a
        plain crash and the failure counter increments.
    """
    with kbc.connect() as conn:
        tid = kb.create_task(conn, title="oom", assignee="a")

        # Run 1: a rate-limited worker that wrote its run-stamped trailer.
        run1 = _claim_dead_worker(conn, tid, 70201)
        _append_stamped_trailer(tid, kb.KANBAN_RATE_LIMIT_EXIT_CODE, run1)
        kbd._recent_worker_exits.clear()
        kbd.detect_crashed_workers(conn)
        task_after_run1 = kb.get_task(conn, tid)
        run1_row = conn.execute(
            "SELECT outcome FROM task_runs WHERE task_id=? ORDER BY id DESC LIMIT 1", (tid,),
        ).fetchone()
        assert task_after_run1.status == "ready"
        assert task_after_run1.consecutive_failures == 0
        assert run1_row["outcome"] == "rate_limited"

        # Run 2: a fresh per-tick dispatcher reclaims a dead worker it did not spawn; the
        # worker OOMs before writing its own trailer, leaving run 1's stamped trailer as the
        # only one in the tail window.
        run2 = _claim_dead_worker(conn, tid, 70202)
        assert run2 != run1
        tail = kb.read_worker_log(tid, tail_bytes=4000) or ""
        assert f"run={run1}" in tail  # run 1's stale trailer survives in the window
        assert f"run={run2}" not in tail  # run 2 wrote no trailer of its own
        kbd._recent_worker_exits.clear()
        kbd.detect_crashed_workers(conn)

        task_after_run2 = kb.get_task(conn, tid)
        run2_row = conn.execute(
            "SELECT outcome FROM task_runs WHERE task_id=? ORDER BY id DESC LIMIT 1", (tid,),
        ).fetchone()
        assert task_after_run2.consecutive_failures == 1
        assert run2_row["outcome"] == "crashed"
