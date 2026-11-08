"""Regression for #150738: the terminal gate must cover CLI approval-policy edits.

The public CLI, its module entrypoint and unsetting the operator's deny floor
must receive the same dangerous-command classification.
"""

import pytest

from tools.approval_detection import detect_dangerous_command


@pytest.mark.parametrize(
    "command",
    [
        "hermes config set approvals.mode off",
        'hermes config set command_allowlist ["*"]',
        "hermes config unset approvals.deny",
        "hermes -p dev config unset approvals.deny",
        "HERMES_HOME=/tmp/dev hermes config unset approvals.deny",
        "python -m hermes_cli.main config set approvals.mode off",
        "python3 -m hermes_cli.main config unset approvals.deny",
    ],
)
def test_agent_config_policy_cli_changes_require_approval(command: str) -> None:
    assert detect_dangerous_command(command)[0] is True


@pytest.mark.parametrize(
    "command",
    [
        "hermes config set display.show_cost true",
        "hermes config unset display.show_cost",
    ],
)
def test_non_security_config_cli_changes_not_gated(command: str) -> None:
    assert detect_dangerous_command(command) == (False, None, None)
