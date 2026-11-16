"""Pin the real terminal pre-exec guard dispatch to its 90-second ceiling.

The cap arithmetic tested in test_terminal_pre_guard_cap.py is reproduced in a
test helper. That helper stays green if terminal_tool stops using the clamp.
This test observes the deadline handed to the real guard boundary instead.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import agent.deadline as deadline
import tools.terminal_tool as terminal_module


def test_long_command_dispatches_pre_exec_guard_with_90s_ceiling(monkeypatch):
    """A 420s command must never lend its full timeout to the identity guard."""
    observed: list[tuple[float, str]] = []

    def plan_for_long_command(_command, **kwargs):
        assert kwargs["timeout"] == 420
        return SimpleNamespace(
            config={},
            env_type="local",
            effective_task_id="pre-guard-runtime-cap-test",
            cwd="/tmp",
            effective_timeout=420,
            promoted_from_foreground_timeout=None,
        )

    def capture_guard(_call, seconds, *, label):
        observed.append((seconds, label))
        # Simulate the wedged guard's deadline without sleeping 90 seconds.
        return SimpleNamespace(timed_out=True)

    monkeypatch.setattr(terminal_module, "_plan_execution", plan_for_long_command)
    monkeypatch.setattr(terminal_module, "_acquire_env", lambda *_a, **_k: object())
    monkeypatch.setattr(deadline, "run_bounded_sync", capture_guard)
    monkeypatch.setattr(
        terminal_module,
        "_run_approval_guards",
        lambda *_a, **_k: pytest.fail("guard timeout reached approval"),
    )
    monkeypatch.setattr(
        terminal_module,
        "_run_foreground",
        lambda *_a, **_k: pytest.fail("a timed-out guard executed the command"),
    )

    result = json.loads(terminal_module.terminal_tool("echo ok", timeout=420))

    # This observes terminal_tool's actual run_bounded_sync argument, not a
    # restatement of its arithmetic. The production 30s/90s defaults stay intact.
    assert observed == [(90, "terminal.pre-exec-guard")]
    assert result["status"] == "error"
    assert "within 90s" in result["error"]
