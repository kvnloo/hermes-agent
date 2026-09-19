"""Regression test for #115483: dead stdio child past the proof deadline.

Premise: in ``_wait_for_lifecycle_event`` the stdio-no-keepalive branch
computes ``timeout = max(0.0, proof_at - now)``, which sticks at 0 once the
proof deadline passes, and the expired-proof check no-ops on a dead child
(``... and not self._stdio_children_dead()``) then ``continue``s. With the
child dead and no events ever firing, the supervisor spins on zero-timeout
``asyncio.wait`` wakes forever instead of reconnecting.

Fix contract (narrow): at expired ``proof_at`` with dead stdio children,
return ``"reconnect"`` (failing stale in-flight calls) instead of
``continue``.
"""
import asyncio

import pytest

from tools.mcp_tool import MCPServerTask
import tools.mcp_tool_server_run as run_mod


@pytest.mark.asyncio
async def test_expired_proof_with_dead_stdio_children_reconnects(monkeypatch):
    task = MCPServerTask("test-stdio-dead")
    # Stdio config: no URL, no keepalive_interval.
    task._config = {"command": "true"}
    task._session_proven = False
    task.session = object()
    task._stdio_children_dead = lambda: True
    failed = []
    task._fail_inflight_calls = lambda reason: failed.append(reason)
    # Expire the proof deadline immediately.
    monkeypatch.setattr("tools.mcp_tool._DEFAULT_KEEPALIVE_INTERVAL", 0.0)

    real_wait = asyncio.wait
    calls = {"n": 0}

    async def fake_wait(waiters, timeout=None, return_when=None):
        calls["n"] += 1
        if calls["n"] == 1:
            # Past the deadline the supervisor must wake immediately...
            assert timeout is not None and timeout <= 1.0, timeout
            # ...and reconnect instead of spinning: nothing completes here.
            return set(), set(waiters)
        # Pre-fix fallback: the loop spun, so shut it down to terminate.
        task._shutdown_event.set()
        return await real_wait(
            waiters, timeout=1.0,
            return_when=return_when or asyncio.FIRST_COMPLETED,
        )

    monkeypatch.setattr(run_mod.asyncio, "wait", fake_wait)
    reason = await asyncio.wait_for(task._wait_for_lifecycle_event(), timeout=10)
    assert reason == "reconnect", reason
    assert failed == ["reconnect"], failed
    assert calls["n"] == 1, "must reconnect on the first expired-proof wake, not spin"


@pytest.mark.asyncio
async def test_expired_proof_with_live_stdio_children_still_proves(monkeypatch):
    """Guard: the fix must not break the healthy path — a live child at the
    expired proof deadline marks the session proven and keeps serving."""
    task = MCPServerTask("test-stdio-live")
    task._config = {"command": "true"}
    task._session_proven = False
    task.session = object()
    task._stdio_children_dead = lambda: False
    monkeypatch.setattr("tools.mcp_tool._DEFAULT_KEEPALIVE_INTERVAL", 0.0)

    real_wait = asyncio.wait
    calls = {"n": 0}

    async def fake_wait(waiters, timeout=None, return_when=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return set(), set(waiters)
        task._shutdown_event.set()
        return await real_wait(
            waiters, timeout=1.0,
            return_when=return_when or asyncio.FIRST_COMPLETED,
        )

    monkeypatch.setattr(run_mod.asyncio, "wait", fake_wait)
    reason = await asyncio.wait_for(task._wait_for_lifecycle_event(), timeout=10)
    assert reason == "shutdown", reason
    assert task._session_proven is True, "live child past proof deadline proves the session"


@pytest.mark.asyncio
async def test_dead_child_smoke_no_zero_timeout_busy_spin(monkeypatch):
    """Integration-shaped smoke for #115483 (no GUI / no seat0).

    Spawn a real tracked stdio child, establish an unproven session, kill the
    child, cross the proof deadline, and assert:

    - exactly one reconnect transition
    - no repeated zero-timeout lifecycle waits (busy spin)
    - wall time stays bounded (no sustained spin)
    """
    import os
    import signal
    import subprocess
    import time as time_mod

    child = subprocess.Popen(["sleep", "120"])
    task = MCPServerTask("test-stdio-smoke")
    task._config = {"command": "sleep"}
    task._session_proven = False
    task.session = object()
    task._stdio_child_pids = [child.pid]
    failed = []
    task._fail_inflight_calls = lambda reason: failed.append(reason)
    monkeypatch.setattr("tools.mcp_tool._DEFAULT_KEEPALIVE_INTERVAL", 0.05)

    real_wait = asyncio.wait
    wait_stats = {"n": 0, "zero": 0, "timeouts": []}

    async def counting_wait(waiters, timeout=None, return_when=None):
        wait_stats["n"] += 1
        wait_stats["timeouts"].append(timeout)
        if timeout is not None and timeout == 0.0:
            wait_stats["zero"] += 1
        # After first wake past deadline with dead child, production must
        # return without spinning. Cap any residual spin.
        if wait_stats["n"] > 5:
            task._shutdown_event.set()
        return await real_wait(
            waiters,
            timeout=timeout,
            return_when=return_when or asyncio.FIRST_COMPLETED,
        )

    monkeypatch.setattr(run_mod.asyncio, "wait", counting_wait)

    t0 = time_mod.monotonic()
    # Let the proof deadline arm, then kill the child before it expires so
    # the expired-proof wake observes death.
    await asyncio.sleep(0.01)
    child.send_signal(signal.SIGKILL)
    child.wait(timeout=2)
    # Ensure psutil sees the pid as gone.
    await asyncio.sleep(0.02)

    reason = await asyncio.wait_for(task._wait_for_lifecycle_event(), timeout=5)
    elapsed = time_mod.monotonic() - t0

    assert reason == "reconnect", reason
    assert failed == ["reconnect"], failed
    # One reconnect path: must not thrash zero-timeout waits.
    assert wait_stats["zero"] <= 1, wait_stats
    assert wait_stats["n"] <= 3, wait_stats
    assert elapsed < 2.0, elapsed
    # Child must stay dead; no orphaned sleep left behind.
    assert child.poll() is not None
    try:
        os.kill(child.pid, 0)
        alive = True
    except OSError:
        alive = False
    assert alive is False
