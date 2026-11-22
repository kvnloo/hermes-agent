"""Cron defers (does not dispatch) a due job while the disk guard reads critical.

Before: the scheduler kept dispatching into a full volume and logged
"not dispatched: execution creation failed: disk I/O error" plus "Failed to record interrupted run".
"""
from __future__ import annotations

from concurrent.futures import Future
from unittest.mock import MagicMock, patch

import pytest

import cron.jobs as jobs_mod
from gateway import disk_status


@pytest.fixture
def cron_store(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    (hermes_home / "cron").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setattr(jobs_mod, "HERMES_DIR", hermes_home)
    monkeypatch.setattr(jobs_mod, "CRON_DIR", hermes_home / "cron")
    monkeypatch.setattr(jobs_mod, "JOBS_FILE", hermes_home / "cron" / "jobs.json")
    monkeypatch.setattr(jobs_mod, "OUTPUT_DIR", hermes_home / "cron" / "output")
    return hermes_home


class _Pool:
    def __init__(self):
        self.submitted = 0

    def submit(self, fn, *a, **k):
        # Run inline so the scheduler's release-in-finally runs and no in-flight claim leaks.
        self.submitted += 1
        fut: Future = Future()
        fut.set_result(fn(*a, **k))
        return fut


def _critical(monkeypatch):
    monkeypatch.setattr(disk_status, "new_work_refusal", lambda *a, **k: "disk critical: 100 MB free")


def test_due_job_is_deferred_before_any_execution_row(cron_store, monkeypatch):
    from cron import scheduler as sched
    _critical(monkeypatch)
    job = jobs_mod.create_job(prompt="tick", schedule="every 60m")
    pool = _Pool()
    create = MagicMock(return_value={"id": "e1"})
    with patch.object(sched, "create_execution", create):
        assert sched._submit_with_guard(dict(job), pool, lambda j: None) is None  # type: ignore[arg-type]
    assert not create.called
    assert pool.submitted == 0
    assert job["id"] not in sched.get_running_job_ids()


def test_one_shot_claim_is_released_so_it_fires_after_recovery(cron_store, monkeypatch):
    from cron import scheduler as sched
    _critical(monkeypatch)
    job = jobs_mod.create_job(prompt="remind me", schedule="in 30m")
    jobs = jobs_mod.load_jobs()
    for j in jobs:
        if j["id"] == job["id"]:
            j["run_claim"] = {"at": "2026-11-21T10:00:00+00:00", "by": "test:1"}
    jobs_mod.save_jobs(jobs)
    pool = _Pool()
    with patch.object(sched, "create_execution", MagicMock(return_value={"id": "e1"})):
        assert sched._submit_with_guard(dict(job), pool, lambda j: None) is None  # type: ignore[arg-type]
    assert pool.submitted == 0
    reloaded = next(j for j in jobs_mod.load_jobs() if j["id"] == job["id"])
    assert reloaded.get("run_claim") is None


def test_healthy_disk_dispatches(cron_store, monkeypatch):
    from cron import scheduler as sched
    monkeypatch.setattr(disk_status, "new_work_refusal", lambda *a, **k: None)
    job = jobs_mod.create_job(prompt="tick", schedule="every 60m")
    pool = _Pool()
    with patch.object(sched, "create_execution", MagicMock(return_value={"id": "e1"})), \
            patch.object(sched, "note_cron_execution", MagicMock()):
        assert sched._submit_with_guard(dict(job), pool, lambda j: None) is not None  # type: ignore[arg-type]
    assert pool.submitted == 1
