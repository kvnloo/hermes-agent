"""Idle-supervisor backoff tests: profiles with no rooms must not poll their store flat out.

On a multiplexed gateway every served profile owns a hosted-room driver thread, and each
tick re-reads the profile's store through the bindings provider (#143256). These tests pin
the exponential backoff that keeps idle profiles at a trickle, and its immediate reset on
wakeup or owned rooms.
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from itertools import pairwise
from pathlib import Path

import pytest

from tui_gateway.hosted_room_driver import HostedRoomBinding, HostedRoomRuntime


class _IdleRPC:
    """Never called: an empty roster never routes a turn; satisfies constructor choice."""


@contextmanager
def _idle_turn_lock(_profile: str):
    yield


BINDING = HostedRoomBinding(room_id="room-1", gateway_id="gateway-a", authority_epoch=1)


def _idle_runtime(tmp_path: Path, provider, **kwargs) -> HostedRoomRuntime:
    return HostedRoomRuntime(
        db_path=tmp_path / "state.db",
        rooms=provider,
        rpc=_IdleRPC(),
        turn_lock=_idle_turn_lock,
        poll_interval_seconds=kwargs.pop("poll_interval_seconds", 0.01),
        **kwargs,
    )


def _wait_for(predicate, *, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not reached before timeout")


def test_idle_runtime_backs_off_the_empty_bindings_recheck(tmp_path: Path):
    calls: list[float] = []

    def counting_provider():
        calls.append(time.monotonic())
        return []

    runtime = _idle_runtime(tmp_path, counting_provider, idle_poll_backoff_max_seconds=1.0)
    runtime.start()
    try:
        _wait_for(lambda: len(calls) >= 5, timeout=5.0)
    finally:
        assert runtime.stop(timeout=5.0)

    # A fixed 10ms poll keeps every gap near the base interval; the backed-off worker's
    # recheck gaps grow past it, so idle profiles stop re-reading their store flat out.
    gaps = [later - earlier for earlier, later in pairwise(calls)]
    assert gaps[-1] > 4 * 0.01
    assert all(later >= earlier - 0.005 for earlier, later in pairwise(gaps))


def test_idle_backoff_resumes_promptly_on_wakeup(tmp_path: Path):
    calls: list[float] = []

    def counting_provider():
        calls.append(time.monotonic())
        return []

    runtime = _idle_runtime(tmp_path, counting_provider, idle_poll_backoff_max_seconds=30.0)
    runtime.start()
    try:
        _wait_for(lambda: len(calls) >= 6, timeout=5.0)  # backed off to a 0.32s wait
        before = time.monotonic()
        runtime.wakeup()
        _wait_for(lambda: len(calls) >= 7, timeout=5.0)
        assert time.monotonic() - before < 0.15
    finally:
        assert runtime.stop(timeout=5.0)


def test_idle_poll_backoff_ceiling_must_not_undercut_the_base_interval(tmp_path: Path):
    with pytest.raises(ValueError, match="idle_poll_backoff_max_seconds"):
        HostedRoomRuntime(
            db_path=tmp_path / "state.db",
            rooms=[BINDING],
            rpc=_IdleRPC(),
            turn_lock=_idle_turn_lock,
            poll_interval_seconds=5.0,
            idle_poll_backoff_max_seconds=1.0,
        )

@pytest.mark.parametrize("failing_step", ("bindings", "maintenance"))
def test_failed_idle_cycle_retries_at_base_poll_interval(tmp_path: Path, monkeypatch, failing_step: str):
    # Exercise the actual 5s/60s defaults without making a test sleep for a minute.
    cycles = 0

    def rooms():
        nonlocal cycles
        cycles += 1
        if failing_step == "bindings" and cycles == 6:
            raise RuntimeError("temporary store failure")
        return ()

    def maintain():
        if failing_step == "maintenance" and cycles == 6:
            raise RuntimeError("temporary maintenance failure")

    runtime = HostedRoomRuntime(
        db_path=tmp_path / "state.db",
        rooms=rooms,
        rpc=_IdleRPC(),
        turn_lock=_idle_turn_lock,
        maintain=maintain,
    )
    runtime._thread = threading.current_thread()
    waits: list[float] = []

    def record_wait(seconds: float) -> bool:
        waits.append(seconds)
        if len(waits) == 6:
            runtime._stop.set()
        return False

    monkeypatch.setattr(runtime._wake, "wait", record_wait)
    runtime._worker_loop()

    # Empty polls back off, but a failed pass must retry after 5s, not the stale 60s.
    assert waits == [5.0, 10.0, 20.0, 40.0, 60.0, 5.0]
