"""Self-PID signal-zero liveness probes must not require termination approval."""

import os

import pytest

from tools.approval import detect_dangerous_command


@pytest.mark.parametrize("template", [
    "kill -0 {pid}",
    "kill -s 0 {pid}",
    "kill -n 0 {pid}",
    "kill -0 {pid} >/dev/null",
    "kill -0 {pid}; kill 999999999",
])
def test_signal_zero_self_pid_does_not_require_approval(template):
    command = template.format(pid=os.getpid())
    assert detect_dangerous_command(command) == (False, None, None)


def test_zero_signal_probe_does_not_hide_terminating_self_kill():
    pid = os.getpid()
    dangerous, key, description = detect_dangerous_command(
        f"kill -0 {pid}; kill {pid}"
    )
    assert dangerous is True
    assert key == description == "kill own process (self-termination)"
