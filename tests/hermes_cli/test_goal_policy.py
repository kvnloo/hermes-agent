"""Behavior at the real goal manager and plugin policy boundary."""
import json
import shlex
import sys
from pathlib import Path

import pytest

from gateway.session_context import scoped_current_session_id
from hermes_cli.goal_policy import GoalPolicyDecision
from hermes_cli.goals import GoalGate, GoalManager, load_goal
from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest


class Policy:
    def prepare(self):
        return "Existing workflow content loaded by the test policy."

    def decide(self, observation):
        if not observation.workflow_loaded:
            return GoalPolicyDecision("load_workflow")
        if observation.verdict == "done" and observation.checks_passed:
            return GoalPolicyDecision("finish")
        if observation.verdict == "wait" and observation.wake_id:
            return GoalPolicyDecision("wait")
        return GoalPolicyDecision("replan")


@pytest.fixture
def armed(tmp_path, monkeypatch):
    home = tmp_path / "profile-a"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    manager = PluginManager()
    manager._discovered = True
    ctx = PluginContext(PluginManifest(name="test-policy"), manager)
    monkeypatch.setattr(ctx, "get_config", lambda key, default=None: True if key == "allow_arm" else default)
    monkeypatch.setattr("hermes_cli.plugins.get_plugin_manager", lambda: manager)
    policy = Policy()
    registration = ctx.register_goal_policy(policy)
    held = GoalManager("mission")
    assert not held.is_active()
    command = f"{shlex.quote(sys.executable)} -c 'print(\"checked\")'"
    with scoped_current_session_id("mission"):
        receipt = ctx.arm_goal("Original whole mission", max_turns=8, gates=[GoalGate(command)])
    assert receipt["armed"]
    assert "workflow content" in receipt["workflow"]
    from hermes_cli.goal_policy import refresh_after_tool_arm
    refresh_after_tool_arm(held)
    assert held.is_active()
    return ctx, policy, registration, GoalManager("mission")


def judge(monkeypatch, verdict="blocked", directive=None):
    monkeypatch.setattr("hermes_cli.goals.judge_goal", lambda *a, **kw:
                        (verdict, "current plan exhausted", False, directive, False))


def test_final_answer_and_blocked_replan_original_goal(armed, monkeypatch):
    *_, manager = armed
    judge(monkeypatch)
    result = manager.evaluate_after_turn("I am blocked. Nothing more can be done.")
    assert result["should_continue"]
    assert result["verdict"] == "replan"
    assert "Original whole mission" in result["continuation_prompt"]
    assert GoalManager("mission").is_active()
    assert GoalManager("mission").state.turns_used == 1


def test_completion_runs_all_checks_with_real_outputs(armed, tmp_path, monkeypatch):
    *_, manager = armed
    marker = tmp_path / "second-check"
    code = f"from pathlib import Path; Path({str(marker)!r}).write_text('verified')"
    manager.add_gate(f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}")
    judge(monkeypatch, "done")
    assert manager.evaluate_after_turn("done")["status"] == "done"
    assert marker.read_text() == "verified"
    assert all(g.last_exit_code == 0 for g in GoalManager("mission").state.gates)


def test_missing_and_failing_checks_cannot_complete(armed, monkeypatch):
    *_, manager = armed
    judge(monkeypatch, "done")
    manager.clear_gates()
    assert manager.evaluate_after_turn("all checks passed")["should_continue"]
    assert manager.is_active()
    manager.add_gate(manager.state.policy_checks[0])
    manager.add_gate(f"{shlex.quote(sys.executable)} -c 'raise SystemExit(3)'")
    result = manager.evaluate_after_turn("all checks passed")
    assert result["should_continue"]
    assert "Exit 3" in result["continuation_prompt"]
    assert manager.is_active()


def test_workflow_load_is_required_not_self_asserted(armed, monkeypatch):
    _, policy, _, manager = armed
    manager.state.policy_workflow_digest = ""
    manager._save()
    judge(monkeypatch, "done")
    result = manager.evaluate_after_turn("I loaded pstack, trust me")
    assert result["verdict"] == "load_workflow"
    assert "Existing workflow content" in result["continuation_prompt"]
    monkeypatch.setattr(policy, "prepare", lambda: "")
    assert manager.evaluate_after_turn("done")["status"] == "paused"


def test_unchanged_workflow_is_not_repeated(armed, monkeypatch):
    _, policy, _, manager = armed
    judge(monkeypatch)
    for _ in range(2):
        prompt = manager.evaluate_after_turn("unfinished")["continuation_prompt"]
        assert policy.prepare() not in prompt
        assert manager.state.policy_workflow_digest in prompt


def test_changed_workflow_is_loaded_once(armed, monkeypatch):
    _, policy, _, manager = armed
    judge(monkeypatch)
    monkeypatch.setattr(policy, "prepare", lambda: "Changed instructions for the same workflow.")
    first = manager.evaluate_after_turn("unfinished")
    assert first["verdict"] == "load_workflow"
    assert policy.prepare() in first["continuation_prompt"]
    assert policy.prepare() not in manager.evaluate_after_turn("unfinished")["continuation_prompt"]


def test_compression_requires_workflow_reload(armed, monkeypatch):
    from hermes_cli.goals import migrate_goal_to_session
    _, policy, _, manager = armed
    judge(monkeypatch)
    assert migrate_goal_to_session(manager.session_id, "compressed", reason="compression")
    resumed = GoalManager("compressed")
    first = resumed.evaluate_after_turn("Earlier instructions were compressed")
    assert first["verdict"] == "load_workflow"
    assert policy.prepare() in first["continuation_prompt"]
    assert policy.prepare() not in resumed.evaluate_after_turn("unfinished")["continuation_prompt"]


@pytest.mark.parametrize("action", ["pause", "clear"])
def test_user_controls_survive_reload(armed, monkeypatch, action):
    *_, manager = armed
    judge(monkeypatch)
    getattr(manager, action)()
    assert not GoalManager("mission").evaluate_after_turn("continue")["should_continue"]
    assert not GoalManager("new-session").evaluate_after_turn("continue")["should_continue"]


def test_pause_during_judge_wins(armed, monkeypatch):
    *_, manager = armed
    def paused(*args, **kwargs):
        GoalManager("mission").pause("user-paused")
        return "done", "done", False, None, False
    monkeypatch.setattr("hermes_cli.goals.judge_goal", paused)
    assert not manager.evaluate_after_turn("done")["should_continue"]
    assert GoalManager("mission").state.status == "paused"


def test_budget_is_not_refilled_by_arm(armed, monkeypatch):
    ctx, _, _, manager = armed
    judge(monkeypatch)
    manager.state.max_turns = 1
    manager._save()
    assert manager.evaluate_after_turn("continue")["status"] == "paused"
    with scoped_current_session_id("mission"), pytest.raises(ValueError, match="already has a goal"):
        ctx.arm_goal("replacement", max_turns=100, gates=manager.state.gates)
    assert GoalManager("mission").state.max_turns == 1


def test_estop_leaves_budget_and_state_untouched(armed, monkeypatch):
    *_, manager = armed
    before = manager.state.to_json()
    monkeypatch.setattr("agent.estop.is_engaged", lambda: True)
    assert not manager.evaluate_after_turn("continue")["should_continue"]
    assert load_goal("mission").to_json() == before


def test_policy_disposal_cannot_fall_back_to_done(armed, monkeypatch):
    _, _, registration, manager = armed
    registration.dispose()
    judge(monkeypatch, "done")
    result = manager.evaluate_after_turn("done")
    assert result["status"] == "paused"
    assert "unavailable" in result["reason"]


def test_dead_or_unowned_wait_replans(armed, monkeypatch):
    *_, manager = armed
    judge(monkeypatch, "wait", {"session_id": "invented"})
    result = manager.evaluate_after_turn("waiting")
    assert result["should_continue"]
    assert not manager.is_waiting()


def test_native_deadline_and_delegation_release(armed, monkeypatch):
    *_, manager = armed
    judge(monkeypatch, "wait", {"seconds": 600})
    monkeypatch.setattr("hermes_cli.goals.count_active_delegations", lambda sid: 1)
    result = manager.evaluate_after_turn("waiting", active_delegations=1)
    assert result["verdict"] == "wait"
    reloaded = GoalManager("mission")
    assert reloaded.is_waiting()
    monkeypatch.setattr("hermes_cli.goals.count_active_delegations", lambda sid: 0)
    assert not reloaded.is_waiting()


def test_other_profile_cannot_arm_with_foreign_context(armed, monkeypatch, tmp_path):
    ctx, _, _, manager = armed
    home = tmp_path / "profile-b"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    assert load_goal("mission") is None
    with pytest.raises(PermissionError, match="another profile"):
        manager.evaluate_after_turn("continue")
    with scoped_current_session_id("mission"), pytest.raises(PermissionError, match="another profile"):
        ctx.arm_goal("foreign", max_turns=4, gates=manager.state.gates)
    assert load_goal("mission") is None


def test_arm_requires_bound_session_and_opt_in(armed, monkeypatch):
    ctx, _, _, manager = armed
    with scoped_current_session_id(""), pytest.raises(RuntimeError, match="bound native session"):
        ctx.arm_goal("new", max_turns=4, gates=manager.state.gates)
    monkeypatch.setattr(ctx, "get_config", lambda key, default=None: False)
    with scoped_current_session_id("new"), pytest.raises(PermissionError, match="allow_arm"):
        ctx.arm_goal("new", max_turns=4, gates=manager.state.gates)


@pytest.mark.parametrize("action", ["finish", "wait", "idle"])
def test_unsafe_policy_decisions_are_rejected(armed, monkeypatch, action):
    _, policy, _, manager = armed
    judge(monkeypatch, "blocked")
    monkeypatch.setattr(policy, "decide", lambda observation: GoalPolicyDecision(action))
    result = manager.evaluate_after_turn("complete without evidence")
    assert result["status"] == "paused"
    assert result["verdict"] == "policy_error"


def test_zero_retry_cap_arms_without_widening(armed):
    ctx, _, _, manager = armed
    gate = GoalGate(manager.state.gates[0].command, max_retries=0)
    with scoped_current_session_id("zero-retries"):
        receipt = ctx.arm_goal("No repair attempts", max_turns=2, gates=[gate])
    assert receipt["armed"]
    stored = load_goal("zero-retries")
    assert stored is not None
    assert stored.status == "active"
    assert stored.gates[0].max_retries == 0


def test_gate_retry_budget_is_authoritative(armed, monkeypatch):
    *_, manager = armed
    manager.add_gate(f"{shlex.quote(sys.executable)} -c 'raise SystemExit(4)'", max_retries=1)
    judge(monkeypatch, "done")
    assert manager.evaluate_after_turn("done")["status"] == "active"
    assert manager.evaluate_after_turn("done")["status"] == "paused"
    assert manager.state.gates[-1].last_exit_code == 4


def test_real_pid_wait_registers_and_releases(armed, monkeypatch):
    import subprocess
    *_, manager = armed
    child = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"], stdin=subprocess.PIPE)
    try:
        judge(monkeypatch, "wait", {"pid": child.pid})
        processes = [{"pid": child.pid, "owner_task_id": manager.session_id, "status": "running"}]
        assert manager.evaluate_after_turn("waiting", background_processes=processes)["verdict"] == "wait"
        reloaded = GoalManager("mission")
        assert reloaded.state is not None
        assert reloaded.state.waiting_on_pid == child.pid
        assert reloaded.is_waiting()
        child.communicate(timeout=10)
        assert not reloaded.is_waiting()
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
        if child.stdin and not child.stdin.closed:
            child.stdin.close()


@pytest.mark.parametrize("verdict", ["continue", "blocked"])
def test_unfinished_acceptance_does_not_consume_repair_retries(armed, monkeypatch, verdict):
    *_, manager = armed
    manager.add_gate(f"{shlex.quote(sys.executable)} -c 'raise SystemExit(4)'", max_retries=1)
    judge(monkeypatch, verdict)
    for _ in range(4):
        assert manager.evaluate_after_turn("Still working on the original goal")["should_continue"]
    stored = load_goal("mission")
    assert stored is not None
    assert stored.gates[-1].attempts == 0
    assert stored.gates[-1].last_exit_code == 4


def test_unfinished_acceptance_can_register_owned_wait(armed, monkeypatch):
    import subprocess
    *_, manager = armed
    manager.add_gate(f"{shlex.quote(sys.executable)} -c 'raise SystemExit(4)'", max_retries=1)
    child = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"], stdin=subprocess.PIPE)
    try:
        judge(monkeypatch, "wait", {"pid": child.pid})
        processes = [{"pid": child.pid, "owner_task_id": manager.session_id, "status": "running"}]
        result = manager.evaluate_after_turn("Waiting for owned work", background_processes=processes)
        assert result["verdict"] == "wait"
        stored = load_goal("mission")
        assert stored is not None
        assert stored.waiting_on_pid == child.pid
        assert stored.gates[-1].attempts == 0
        child.communicate(timeout=10)
        assert not GoalManager("mission").is_waiting()
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
        if child.stdin and not child.stdin.closed:
            child.stdin.close()


@pytest.mark.parametrize("control", ["pause", "clear"])
@pytest.mark.parametrize("verdict", ["continue", "done", "wait"])
def test_user_control_at_commit_boundary_wins(armed, monkeypatch, control, verdict):
    from hermes_cli.goals import _get_session_db

    *_, manager = armed
    judge(monkeypatch, verdict, {"seconds": 600} if verdict == "wait" else None)
    db = _get_session_db()
    assert db is not None
    write = db._execute_write
    intercepted = False

    def controlled_write(operation, *args, **kwargs):
        nonlocal intercepted
        if not intercepted:
            intercepted = True
            getattr(GoalManager("mission"), control)()
        return write(operation, *args, **kwargs)

    monkeypatch.setattr(db, "_execute_write", controlled_write)
    result = manager.evaluate_after_turn("Current turn ended")
    assert intercepted
    assert not result["should_continue"]
    stored = load_goal("mission")
    assert stored is not None
    assert stored.status == {"pause": "paused", "clear": "cleared"}[control]
    assert stored.turns_used == 0


def test_two_armers_cannot_replace_each_other(armed, monkeypatch):
    from hermes_cli.goals import _get_session_db

    ctx, _, _, manager = armed
    db = _get_session_db()
    assert db is not None
    write = db._execute_write
    intercepted = False

    def competing_write(operation, *args, **kwargs):
        nonlocal intercepted
        if not intercepted:
            intercepted = True
            ctx.arm_goal("Winning mission", max_turns=2, gates=manager.state.gates)
        return write(operation, *args, **kwargs)

    monkeypatch.setattr(db, "_execute_write", competing_write)
    with scoped_current_session_id("concurrent-arm"), pytest.raises((ValueError, PermissionError)):
        ctx.arm_goal("Stale mission", max_turns=8, gates=manager.state.gates)
    stored = load_goal("concurrent-arm")
    assert stored is not None
    assert stored.goal == "Winning mission"
    assert stored.max_turns == 2


def test_legacy_state_and_default_blocked_unchanged(monkeypatch):
    from hermes_cli.goals import GoalState
    assert GoalState.from_json(json.dumps({"goal": "legacy"})).policy == ""
    manager = GoalManager("default")
    manager.set("ordinary goal")
    judge(monkeypatch)
    assert manager.evaluate_after_turn("blocked")["status"] == "paused"
