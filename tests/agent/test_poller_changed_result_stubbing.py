"""A poller's changing status must never be replaced by an identical-result stub.

Regression for the long `gh pr checks` results in jleechan2015's PR #152446.
"""

import json

from agent.tool_guardrails import (
    IDENTICAL_RESULT_STUB_MIN_CHARS,
    STALL_GUARD_IDENTICAL_CALL_THRESHOLD,
    ToolCallGuardrailController,
)


def _long_poll_result(status: str) -> str:
    return json.dumps({
        "exit_code": 0,
        "stdout": status + "\n" + "detail " * IDENTICAL_RESULT_STUB_MIN_CHARS,
    })


def test_changing_poller_results_remain_visible() -> None:
    controller = ToolCallGuardrailController()
    args = {"command": "gh pr checks 123"}
    results = [
        _long_poll_result("pending: 2 checks"),
        _long_poll_result("pending: 1 check"),
        _long_poll_result("pass: 5 checks"),
    ]

    observations = [
        controller.observe_call("terminal", args, result, tool_call_id=f"poll-{i}")
        for i, result in enumerate(results, 1)
    ]

    # Count polls by args for the warning, but never call a different status
    # byte-identical or hide the new terminal result behind a stale stub.
    assert len(results) == STALL_GUARD_IDENTICAL_CALL_THRESHOLD
    assert all(observation.stub is None for observation in observations)
    assert observations[-1].kind == "identical_call_streak"
    assert observations[-1].notice is not None


def test_identical_long_poller_result_still_stubs() -> None:
    controller = ToolCallGuardrailController()
    args = {"command": "gh pr checks 123"}
    result = _long_poll_result("pending: 2 checks")

    first = controller.observe_call("terminal", args, result, tool_call_id="original")
    second = controller.observe_call("terminal", args, result, tool_call_id="replay")

    assert first.stub is None
    assert second.stub is not None
    assert "tool_call_id original" in second.stub
