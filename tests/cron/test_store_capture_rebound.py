"""Regression for NousResearch/hermes-agent#151865: captured cron-store ContextVar."""

import json
from unittest.mock import patch

from cron import jobs, scheduler, scheduler_tick


def test_tick_rebinds_an_inherited_shadow_store(tmp_path, monkeypatch, caplog):
    """An admitted tick writes the same home's jobs.json as its tick lock, even if
    an unrelated staging context left a shadow-store override on this thread."""
    real_home = tmp_path / "real"
    shadow_home = tmp_path / "shadow"
    real_home.mkdir()
    shadow_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(real_home))
    monkeypatch.setattr(scheduler, "_hermes_home", None)

    jobs.save_jobs([{"id": "real-before"}], replace=True)
    real_file = real_home / "cron" / "jobs.json"
    with jobs.use_cron_store(shadow_home):
        jobs.save_jobs([{"id": "shadow-sentinel"}], replace=True)
    shadow_file = shadow_home / "cron" / "jobs.json"
    shadow_before = shadow_file.read_bytes()

    def scan_and_persist():
        # This is the real jobs.json save API at the scheduler's due-scan seam.
        jobs.save_jobs([{"id": "real-after-tick"}], replace=True)
        return []

    # Simulate an un-unwound use_cron_store from a profile-distribution stage.
    token = jobs._cron_store_override.set(
        jobs._CronStorePaths.for_dir(shadow_home / "cron"))
    try:
        with patch.object(scheduler, "_should_yield_tick_to_fresh_gateway", return_value=None), \
             patch.object(scheduler_tick, "_pre_dispatch_housekeeping"), \
             patch.object(scheduler, "_maybe_run_worktree_maintenance"), \
             patch.object(scheduler, "get_due_jobs", side_effect=scan_and_persist), \
             patch.object(scheduler, "_sweep_stale_inflight_for_tick"), \
             patch.object(scheduler, "_sweep_mcp_orphans"), \
             patch.object(jobs.store_health, "recheck_idle"):
            assert scheduler.tick(verbose=False) == 0
        # Do not destroy a caller's scope; the tick must restore it on return.
        assert jobs._current_cron_store().cron_dir == shadow_home / "cron"
    finally:
        jobs._cron_store_override.reset(token)

    assert [job["id"] for job in json.loads(real_file.read_text(encoding="utf-8"))["jobs"]] == [
        "real-after-tick"
    ]
    assert shadow_file.read_bytes() == shadow_before
    assert "CRON-STORE-REBOUND-AT-SEAM seam=tick" in caplog.text
