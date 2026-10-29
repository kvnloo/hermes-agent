"""Policy resumption preserves admission budget and reloads workflow obligations."""
from hermes_cli.goals import GoalManager, load_goal


def test_resume_without_refill_invalidates_policy_workflow_receipt():
    manager = GoalManager("policy-resume-budget")
    manager.set("Complete the authorized fixture", max_turns=8)
    assert manager.state is not None
    manager.state.policy = "fixture-policy"
    manager.state.policy_workflow_digest = "prepared-but-not-delivered"
    manager.state.turns_used = 2
    manager._save()
    manager.pause("user-paused")
    GoalManager(manager.session_id).resume(reset_budget=False)
    stored = load_goal(manager.session_id)
    assert stored is not None
    assert stored.status == "active"
    assert stored.turns_used == 2
    assert stored.max_turns == 8
    assert stored.policy_workflow_digest == ""
