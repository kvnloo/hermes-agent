"""Regression: a rejected kanban_schedule lifecycle handoff cannot replay indefinitely.

The goal-mode scheduling gate rejects this call without mutating the card. A worker
using the default attended guardrail policy must stop before its fourth replay.
"""
from __future__ import annotations

import json

from agent.tool_guardrails import ToolCallGuardrailConfig, ToolCallGuardrailController


def test_goal_mode_schedule_rejection_blocks_fourth_identical_call():
    config = ToolCallGuardrailConfig.from_mapping({}, platform="cli")
    assert config.hard_stop_enabled is False  # real attended-worker default
    guard = ToolCallGuardrailController(config)
    args = {"task_id": "t_goal_mode", "reason": "wait for external review"}
    rejected = json.dumps({"error": "goal_mode tasks cannot be scheduled"})

    for _ in range(3):
        assert guard.before_call("kanban_schedule", args).allows_execution
        guard.after_call("kanban_schedule", args, rejected)

    stopped = guard.before_call("kanban_schedule", args)
    assert stopped.action == "block"
    assert stopped.should_halt
    assert stopped.count == 3
    assert guard.halt_decision is stopped
