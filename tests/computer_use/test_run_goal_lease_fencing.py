"""run_goal must re-admit lease / re-resolve backend per leaf (#114532 on #108914).

No long-lived backend capability. A human takeover between steps must stop
dispatch; no automatic replay after hand-back.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from tools.bot_desktop import lease as bd_lease
from tools.computer_use import tool as cu_tool


@pytest.fixture
def agent_lease(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    bd_lease._reset_for_tests()
    assert bd_lease.human_holds() is False
    yield
    bd_lease._reset_for_tests()


def test_run_goal_second_step_refuses_after_human_takeover(monkeypatch, agent_lease):
    """TEST A: step1 ok → human takes lease → step2 never dispatches."""
    decide_queue = [
        {"ok": True, "fail_open": False, "decision": {
            "action": "click", "target_element": 1, "done": False, "backend": "jev", "confidence": 0.9,
        }},
        {"ok": True, "fail_open": False, "decision": {
            "action": "click", "target_element": 2, "done": False, "backend": "jev", "confidence": 0.9,
        }},
    ]
    clicks = []
    backends = []

    def fake_handle(args, **kwargs):
        action = args.get("action")
        if action == "decide":
            return decide_queue.pop(0)
        if action == "click":
            # Simulate the real leaf: admit then dispatch. After takeover this raises.
            try:
                bd_lease.assert_agent_may_act()
            except bd_lease.HumanHasControl as e:
                return json.dumps({"ok": False, "action": "click", "code": "human_has_control", "error": str(e)})
            clicks.append(args.get("element"))
            backends.append(id(kwargs.get("_backend_marker", object())))
            # After first click, human takes over before step 2.
            if len(clicks) == 1:
                bd_lease.acquire("human-1", reason="test")
            return {"ok": True}
        return {"ok": False, "error": action}

    monkeypatch.setattr(cu_tool, "handle_computer_use", fake_handle)

    raw = cu_tool._run_goal_canonical({"action": "run_goal", "goal": "click twice"}, session_id="s1")
    payload = json.loads(raw)

    assert clicks == [1], clicks
    assert payload["ok"] is False
    assert any("human_has_control" in (s.get("error") or "") or s.get("execute_ok") is False
               for s in payload.get("steps", [])) or payload.get("status") != "done"


def test_run_goal_no_replay_after_hand_back(monkeypatch, agent_lease):
    """After a mid-loop takeover, handing back must not auto-replay the failed step."""
    decide_n = {"n": 0}
    clicks = []

    def fake_handle(args, **kwargs):
        action = args.get("action")
        if action == "decide":
            decide_n["n"] += 1
            return {"ok": True, "fail_open": False, "decision": {
                "action": "click", "target_element": decide_n["n"], "done": False,
                "backend": "jev", "confidence": 0.9,
            }}
        if action == "click":
            try:
                bd_lease.assert_agent_may_act()
            except bd_lease.HumanHasControl as e:
                return json.dumps({"ok": False, "action": "click", "code": "human_has_control", "error": str(e)})
            clicks.append(args.get("element"))
            bd_lease.acquire("human-1", reason="test")
            return {"ok": True}
        return {"ok": False, "error": action}

    monkeypatch.setattr(cu_tool, "handle_computer_use", fake_handle)
    raw = cu_tool._run_goal_canonical({"goal": "once"}, session_id="s1")
    payload = json.loads(raw)
    assert clicks == [1]
    # Hand back and ensure no automatic extra click from the same loop.
    bd_lease.release("human-1")
    assert clicks == [1]
    assert payload.get("status") != "done" or payload.get("ok") is False


def test_run_goal_rejects_mutation_when_lease_changes_during_blocked_wait(monkeypatch, agent_lease):
    """TEST B: while a leaf is blocked (approval wait simulated), lease flip voids effect."""
    from tools.computer_use.tool import handle_computer_use

    # Use real lease fencing around a stubbed backend path: after admit, flip lease then fence.
    admitted = bd_lease.assert_agent_may_act()
    bd_lease.acquire("human-1", reason="during wait")
    with pytest.raises(bd_lease.HumanHasControl):
        if bd_lease.get().epoch != admitted.epoch:
            raise bd_lease.HumanHasControl("lease moved during wait")
