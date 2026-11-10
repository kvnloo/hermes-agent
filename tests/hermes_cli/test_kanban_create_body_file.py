"""`kanban create --body-file` — shell-proof body delivery (#115432).

`--body` is a plain string: embedded newlines and trailing flag-like tokens
(e.g. a body line reading ``--json``) die in shell-to-Python marshalling
(MSYS git-bash / terminal shell=True). ``--body-file <path>|-`` reads the
body from a file (``-`` = stdin) so the bytes never cross the shell.
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

import pytest

from hermes_cli import kanban as kc
from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc

BODY = "line one\nline two\n--json\n--body should survive verbatim\n"


@pytest.fixture
def kanban_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    return home


def _create(argv, monkeypatch=None, stdin=None):
    """Drive the real ``hermes kanban create`` parser into ``_cmd_create``."""
    root = argparse.ArgumentParser(prog="hermes")
    kc.build_parser(root.add_subparsers())
    args = root.parse_args(["kanban", "create", *argv])
    if stdin is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    return kc._cmd_create(args)


def _latest_body():
    with kbc.connect_closing() as conn:
        tasks = kb.list_tasks(conn)
    assert tasks, "expected _cmd_create to have stored a task"
    return tasks[-1]


def test_body_file_stores_body_verbatim_with_trailing_flags_intact(kanban_home, tmp_path, capsys):
    f = tmp_path / "body.md"
    f.write_text(BODY, encoding="utf-8")
    assert _create(["PROBE", "--body-file", str(f), "--assignee", "baxter", "--priority", "7"]) == 0
    capsys.readouterr()
    task = _latest_body()
    assert (task.body, task.assignee, task.priority) == (BODY, "baxter", 7)
    # --body and --body-file cannot both win; refuse instead of picking one.
    assert _create(["PROBE", "--body", "inline", "--body-file", str(f)]) == 2


def test_body_file_dash_reads_stdin(kanban_home, monkeypatch, capsys):
    assert _create(["PROBE", "--body-file", "-"], monkeypatch, stdin=BODY) == 0
    capsys.readouterr()
    assert _latest_body().body == BODY


# --- `--reasoning-effort` (Z21, kanban t_a43e2432) ----------------------------
# `create_task` already had the kwarg and `gateway/session_kanban.py` already
# forwarded `task.reasoning_effort` to the worker; neither create surface could
# set it, so a task created from the CLI or the kanban_create tool always ran at
# the profile default. These lock the wiring on both ends.

def _reasoning_effort(task_id):
    with kbc.connect_closing() as conn:
        return conn.execute(
            "SELECT reasoning_effort FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()[0]


def test_reasoning_effort_flag_persists_to_the_row(kanban_home, capsys):
    assert _create(["PROBE", "--assignee", "baxter", "--reasoning-effort", "low"]) == 0
    capsys.readouterr()
    assert _reasoning_effort(_latest_body().id) == "low"


def test_reasoning_effort_none_disables_thinking(kanban_home, capsys):
    assert _create(["PROBE", "--reasoning-effort", "none", "--json"]) == 0
    assert _reasoning_effort(_latest_body().id) == "none"


def test_reasoning_effort_invalid_value_is_rejected(kanban_home, capsys):
    # A typo'd level must not silently fall back to the profile default.
    assert _create(["PROBE", "--reasoning-effort", "ultrabrain"]) == 2
    assert "reasoning_effort must be one of" in capsys.readouterr().err
    with kbc.connect_closing() as conn:
        assert kb.list_tasks(conn) == []


def test_reasoning_effort_omitted_stays_null(kanban_home, capsys):
    assert _create(["PROBE"]) == 0
    capsys.readouterr()
    assert _reasoning_effort(_latest_body().id) is None
