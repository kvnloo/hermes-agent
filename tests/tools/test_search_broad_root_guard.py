"""search_files refuses roots that span a whole disk before any walk starts.

A content or file search rooted at ``/``, the user's home, or a large data mount
still *succeeds*, but only after rg has read GiBs from the disk and slowed every
other process on it. Contract:

- A root that IS, or CONTAINS, a broad root (``/``, the home directory, any entry
  of ``search_files_broad_roots``) is refused before any shell runs, as a
  guardrail refusal that tells the caller to narrow ``path``.
- Every part of a multi-path string is checked.
- A project-sized root below a broad root still searches.
- ``search_files_refuse_broad_roots: false`` turns the check off.
"""

import json
from unittest.mock import patch

import pytest

from agent.tool_result_classification import GUARDRAIL_REFUSAL_KEY
from tools import file_tools
from tools.file_tools import search_tool


@pytest.fixture
def tree(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)
    monkeypatch.setattr("tools.file_operations._HOME", str(home))
    big = tmp_path / "disk" / "data"
    task = big / "projects" / "repo"
    task.mkdir(parents=True)
    (task / "a.py").write_text("NEEDLE_TOKEN = 1\n")
    return tmp_path


def _cfg(**values):
    return patch("hermes_cli.config.load_config_readonly", return_value=values)


@pytest.fixture
def no_shell(monkeypatch):
    """Fail loudly if a refused search reaches the file-ops/shell layer."""
    def _boom(*_a, **_k):
        raise AssertionError("refused search must not reach the shell")
    monkeypatch.setattr(file_tools, "_get_file_ops", _boom)


def _refused(raw: str) -> dict:
    result = json.loads(raw)
    assert "error" in result, result
    assert "narrow `path`" in result["error"].lower()
    assert result.get(GUARDRAIL_REFUSAL_KEY) is True
    return result


@pytest.mark.parametrize("rel", ["home/user", "home", "."])
def test_home_or_its_ancestor_is_refused(tree, no_shell, rel):
    with _cfg():
        _refused(search_tool("NEEDLE_TOKEN", path=str(tree / rel), task_id="t-broad"))


def test_filesystem_root_is_refused(tree, no_shell):
    with _cfg():
        r = _refused(search_tool("NEEDLE_TOKEN", target="files", path="/", task_id="t-broad"))
    assert "is a broad root" in r["error"]


@pytest.mark.parametrize("rel", ["disk/data", "disk"])
def test_configured_root_or_its_ancestor_is_refused(tree, no_shell, rel):
    with _cfg(search_files_broad_roots=[str(tree / "disk" / "data")]):
        _refused(search_tool("NEEDLE_TOKEN", path=str(tree / rel), task_id="t-broad"))


def test_trailing_slash_and_dotdot_do_not_bypass(tree, no_shell):
    sneaky = str(tree / "disk" / "data" / "projects" / "..") + "/"
    with _cfg(search_files_broad_roots=[str(tree / "disk" / "data")]):
        _refused(search_tool("NEEDLE_TOKEN", path=sneaky, task_id="t-broad"))


def test_multi_path_string_with_a_broad_part_is_refused(tree, no_shell):
    task = tree / "disk" / "data" / "projects" / "repo"
    with _cfg():
        _refused(search_tool("NEEDLE_TOKEN", path=f"{task}, {tree / 'home'}", task_id="t-broad"))


def test_root_below_broad_root_still_searches(tree):
    task = tree / "disk" / "data" / "projects" / "repo"
    with _cfg(search_files_broad_roots=[str(tree / "disk" / "data")]):
        result = json.loads(search_tool("NEEDLE_TOKEN", path=str(task), task_id="t-broad"))
    assert "error" not in result, result
    assert result["total_count"] == 1


def test_opt_out_disables_the_guard(tree):
    with _cfg(search_files_refuse_broad_roots=False,
              search_files_broad_roots=[str(tree / "disk" / "data")]):
        result = json.loads(search_tool("NEEDLE_TOKEN", path=str(tree / "disk"), task_id="t-broad"))
    assert "error" not in result, result
    assert result["total_count"] == 1
