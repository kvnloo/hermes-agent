"""Shared disk guard: one verdict decides whether new work may start (disk-full cascade).

On a host whose data volume filled, every layer failed its own write (transcript appends, turn
leases, admission settlement, runtime status, sessions.json, jobs.json, provider temp files) while
the gateway kept admitting turns, the kanban dispatcher kept spawning workers and cron kept firing.
These tests pin the guard those producers now consult before starting work.
"""
from __future__ import annotations

import logging

import pytest

from gateway import disk_status

pytestmark = pytest.mark.real_disk_guard

_GB = 1024  # MB


@pytest.fixture(autouse=True)
def _fresh_guard(monkeypatch):
    monkeypatch.delenv(disk_status.GUARD_DISABLE_ENV, raising=False)
    disk_status.reset_guard_cache()
    yield
    disk_status.reset_guard_cache()


def _fake_volumes(monkeypatch, table):
    """``table``: path -> (dev, free_mb, total_mb) or None (unreadable)."""
    calls = []

    def sample(path):
        calls.append(str(path))
        return table[str(path)]
    monkeypatch.setattr(disk_status, "_volume_sample", sample)
    return calls


def test_the_studio_shape_is_critical_and_refuses_new_work(monkeypatch):
    # 425 MiB free of 460 GiB: the measured state at 05:30 on the incident morning.
    _fake_volumes(monkeypatch, {"/h": (1, 425, 460 * _GB)})
    verdict = disk_status.storage_pressure(["/h"], now=0.0)
    assert verdict["pressure"] == "critical"
    refusal = disk_status.new_work_refusal(["/h"])
    assert refusal is not None and "425 MB free" in refusal


def test_ample_space_admits(monkeypatch):
    # 20 GiB free of 460 GiB (96% used): percent alone must not block.
    _fake_volumes(monkeypatch, {"/h": (1, 20 * _GB, 460 * _GB)})
    assert disk_status.storage_pressure(["/h"], now=0.0)["pressure"] == "ok"
    assert disk_status.new_work_refusal(["/h"]) is None


def test_worst_volume_wins_and_a_shared_volume_is_sampled_once(monkeypatch):
    # HERMES_HOME is fine but the temp root (provider spool files) sits on a full volume.
    _fake_volumes(monkeypatch, {"/home": (1, 50 * _GB, 460 * _GB), "/home2": (1, 50 * _GB, 460 * _GB),
                                "/tmp": (2, 100, 20 * _GB)})
    verdict = disk_status.storage_pressure(["/home", "/home2", "/tmp"], now=0.0)
    assert verdict["pressure"] == "critical"
    assert verdict["path"] == "/tmp"


def test_an_unreadable_volume_fails_open(monkeypatch):
    _fake_volumes(monkeypatch, {"/h": None})
    assert disk_status.storage_pressure(["/h"], now=0.0)["pressure"] == "unknown"
    assert disk_status.new_work_refusal(["/h"]) is None


def test_env_escape_hatch_disables_the_guard(monkeypatch):
    calls = _fake_volumes(monkeypatch, {"/h": (1, 10, 460 * _GB)})
    monkeypatch.setenv(disk_status.GUARD_DISABLE_ENV, "off")
    assert disk_status.new_work_refusal(["/h"]) is None
    assert calls == []


def test_samples_are_cached_briefly(monkeypatch):
    calls = _fake_volumes(monkeypatch, {"/h": (1, 10 * _GB, 460 * _GB)})
    disk_status.storage_pressure(["/h"], now=100.0)
    disk_status.storage_pressure(["/h"], now=102.0)
    assert len(calls) == 1
    disk_status.storage_pressure(["/h"], now=100.0 + disk_status._GUARD_TTL_SECONDS + 1)
    assert len(calls) == 2


def test_degraded_state_is_announced_once_and_recovery_once(monkeypatch, caplog):
    table = {"/h": (1, 100, 460 * _GB)}
    _fake_volumes(monkeypatch, table)
    caplog.set_level(logging.INFO, logger="gateway.disk_status")
    for tick in range(5):
        disk_status.storage_pressure(["/h"], now=tick * 10.0)
    table["/h"] = (1, 30 * _GB, 460 * _GB)
    disk_status.storage_pressure(["/h"], now=100.0)
    messages = [r.getMessage() for r in caplog.records if r.name == "gateway.disk_status"]
    assert sum("critical" in m for m in messages) == 1, messages
    assert sum("recovered" in m for m in messages) == 1, messages


def test_default_paths_cover_hermes_home_and_the_temp_root(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("TMPDIR", str(tmp_path / "t"))
    (tmp_path / "t").mkdir()
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", None)
    paths = [str(p) for p in disk_status._guard_paths()]
    assert str(tmp_path) in paths
    assert str(tmp_path / "t") in paths
