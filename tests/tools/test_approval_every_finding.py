"""A grant for one finding must not approve a different dangerous finding later in the command.

The gates used to check only the first detector match, so with ``script execution via -e/-c flag``
on the permanent allowlist, ``python3 -c 1 && rg --pre ./x.sh foo .`` ran without asking even
though ``rg --pre`` alone prompts; ``docker stop web && git push --force`` passed under the docker
key the same way. Every finding must be covered by a grant, and an answer grants only the findings
its prompt showed.
"""

from unittest.mock import MagicMock

import pytest

import tools.approval as approval_module
from tools import approval_context
from tools.approval import approve_session, check_all_command_guards, check_dangerous_command, is_approved
from tools.approval_context import reset_current_session_key, set_current_session_key
from tools.approval_detection import detect_dangerous_command

SCRIPT_FLAG = detect_dangerous_command("python3 -c 'print(1)'")[1]
RG_PRE = detect_dangerous_command("rg --pre ./x.sh foo .")[1]
DOCKER_STOP = detect_dangerous_command("docker stop web")[1]
FORCE_PUSH = detect_dangerous_command("git push --force")[1]
SCRIPT_THEN_RG = "python3 -c 'print(1)' && rg --pre ./x.sh foo ."
DOCKER_THEN_PUSH = "docker stop web && git push --force"
_ENV = ("HERMES_INTERACTIVE", "HERMES_GATEWAY_SESSION", "HERMES_EXEC_ASK", "HERMES_YOLO_MODE",
        "HERMES_CRON_SESSION")
GUARDS = [check_all_command_guards, check_dangerous_command]


def _clear_approvals():
    approval_module._session_approved.clear()
    approval_module._permanent_approved.clear()
    approval_module._permanent_approved_by_home.clear()


@pytest.fixture(autouse=True)
def _manual_mode_and_clean_state(monkeypatch):
    monkeypatch.setattr(approval_context, "_get_approval_mode", lambda: "manual")
    for name in _ENV:
        monkeypatch.delenv(name, raising=False)
    _clear_approvals()
    token = set_current_session_key("every-finding")
    yield
    reset_current_session_key(token)
    _clear_approvals()


def test_the_chained_commands_carry_two_distinct_findings():
    assert len({SCRIPT_FLAG, RG_PRE, DOCKER_STOP, FORCE_PUSH}) == 4
    assert detect_dangerous_command(SCRIPT_THEN_RG)[1] == SCRIPT_FLAG
    assert detect_dangerous_command(DOCKER_THEN_PUSH)[1] == DOCKER_STOP


@pytest.mark.parametrize("guard", GUARDS)
@pytest.mark.parametrize(("command", "granted", "hidden"), [
    (SCRIPT_THEN_RG, SCRIPT_FLAG, RG_PRE),
    (DOCKER_THEN_PUSH, DOCKER_STOP, FORCE_PUSH),
])
def test_permanent_class_key_does_not_cover_a_later_finding(guard, command, granted, hidden, monkeypatch):
    monkeypatch.setenv("HERMES_INTERACTIVE", "1")
    approval_module.approve_permanent(granted)
    cb = MagicMock(return_value="deny")
    assert guard(command, "local", approval_callback=cb)["approved"] is False
    cb.assert_called_once()
    assert cb.call_args[0][1] == hidden  # the prompt names only what is still unapproved


@pytest.mark.parametrize("guard", GUARDS)
def test_session_grant_does_not_cover_a_later_finding(guard, monkeypatch):
    monkeypatch.setenv("HERMES_INTERACTIVE", "1")
    approve_session("every-finding", DOCKER_STOP)
    cb = MagicMock(return_value="deny")
    assert guard(DOCKER_THEN_PUSH, "local", approval_callback=cb)["approved"] is False
    assert cb.call_args[0][1] == FORCE_PUSH


def test_cron_deny_blocks_until_every_finding_is_allowed(monkeypatch):
    monkeypatch.setenv("HERMES_CRON_SESSION", "1")
    monkeypatch.setattr(approval_context, "_get_cron_approval_mode", lambda: "deny")
    approval_module.approve_permanent(SCRIPT_FLAG)
    result = check_all_command_guards(SCRIPT_THEN_RG, "local")
    assert result["approved"] is False
    assert RG_PRE in result["message"]
    approval_module.approve_permanent(RG_PRE)
    assert check_all_command_guards(SCRIPT_THEN_RG, "local")["approved"] is True


def test_an_answer_grants_only_the_findings_its_prompt_showed(monkeypatch):
    monkeypatch.setenv("HERMES_INTERACTIVE", "1")
    approve_session("every-finding", SCRIPT_FLAG)
    cb = MagicMock(return_value="session")
    assert check_all_command_guards(SCRIPT_THEN_RG, "local", approval_callback=cb)["approved"] is True
    assert cb.call_args[0][1] == RG_PRE
    assert is_approved("every-finding", RG_PRE)
    assert not is_approved("every-finding", DOCKER_STOP)
    assert check_all_command_guards(SCRIPT_THEN_RG, "local", approval_callback=cb)["approved"] is True
    cb.assert_called_once()


def test_a_command_with_one_finding_still_passes_on_its_key(monkeypatch):
    monkeypatch.setenv("HERMES_INTERACTIVE", "1")
    approval_module.approve_permanent(SCRIPT_FLAG)
    cb = MagicMock(return_value="deny")
    assert check_all_command_guards("python3 -c 'print(1)'", "local", approval_callback=cb)["approved"] is True
    cb.assert_not_called()
