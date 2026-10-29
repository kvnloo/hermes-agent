"""Opt-in goal policies. The host owns controls, checks, budgets, and waits."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import time
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from hermes_cli.goals import GoalManager, GoalState

if TYPE_CHECKING:
    from hermes_cli.goals import GoalGate


@dataclass(frozen=True)
class GoalObservation:
    goal: str
    verdict: str
    workflow_loaded: bool
    checks_passed: bool
    wake_id: str | None = None


@dataclass(frozen=True)
class GoalPolicyDecision:
    action: Literal["load_workflow", "execute", "replan", "finish", "wait"]
    message: str = ""


@runtime_checkable
class GoalPolicy(Protocol):
    def prepare(self) -> str:
        """Load required workflow and return its actual content, or raise."""
        ...

    def decide(self, observation: GoalObservation) -> GoalPolicyDecision: ...


def register_goal_policy(ctx, policy: GoalPolicy):
    if not isinstance(policy, GoalPolicy):
        raise TypeError("policy must implement prepare and decide")
    return ctx._register_entry(
        "goal_policy", ctx.plugin_id, ctx._manager._goal_policies, policy,
        "Plugin %s registered goal policy: %s", ctx.plugin_id,
    )


def _policy(name: str) -> GoalPolicy:
    from hermes_cli.plugins import _delivery_manager
    policy = _delivery_manager()._goal_policies.get(name)
    if policy is None:
        raise RuntimeError(f"goal policy {name!r} is unavailable in this profile")
    return policy


def refresh_after_tool_arm(manager) -> None:
    from hermes_cli.gateway_automation import GatewayGoalManager
    from hermes_cli.goals import GoalManager, load_goal
    if isinstance(manager, GatewayGoalManager):
        manager.refresh()
    elif isinstance(manager, GoalManager):
        stored = load_goal(manager.session_id)
        if (stored and stored.policy) or (manager.state and manager.state.policy):
            manager._state = stored


def _workflow(policy: GoalPolicy) -> tuple[str, str]:
    text = policy.prepare()
    if not isinstance(text, str) or not text.strip():
        raise ValueError("goal policy returned no workflow content")
    return text, sha256(text.encode()).hexdigest()


class _GoalProposal(GoalManager):
    """Reuse native transitions without publishing their intermediate states."""

    def __init__(self, manager):
        self._profile_home = manager._profile_home
        self.session_id = manager.session_id
        self.default_max_turns = manager.default_max_turns
        self._state = GoalState.from_json(manager.state.to_json())

    def _save(self):
        return self._state


def _commit_goal(session_id: str, expected: str | None, state: GoalState) -> bool:
    from agent.estop import is_engaged
    from hermes_cli.goals import _get_session_db, _meta_key

    db = _get_session_db()
    if db is None:
        raise RuntimeError("goal database unavailable; transition not committed")
    key, replacement = _meta_key(session_id), state.to_json()

    def commit(conn):
        row = conn.execute("SELECT value FROM state_meta WHERE key = ?", (key,)).fetchone()
        current = GoalState.from_json(row[0]).to_json() if row is not None else None
        if current != expected or is_engaged():
            return False
        db.set_meta(key, replacement, cursor=conn.cursor())
        return True

    return db._execute_write(commit)


def arm_goal(ctx, goal: str, *, max_turns: int, gates: list[GoalGate]) -> dict:
    from agent.estop import is_engaged
    from gateway.session_context import _SESSION_ID
    from hermes_constants import hermes_home_key
    from hermes_cli.goals import GoalGate, load_goal

    sid = _SESSION_ID.get()
    if not isinstance(sid, str) or not sid:
        raise RuntimeError("arming requires a bound native session")
    if hermes_home_key() != ctx._manager.scope_key:
        raise PermissionError("goal policy belongs to another profile")
    if is_engaged():
        raise PermissionError("emergency stop is engaged")
    if ctx.get_config("allow_arm", False) is not True:
        raise PermissionError("operator must enable this plugin's allow_arm setting")
    if load_goal(sid) is not None:
        raise ValueError("session already has a goal; use native user controls or a new session")
    if type(max_turns) is not int or max_turns < 1:
        raise ValueError("max_turns must be a positive integer")
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError("goal must be nonempty")
    if not gates or any(not isinstance(g, GoalGate) or not g.command.strip()
                        or g.timeout_seconds <= 0 or g.max_retries < 0 for g in gates):
        raise ValueError("at least one operator-approved acceptance gate is required")
    text, digest = _workflow(_policy(ctx.plugin_id))
    if load_goal(sid) is not None or is_engaged():
        raise PermissionError("goal authority changed while loading workflow")
    state = GoalState(goal=goal.strip(), max_turns=max_turns, gates=gates, created_at=time.time(),
                      policy=ctx.plugin_id, policy_checks=[g.command for g in gates],
                      policy_workflow_digest=digest)
    if not _commit_goal(sid, None, state):
        raise PermissionError("goal authority changed before arming committed")
    stored = load_goal(sid)
    if stored is None or stored.to_json() != state.to_json():
        raise RuntimeError("goal did not persist; continuation is not armed")
    return {"armed": True, "session_id": sid, "status": GoalManager(sid).status_line(),
            "workflow": text, "workflow_sha256": digest}


def _observed_wake(manager, directive, background_processes) -> str | None:
    if not directive:
        return None
    from hermes_cli.goals import _pid_alive, _session_waiting
    own = [p for p in (background_processes or []) if p.get("status") != "exited"
           and str(p.get("owner_task_id") or p.get("task_id") or "") == manager.session_id]
    session = directive.get("session_id")
    if session and any(p.get("session_id") == session for p in own) and _session_waiting(session):
        return f"process:{session}"
    pid = directive.get("pid")
    if pid and any(p.get("pid") == pid for p in own) and _pid_alive(pid):
        return f"pid:{pid}"
    seconds = directive.get("seconds")
    if type(seconds) is int and seconds > 0:
        return f"deadline:{seconds}"
    return None


def _run_checks(state, *, completion_attempt: bool) -> tuple[bool, str, bool]:
    from hermes_cli.goals import _gate_workspace, run_gate
    if not state.policy_checks or any(cmd not in [g.command for g in state.gates] for cmd in state.policy_checks):
        return False, "Registered acceptance checks are missing. Restore them before completion.", False
    if state.subgoals:
        return False, "Additional criteria need an operator-reviewed acceptance mapping.", False
    cwd, refusal = _gate_workspace()
    if refusal:
        return False, refusal, True
    failures = []
    exhausted = False
    for gate in state.gates:
        passed, code, output = run_gate(gate, cwd=cwd)
        gate.last_exit_code, gate.last_output_tail = code, output
        if passed:
            gate.attempts = 0
        elif completion_attempt:
            gate.attempts += 1
        if not passed:
            failures.append(f"$ {gate.command}\nExit {code}\n{output}")
            exhausted |= gate.attempts > gate.max_retries
    return not failures, "\n\n".join(failures), exhausted


@dataclass
class _Evaluation:
    result: GoalPolicyDecision
    workflow: str = ""
    digest: str = ""
    evidence: str = ""
    reason: str = ""
    directive: dict | None = None
    failure: str = ""


def _validate_decision(result, observation: GoalObservation) -> None:
    if not isinstance(result, GoalPolicyDecision) or result.action not in {
        "load_workflow", "execute", "replan", "finish", "wait"
    }:
        raise ValueError("invalid goal policy decision")
    if result.action == "finish" and not (
        observation.workflow_loaded and observation.checks_passed and observation.verdict == "done"
    ):
        raise ValueError("policy attempted completion without current acceptance evidence")
    if result.action == "wait" and not (observation.workflow_loaded and observation.wake_id):
        raise ValueError("policy attempted an unregistered wait")


def _observe(manager, state, last_response, background_processes, active_delegations) -> _Evaluation:
    from hermes_cli.goals import (
        DEFAULT_MAX_CONSECUTIVE_PARSE_FAILURES, DEFAULT_MAX_CONSECUTIVE_TRANSPORT_FAILURES, judge_goal,
    )
    policy = _policy(state.policy)
    workflow, digest = _workflow(policy)
    loaded = state.policy_workflow_digest == digest
    verdict, reason, parse, directive, transport = (
        judge_goal(state.goal, last_response, subgoals=state.subgoals or None,
                   contract=state.contract if state.has_contract() else None,
                   background_processes=background_processes, active_delegations=active_delegations)
        if loaded else ("continue", "workflow required", False, None, False)
    )
    checks, evidence, exhausted = (
        _run_checks(state, completion_attempt=verdict == "done") if loaded else (False, "", False)
    )
    state.last_verdict, state.last_reason = verdict, reason
    state.consecutive_parse_failures = state.consecutive_parse_failures + 1 if parse else 0
    state.consecutive_transport_failures = state.consecutive_transport_failures + 1 if transport else 0
    wake = _observed_wake(manager, directive, background_processes) if verdict == "wait" else None
    observation = GoalObservation(state.goal, verdict, loaded, checks, wake)
    result = policy.decide(observation)
    _validate_decision(result, observation)
    failure = "acceptance retry budget exhausted" if exhausted else ""
    if state.consecutive_parse_failures >= DEFAULT_MAX_CONSECUTIVE_PARSE_FAILURES:
        failure = "judge parse failure budget exhausted"
    if state.consecutive_transport_failures >= DEFAULT_MAX_CONSECUTIVE_TRANSPORT_FAILURES:
        failure = "judge transport failure budget exhausted"
    return _Evaluation(result, workflow, digest, evidence, reason, directive, failure)


def evaluate_policy(manager, last_response, *, background_processes=None, active_delegations=0):
    from agent.estop import is_engaged
    from hermes_constants import hermes_home_key
    from hermes_cli.goals import _decision, load_goal

    original = manager.state.to_json()
    if manager._profile_home != hermes_home_key():
        raise PermissionError("goal manager belongs to another profile")
    stored = load_goal(manager.session_id)
    if stored is None or stored.to_json() != original:
        manager._state = stored
        return _decision(stored.status if stored else None, False, None, "superseded",
                         "goal changed before evaluation", "Goal evaluation superseded by user control.")
    if is_engaged():
        return _decision(manager.state.status, False, None, "paused", "emergency stop", "Emergency stop is engaged.")
    proposal = _GoalProposal(manager)
    decision = _evaluate_proposal(proposal, last_response, background_processes, active_delegations)
    if not _commit_goal(manager.session_id, original, proposal.state):
        current = load_goal(manager.session_id)
        manager._state = current
        return _decision(current.status if current else None, False, None, "superseded",
                         "goal controls changed during evaluation", "Goal evaluation superseded by user control.")
    manager._state = proposal.state
    decision["goal_revision"] = sha256(proposal.state.to_json().encode()).hexdigest()
    return decision


def _evaluate_proposal(manager, last_response, background_processes, active_delegations):
    state = manager.state
    if state.turns_used >= state.max_turns:
        return manager._budget_pause(manager.state, "continue", "turn budget exhausted")
    if manager.is_waiting():
        return manager._waiting_decision(manager.state)
    state.turns_used += 1
    state.last_turn_at = time.time()
    try:
        evaluation = _observe(manager, state, last_response, background_processes, active_delegations)
    except Exception as exc:
        failure = f"goal policy unavailable: {type(exc).__name__}: {exc}"
        evaluation = _Evaluation(GoalPolicyDecision("replan"), failure=failure)

    if evaluation.failure:
        return manager._pause_decision(evaluation.failure, "policy_error", evaluation.failure, evaluation.failure)
    return _apply_evaluation(manager, evaluation, active_delegations)


def _apply_evaluation(manager, evaluation: _Evaluation, active_delegations: int):
    from hermes_cli.goals import _decision
    state = manager.state
    result, reason = evaluation.result, evaluation.reason
    if result.action == "finish":
        manager.mark_done(reason)
        return _decision("done", False, None, "done", reason, "Goal acceptance checks passed.")
    if state.turns_used >= state.max_turns:
        return manager._budget_pause(state, "continue", reason)
    if result.action == "wait":
        parked = manager._apply_wait_directive(evaluation.directive, reason, active_delegations=active_delegations)
        if parked is not None and manager.is_waiting():
            return parked
        result = GoalPolicyDecision("replan", "Wake source is no longer pending.")
    state.policy_workflow_digest = evaluation.digest
    manager._save()
    prompt = (f"[Goal policy: {result.action}]\nOriginal goal: {state.goal}\n"
              f"{state.contract.render_block()}\n{result.message}\n{reason}\n{evaluation.evidence}\n\n"
              f"Required workflow, loaded by the host:\n{evaluation.workflow}\n\n"
              "Continue only within existing permissions and resource budgets. "
              "Reconsider the whole original goal, not only the blocked item. "
              "An exhausted plan is not completion. Do not bypass user controls.")
    return _decision("active", True, prompt, result.action, reason, f"Continuing goal: {result.action}")
