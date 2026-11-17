"""A due cron job must not fire while `hermes update` holds the install.

``tick()`` advances ``next_run_at`` BEFORE dispatch, and the code swap happens after that, so a job
firing in that window runs against a tree whose source has moved but whose venv/env has not. The
failure presents as an ImportError/ModuleNotFoundError naming a symbol that IS present on disk, or
a dead interpreter — and for a weekly job the next real run is a week away.

The gate returns BEFORE ``get_due_jobs()``, so deferring mutates nothing: no ``next_run_at``
advance, no execution row, no failure streak. The assertions are behaviour contracts, never
snapshots of message text.
"""

import json
import os
from pathlib import Path

import pytest

from cron import scheduler_preflight


@pytest.fixture
def hermes_home(tmp_path, monkeypatch):
    """Isolate HERMES_HOME (root) and the profile-level default root."""
    root = tmp_path / ".hermes"
    (root / "cron").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(root))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return root


def _write_marker(path: Path, pid: int) -> None:
    import time

    path.write_text(f"{pid}\n{int(time.time())}\n", encoding="utf-8")


def test_live_marker_defers_and_a_dead_one_never_wedges(hermes_home):
    """The two halves of the contract in one place: defer while live, never block when stale."""
    marker = hermes_home / ".hermes-update-in-progress"

    _write_marker(marker, 999_999_999)  # crashed updater
    assert scheduler_preflight.update_in_progress() is False
    assert not marker.exists(), "a dead-pid marker must be reaped, not honoured forever"

    _write_marker(marker, os.getpid())
    assert scheduler_preflight.update_in_progress() is True


def test_profile_gateway_sees_the_root_marker(tmp_path, monkeypatch):
    """A CLIENT PROFILE gateway must still see an update.

    ``hermes update`` writes the marker at the ROOT Hermes home, but a profile gateway runs with
    ``HERMES_HOME=<root>/profiles/<name>``. Probing only the process home silently no-ops for
    every client profile — exactly the case this gate exists for.
    """
    root = tmp_path / ".hermes"
    profile_home = root / "profiles" / "sample-client"
    profile_home.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(profile_home))

    _write_marker(root / ".hermes-update-in-progress", os.getpid())
    assert scheduler_preflight.update_in_progress() is True


def test_deferring_leaves_the_job_store_untouched(hermes_home):
    """The outcome contract: no dispatch, and the schedule is not consumed.

    A deferred job must fire on a later tick, so ``next_run_at`` has to be byte-identical.
    """
    import cron.jobs as jobs
    import cron.scheduler as scheduler

    jobs.create_job(name="weekly-report", prompt="do the thing", schedule="0 7 * * 1")
    before = json.loads((hermes_home / "cron" / "jobs.json").read_text())["jobs"]

    _write_marker(hermes_home / ".hermes-update-in-progress", os.getpid())
    fired = scheduler.tick(verbose=False, adapters=[], loop=None, sync=True)

    after = json.loads((hermes_home / "cron" / "jobs.json").read_text())["jobs"]
    assert fired == 0
    assert [j.get("next_run_at") for j in after] == [j.get("next_run_at") for j in before]


def test_update_begins_during_due_scan_defers_without_spending_slot(hermes_home, monkeypatch):
    """An update arriving between the first fence check and due scan must not consume a fire."""
    from datetime import datetime, timedelta, timezone

    from cron import jobs, scheduler

    job = jobs.create_job(name="hourly-report", prompt="report", schedule="every 1h")
    due_at = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    with jobs._jobs_lock():
        records = jobs.load_jobs()
        next(j for j in records if j["id"] == job["id"])["next_run_at"] = due_at
        jobs.save_jobs(records)

    before = jobs.get_job(job["id"])["next_run_at"]
    get_due_jobs = scheduler.get_due_jobs
    scanned = []

    def update_during_due_scan():
        due = get_due_jobs()
        scanned.extend(j["id"] for j in due)
        _write_marker(hermes_home / ".hermes-update-in-progress", os.getpid())
        return due

    monkeypatch.setattr(scheduler, "get_due_jobs", update_during_due_scan)
    submitted = []

    def capture_submit(job, _pool, _process):
        submitted.append(job["id"])
        return None

    monkeypatch.setattr(scheduler, "_get_parallel_pool", lambda *_args: object())
    monkeypatch.setattr(scheduler, "_submit_with_guard", capture_submit)

    assert scheduler.tick(verbose=False, adapters=[], loop=None, sync=True) == 0
    assert job["id"] in scanned  # A real occurrence was due when the update began.
    assert submitted == []
    assert jobs.get_job(job["id"])["next_run_at"] == before
