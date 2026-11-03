"""Regression for NousResearch/hermes-agent#148237: missing psutil teardown."""

import os
import signal
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests._fixtures.live_system_guard import _live_system_guard


@pytest.mark.platforms("linux")
@pytest.mark.live_system_guard_bypass
def test_no_psutil_guard_allows_own_child_with_spaced_comm(monkeypatch):
    """The /proc stat comm field is one field even when it contains spaces."""
    child_code = (
        "import ctypes, signal\n"
        "assert ctypes.CDLL(None).prctl(15, b'hermes test kid', 0, 0, 0) == 0\n"
        "print('ready', flush=True)\n"
        "signal.pause()\n"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", child_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout is not None
        assert child.stdout.readline() == "ready\n"

        # Exercise the guard with psutil missing; leave raw os.kill available
        # for guaranteed cleanup even if the guarded signal is refused.
        request = SimpleNamespace(
            node=SimpleNamespace(get_closest_marker=lambda _name: None)
        )
        with monkeypatch.context() as scoped:
            scoped.setitem(sys.modules, "psutil", None)
            guard = _live_system_guard.__wrapped__(request, scoped)
            next(guard)
            try:
                with pytest.raises(RuntimeError, match="outside the test process subtree"):
                    os.kill(1, signal.SIGTERM)
                os.kill(child.pid, signal.SIGTERM)
            finally:
                guard.close()

        assert child.wait(timeout=5) == -signal.SIGTERM
    finally:
        if child.poll() is None:
            os.kill(child.pid, signal.SIGKILL)
            child.wait(timeout=5)
        if child.stdout is not None:
            child.stdout.close()
        if child.stderr is not None:
            child.stderr.close()
