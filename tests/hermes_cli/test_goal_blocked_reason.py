"""Regression for a goal blocked by approval rather than impossibility.

The judge's BLOCKED verdict covers both impossible work and a user dependency.
The persisted pause reason and notice must not label the latter unachievable.
"""

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def hermes_home(tmp_path, monkeypatch):
    """Isolate the goal state DB, as in test_goals.py."""
    from hermes_cli import goals

    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))
    goals._DB_CACHE.clear()
    yield home
    goals._DB_CACHE.clear()


def test_user_approval_blocker_pauses_without_unachievable_label(hermes_home):
    from hermes_cli.goals import GoalManager

    manager = GoalManager(session_id="approval-blocker")
    manager.set("Publish the verified release")
    reason = "Publishing needs user approval"

    with patch(
        "hermes_cli.goals.judge_goal",
        return_value=("blocked", reason, False, None, False),
    ):
        decision = manager.evaluate_after_turn(
            "The release is verified; publishing requires approval."
        )

    assert decision["verdict"] == "blocked"
    assert decision["status"] == "paused"
    assert decision["should_continue"] is False
    assert decision["continuation_prompt"] is None
    assert "waiting on you" in decision["message"].lower()
    assert "/goal resume" in decision["message"]
    assert "unachievable" not in decision["message"].lower()
    assert manager.state is not None
    assert manager.state.status == "paused"
    assert manager.state.paused_reason == f"blocked on user input: {reason}"
