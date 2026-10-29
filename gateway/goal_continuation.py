"""Policy goal authority carried by the existing LOCAL automation FIFO."""
from hashlib import sha256
import logging

from hermes_state_runtime import RuntimeStoreError

logger = logging.getLogger(__name__)


class GoalSuperseded(RuntimeStoreError):
    def __init__(self):
        super().__init__("goal_superseded")


def continuation_guard(payload):
    token = payload.get("local_automation_v1", {}).get("goal_continuation")
    if token is None:
        return None
    if (not isinstance(token, dict) or set(token) != {"session_id", "revision"}
            or not all(isinstance(value, str) and value for value in token.values())):
        raise RuntimeStoreError("invalid_params")
    if token["session_id"] != payload["local_automation_v1"]["target"]:
        raise RuntimeStoreError("permission_denied")

    def guard(conn):
        from agent.estop import is_engaged
        from hermes_cli.goals import GoalState, _meta_key
        row = conn.execute("SELECT value FROM state_meta WHERE key = ?", (_meta_key(token["session_id"]),)).fetchone()
        state = GoalState.from_json(row[0]) if row else None
        if (state is None or state.status != "active" or is_engaged()
                or sha256(state.to_json().encode()).hexdigest() != token["revision"]):
            raise GoalSuperseded()
    return guard


def pause_undelivered(session_id, revision):
    from hermes_cli.goal_policy import _commit_goal
    from hermes_cli.goals import load_goal
    state = load_goal(session_id)
    if state is None or state.status != "active":
        return False
    expected = state.to_json()
    if sha256(expected.encode()).hexdigest() != revision:
        return False
    state.status = "paused"
    state.clear_wait()
    state.policy_workflow_digest = ""
    state.paused_reason = "Continuation admission failed; repair transport and use /goal resume."
    return _commit_goal(session_id, expected, state)


async def admit_policy_continuation(runner, source, session_id, prompt, revision):
    from gateway.session_automation import admit_route_wake
    metadata = {"goal_continuation": {"session_id": session_id, "revision": revision}}
    try:
        admitted = await admit_route_wake(runner, runner._delivery_adapter_for(source), source,
                                          prompt, "goal-continuation", metadata=metadata)
    except Exception:
        logger.warning("Policy goal continuation admission failed", exc_info=True)
        admitted = False
    if not admitted:
        paused = await runner._run_in_executor_with_context(lambda: pause_undelivered(session_id, revision))
        if paused:
            await runner._defer_goal_status_notice_after_delivery(
                source, "Goal paused: continuation admission failed. Repair the transport, then use /goal resume.")
    return admitted
