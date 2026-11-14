"""A monitor-gated (unchanged) cron fire must not leave its session row open."""
from __future__ import annotations

import sqlite3

from tests.cron.test_monitor_kind import _install_agent_stubs, _make_monitor_job, hermes_env  # noqa: F401


def _cron_rows(home):
    conn = sqlite3.connect(home / "state.db")
    try:
        return conn.execute(
            "SELECT id, ended_at, end_reason, message_count FROM sessions"
            " WHERE source = 'cron' ORDER BY started_at").fetchall()
    finally:
        conn.close()


def test_unchanged_monitor_fire_closes_its_session_row(hermes_env, monkeypatch):
    from cron.scheduler import run_job

    job = _make_monitor_job(hermes_env, "echo 'state A'\n")
    observed: dict = {}
    _install_agent_stubs(monkeypatch, observed)

    from cron.jobs import get_job

    assert run_job(job)[0] is True  # first fire: agent runs
    assert run_job(get_job(job["id"]))[0] is True  # unchanged: agent run suppressed
    assert observed["agent_runs"] == 1

    rows = _cron_rows(hermes_env)
    assert len(rows) == 2, rows
    gated = rows[1]
    assert gated[1] is not None, f"suppressed fire left its session row open: {gated}"
