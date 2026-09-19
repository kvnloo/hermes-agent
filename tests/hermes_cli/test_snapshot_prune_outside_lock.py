"""active_session_registry_snapshot must not probe liveness under lock (#115578).

_prune_dead() runs one psutil round-trip per entry (~7 ms on Windows for
the POSIX zombie probe). Holding the exclusive, unfair registry file lock
across that starves concurrent pollers once a handful of leases exist.
The snapshot reads raw entries under the lock, prunes after release, and
writes back only the lease ids proven dead — so a lease created between
the snapshot and the write-back survives.
"""

import json
import os

from hermes_cli import active_sessions


DEAD_PID = 2 ** 30  # never a live pid; _pid_exists() is False, no signal sent


def _entry(lease_id, session_id, pid):
    return {"lease_id": lease_id, "session_id": session_id, "pid": pid}


def _seed(home, entries):
    state_path = home / "runtime" / "active_sessions.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    active_sessions._write_entries(state_path, entries)
    return state_path


def _read_all(state_path):
    return json.loads(state_path.read_text(encoding="utf-8"))["entries"]


class _TrackingFileLock(active_sessions._FileLock):
    held = 0

    def __enter__(self):
        result = super().__enter__()
        type(self).held += 1
        return result

    def __exit__(self, *exc):
        type(self).held -= 1
        return super().__exit__(*exc)


def test_prune_dead_runs_after_lock_released(tmp_path, monkeypatch):
    home = tmp_path / "home"
    _seed(home, [_entry("live-1", "s-live", os.getpid()), _entry("dead-1", "s-dead", DEAD_PID)])

    monkeypatch.setattr(active_sessions, "_FileLock", _TrackingFileLock)
    _TrackingFileLock.held = 0
    real_prune = active_sessions._prune_dead
    seen = {}

    def spy_prune(entries, **kwargs):
        seen["held_during_prune"] = _TrackingFileLock.held
        return real_prune(entries, **kwargs)

    monkeypatch.setattr(active_sessions, "_prune_dead", spy_prune)

    live = active_sessions.active_session_registry_snapshot(registry_home=home)

    assert seen["held_during_prune"] == 0
    assert [e["lease_id"] for e in live] == ["live-1"]


def test_snapshot_still_prunes_and_persists(tmp_path):
    home = tmp_path / "home"
    state_path = _seed(home, [_entry("live-1", "s-live", os.getpid()), _entry("dead-1", "s-dead", DEAD_PID)])

    live = active_sessions.active_session_registry_snapshot(registry_home=home)

    assert [e["lease_id"] for e in live] == ["live-1"]
    assert [e["lease_id"] for e in _read_all(state_path)] == ["live-1"]


def test_concurrent_lease_survives_prune_writeback(tmp_path, monkeypatch):
    home = tmp_path / "home"
    state_path = _seed(home, [_entry("live-1", "s-live", os.getpid()), _entry("dead-1", "s-dead", DEAD_PID)])
    newcomer = _entry("new-1", "s-new", os.getpid())

    real_prune = active_sessions._prune_dead

    def spy_prune(entries, **kwargs):
        # A concurrent acquirer lands between our snapshot and our write-back.
        current = active_sessions._read_entries(state_path, strict=True)
        current.append(dict(newcomer))
        active_sessions._write_entries(state_path, current)
        return real_prune(entries, **kwargs)

    monkeypatch.setattr(active_sessions, "_prune_dead", spy_prune)

    live = active_sessions.active_session_registry_snapshot(registry_home=home)

    assert [e["lease_id"] for e in live] == ["live-1"]
    assert sorted(e["lease_id"] for e in _read_all(state_path)) == ["live-1", "new-1"]



def test_concurrent_same_lease_update_survives_stale_prune_writeback(tmp_path, monkeypatch):
    """Critical race (#115578 adversarial): A snapshots lease X as dead; B renews
    the SAME lease_id with a live pid; A's stale write-back must not delete B."""
    home = tmp_path / "home"
    state_path = _seed(home, [
        _entry("live-1", "s-live", os.getpid()),
        _entry("x-1", "s-x", DEAD_PID),
    ])
    renewed = {
        "lease_id": "x-1",
        "session_id": "s-x",
        "pid": os.getpid(),
        "updated_at": 9_999_999.0,
        "process_start_time": 1.0,
    }

    real_prune = active_sessions._prune_dead

    def spy_prune(entries, **kwargs):
        current = active_sessions._read_entries(state_path, strict=True)
        rewritten = []
        for entry in current:
            if str(entry.get("lease_id") or "") == "x-1":
                rewritten.append(dict(renewed))
            else:
                rewritten.append(entry)
        active_sessions._write_entries(state_path, rewritten)
        return real_prune(entries, **kwargs)

    monkeypatch.setattr(active_sessions, "_prune_dead", spy_prune)

    live = active_sessions.active_session_registry_snapshot(registry_home=home)

    # Returned snapshot is A's view (x-1 looked dead); persisted registry must
    # keep B's renewal.
    assert [e["lease_id"] for e in live] == ["live-1"]
    persisted = {e["lease_id"]: e for e in _read_all(state_path)}
    assert set(persisted) == {"live-1", "x-1"}
    assert persisted["x-1"]["pid"] == os.getpid()
    assert persisted["x-1"]["updated_at"] == 9_999_999.0


def test_snapshot_lock_metrics_stay_bounded_with_many_leases(tmp_path, monkeypatch):
    """~12 leases: expensive prune work outside lock; no multi-second lock hold."""
    import time as time_mod

    home = tmp_path / "home"
    entries = [_entry(f"live-{i}", f"s-{i}", os.getpid()) for i in range(10)]
    entries.append(_entry("dead-a", "s-dead-a", DEAD_PID))
    entries.append(_entry("dead-b", "s-dead-b", DEAD_PID))
    _seed(home, entries)

    hold_samples = []
    wait_samples = []

    class _TimedLock(active_sessions._FileLock):
        def __enter__(self):
            wait_t0 = time_mod.monotonic()
            result = super().__enter__()
            wait_samples.append(time_mod.monotonic() - wait_t0)
            self._hold_t0 = time_mod.monotonic()
            return result

        def __exit__(self, *exc):
            hold_samples.append(time_mod.monotonic() - self._hold_t0)
            return super().__exit__(*exc)

    monkeypatch.setattr(active_sessions, "_FileLock", _TimedLock)

    # Inject artificial expensive work into prune to prove it is outside lock.
    real_prune = active_sessions._prune_dead

    def slow_prune(entries, **kwargs):
        time_mod.sleep(0.05)
        return real_prune(entries, **kwargs)

    monkeypatch.setattr(active_sessions, "_prune_dead", slow_prune)

    live = active_sessions.active_session_registry_snapshot(registry_home=home)

    assert len(live) == 10
    assert hold_samples, hold_samples
    assert max(hold_samples) < 0.05, hold_samples  # prune sleep must not be in hold
    assert max(wait_samples) < 1.0, wait_samples
