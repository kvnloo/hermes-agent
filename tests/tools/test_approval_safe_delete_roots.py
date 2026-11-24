"""``approvals.safe_delete_roots``: an agent deleting its own scratch, worktrees and caches runs without a prompt.

A delete-only command clears when every target resolves strictly inside a safe root and, for git targets,
nothing is uncommitted or unpushed. Everything else is prompted exactly as before, and ``approvals.deny``
still wins. The tests drive the public guards with a deny-answering callback: a prompt shows up as a call.
"""

import os
import subprocess
from unittest.mock import MagicMock

import pytest

import tools.approval as approval_module
from hermes_constants import get_hermes_home
from tools import approval_context
from tools.approval import check_all_command_guards, check_dangerous_command
from tools.approval_context import reset_current_session_key, set_current_session_key

GUARDS = [check_all_command_guards, check_dangerous_command]
DEFAULT_ROOTS = ["<scratch>", "<kanban-workspaces>", "<build-outputs>"]
_ENV = ("HERMES_INTERACTIVE", "HERMES_GATEWAY_SESSION", "HERMES_EXEC_ASK", "HERMES_YOLO_MODE",
        "HERMES_CRON_SESSION", "UNSET_VAR")


def _git(cwd, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false",
                    "-c", "init.defaultBranch=main", *args], cwd=cwd, env=env, check=True, capture_output=True)


@pytest.fixture
def config(monkeypatch):
    state = {"mode": "manual", "deny": [], "safe_delete_roots": list(DEFAULT_ROOTS)}
    monkeypatch.setattr(approval_context, "_get_approval_config", lambda: state)
    return state


@pytest.fixture(autouse=True)
def _interactive(monkeypatch, config):
    monkeypatch.setattr(approval_context, "_get_approval_mode", lambda: "manual")
    monkeypatch.setattr(approval_module, "_YOLO_MODE_FROZEN", False)
    for name in _ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HERMES_INTERACTIVE", "1")
    approval_module._session_approved.clear()
    approval_module._permanent_approved.clear()
    approval_module._permanent_approved_by_home.clear()
    token = set_current_session_key("safe-delete-roots")
    yield
    reset_current_session_key(token)


@pytest.fixture
def scratch():
    path = get_hermes_home() / "cache" / "scratch"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def repo(tmp_path, scratch):
    """A clone in scratch with a pushed ``main`` and ``pushed``, an unpushed ``local-only`` branch, a clean pushed
    worktree ``wt`` on ``topic`` and a dirty one ``wt-dirty`` on ``topic2`` (pushed, with an uncommitted file)."""
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    clone = scratch / "clone"
    _git(scratch, "clone", "-q", str(remote), str(clone))
    (clone / "f.txt").write_text("1\n")
    _git(clone, "add", "f.txt")
    _git(clone, "commit", "-q", "-m", "one")
    _git(clone, "push", "-q", "origin", "main")
    for branch in ("pushed", "topic", "topic2"):
        _git(clone, "branch", branch)
        _git(clone, "push", "-q", "origin", branch)
    _git(clone, "switch", "-q", "-c", "local-only")
    (clone / "g.txt").write_text("2\n")
    _git(clone, "add", "g.txt")
    _git(clone, "commit", "-q", "-m", "unpushed")
    _git(clone, "switch", "-q", "main")
    _git(clone, "worktree", "add", "-q", str(scratch / "wt"), "topic")
    _git(clone, "worktree", "add", "-q", str(scratch / "wt-dirty"), "topic2")
    (scratch / "wt-dirty" / "f.txt").write_text("changed\n")
    return clone


def _run(guard, command, env_type="local"):
    cb = MagicMock(return_value="deny")
    return guard(command, env_type, approval_callback=cb), cb


def _assert_cleared(guard, command):
    result, cb = _run(guard, command)
    cb.assert_not_called()
    assert result["approved"] is True, result
    return result


def _assert_prompted(guard, command, env_type="local"):
    result, cb = _run(guard, command, env_type)
    cb.assert_called_once()
    assert result["approved"] is False


# --- Cleared (each one prompts without this feature) --------------------------------------------------------------

@pytest.mark.parametrize("guard", GUARDS)
def test_rm_rf_inside_scratch_runs_without_a_prompt(guard, scratch):
    (scratch / "x" / "sub").mkdir(parents=True)
    result = _assert_cleared(guard, f"rm -rf {scratch}/x")
    assert result["pre_approved"][0]["scope"] == "safe_delete"


@pytest.mark.parametrize("guard", GUARDS)
def test_clean_pushed_worktree_remove_and_branch_delete_run_without_a_prompt(guard, repo, scratch):
    _assert_cleared(guard, f"git -C {repo} worktree remove {scratch}/wt && git -C {repo} branch -D topic")


@pytest.mark.parametrize("guard", GUARDS)
def test_branch_delete_of_a_fully_pushed_branch_runs_without_a_prompt(guard, repo):
    _assert_cleared(guard, f"cd {repo} && git branch -D pushed")


@pytest.mark.parametrize("guard", GUARDS)
def test_build_outputs_under_the_cd_directory_run_without_a_prompt(guard, tmp_path):
    project = tmp_path / "project"
    (project / "node_modules").mkdir(parents=True)
    _assert_cleared(guard, f"cd {project} && rm -rf node_modules __pycache__ .pytest_cache")


@pytest.mark.parametrize("guard", GUARDS)
def test_an_earlier_grant_covers_the_rest_of_the_command(guard, scratch):
    """A finding the user already allowed (here the script flag) composes with a safe delete."""
    command = f"python3 -c 'print(1)' && rm -rf {scratch}/x"
    _assert_prompted(guard, command)
    approval_module.approve_permanent("script execution via -e/-c flag")
    result = _assert_cleared(guard, command)
    assert {e["scope"] for e in result["pre_approved"]} == {"permanent", "safe_delete"}


def test_default_roots_apply_when_the_key_is_absent(config, scratch):
    del config["safe_delete_roots"]
    _assert_cleared(check_all_command_guards, f"rm -rf {scratch}/x")


def test_unattended_deny_mode_no_longer_blocks_scratch_cleanup(monkeypatch, scratch):
    monkeypatch.delenv("HERMES_INTERACTIVE")
    monkeypatch.setenv("HERMES_CRON_SESSION", "1")
    monkeypatch.setattr(approval_context, "_get_cron_approval_mode", lambda: "deny")
    assert check_all_command_guards(f"rm -rf {scratch}/x", "local")["approved"] is True
    assert check_all_command_guards("rm -rf ~/projects", "local")["approved"] is False


# --- Controls: still prompted (or blocked) ------------------------------------------------------------------------

@pytest.mark.parametrize("guard", GUARDS)
def test_rm_rf_home_is_never_cleared(guard):
    result, _cb = _run(guard, "rm -rf ~")
    assert result["approved"] is False
    _assert_prompted(guard, "rm -rf ~/projects")


@pytest.mark.parametrize("guard", GUARDS)
def test_dotdot_escape_from_scratch_is_prompted(guard, scratch):
    _assert_prompted(guard, f"rm -rf {scratch}/../..")


@pytest.mark.parametrize("guard", GUARDS)
def test_symlink_in_scratch_pointing_at_home_is_prompted(guard, scratch):
    link = scratch / "home-link"
    link.symlink_to(os.path.expanduser("~"))
    # The real home holds this interpreter, so the runtime self-delete floor may block before any prompt.
    result, _cb = _run(guard, f"rm -rf {link}")
    assert result["approved"] is False
    outside = get_hermes_home() / "outside"
    outside.mkdir()
    (scratch / "out-link").symlink_to(outside)
    _assert_prompted(guard, f"rm -rf {scratch}/out-link")


@pytest.mark.parametrize("guard", GUARDS)
def test_worktree_with_uncommitted_changes_is_prompted(guard, repo, scratch):
    _assert_prompted(guard, f"git -C {repo} worktree remove --force {scratch}/wt-dirty && git -C {repo} branch -D topic2")


@pytest.mark.parametrize("guard", GUARDS)
def test_branch_with_unpushed_commits_is_prompted(guard, repo):
    _assert_prompted(guard, f"cd {repo} && git branch -D local-only")


@pytest.mark.parametrize("guard", GUARDS)
def test_rm_of_a_clone_needs_it_clean_and_pushed(guard, repo, scratch):
    """``rm -rf`` of a checkout gets the same check as ``git worktree remove``."""
    _assert_cleared(guard, f"rm -rf {scratch}/wt")
    _assert_prompted(guard, f"rm -rf {scratch}/wt-dirty")
    _assert_prompted(guard, f"rm -rf {scratch}/w*")
    _git(repo, "switch", "-q", "local-only")  # HEAD has a commit no remote has
    _assert_prompted(guard, f"rm -rf {repo}")


@pytest.mark.parametrize("guard", GUARDS)
def test_unset_variable_target_is_prompted(guard):
    _assert_prompted(guard, "rm -rf $UNSET_VAR/x")


@pytest.mark.parametrize("guard", GUARDS)
def test_deny_rule_wins_over_a_safe_root(guard, config, scratch):
    config["deny"] = ["rm -rf *"]
    result, cb = _run(guard, f"rm -rf {scratch}/x")
    cb.assert_not_called()
    assert result["approved"] is False


@pytest.mark.parametrize("guard", GUARDS)
def test_chain_with_one_target_outside_is_prompted(guard, scratch):
    _assert_prompted(guard, f"rm -rf {scratch}/x && rm -rf {get_hermes_home()}/outside")


@pytest.mark.parametrize("command", [
    "rm -rf {s}/x && python3 -c 'print(1)'",  # another finding keeps the prompt
    "sudo rm -rf {s}/x",
    "rm -rf $(echo {s})/x",
    "rm -rf {s}/x 2>/dev/null",
    "cd {s} ; rm -rf x",                      # a failed cd would not stop the rm
    "rm -rf x",                                 # relative target, cwd unknown
    "rm -rf {s}",                               # the root itself
    "rm -rf {s}/*/x",
    "rm --no-preserve-root -rf {s}/x",
    "rm -rf {s}/x; ssh host 'rm -rf /srv/data'",
    'rm -rf "$(echo {s})/x"',                 # substitution inside double quotes still runs
    "rm -rf {s}/x # trailing comment",
    "rm -rf {s}/x\nrm -rf ~/projects",
])
def test_shapes_the_check_does_not_read_are_prompted(command, scratch):
    _assert_prompted(check_all_command_guards, command.format(s=scratch))


def test_single_quoted_program_text_is_literal(scratch):
    """``{``, ``$`` and ``#`` inside single quotes are data for awk/grep, not shell syntax."""
    _assert_cleared(check_all_command_guards,
                    f"rm -rf {scratch}/x && df -k / | awk 'NR==2{{print $4}}' && ls {scratch} | grep -c '^x#$'")


def test_remote_backends_are_prompted(scratch):
    _assert_prompted(check_all_command_guards, f"rm -rf {scratch}/x", env_type="ssh")


def test_empty_list_turns_it_off(config, scratch):
    config["safe_delete_roots"] = []
    _assert_prompted(check_all_command_guards, f"rm -rf {scratch}/x")


def test_user_root_with_tilde_and_glob_in_last_component(config, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "wt" / "a").mkdir(parents=True)
    config["safe_delete_roots"] = ["~/wt"]
    _assert_cleared(check_all_command_guards, "rm -rf ~/wt/a ~/wt/b*")
    _assert_prompted(check_all_command_guards, "rm -rf ~/wt")
