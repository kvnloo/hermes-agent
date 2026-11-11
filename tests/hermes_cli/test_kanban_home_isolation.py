"""Kanban path isolation regression for #153098."""

from pathlib import Path

import hermes_constants
from hermes_cli import kanban_db as kb


def test_named_board_under_nested_scratch_home_stays_in_scratch(tmp_path, monkeypatch):
    native_root = tmp_path / "user" / ".hermes"
    scratch = native_root / "profiles" / "worker" / "cache" / "scratch" / "run" / ".hermes"
    scratch.mkdir(parents=True)
    monkeypatch.setattr(
        hermes_constants, "_get_platform_default_hermes_home", lambda: native_root
    )
    monkeypatch.setenv("HERMES_HOME", str(scratch))
    monkeypatch.delenv("HERMES_KANBAN_HOME", raising=False)
    monkeypatch.delenv("HERMES_KANBAN_DB", raising=False)

    assert kb.kanban_home() == scratch
    assert kb.kanban_db_path(board="isolated") == (
        scratch / "kanban" / "boards" / "isolated" / "kanban.db"
    )
    assert not (native_root / "kanban.db").exists()


def test_cli_named_board_create_uses_nested_scratch_home_even_with_db_pin(
    tmp_path, monkeypatch,
):
    """A CLI --board write must not reach the native board from a scratch home."""
    import argparse
    import sqlite3

    from hermes_cli import kanban as kc

    native_root = tmp_path / "user" / ".hermes"
    scratch = native_root / "profiles" / "worker" / "cache" / "scratch" / "run" / ".hermes"
    scratch.mkdir(parents=True)
    monkeypatch.setattr(
        hermes_constants, "_get_platform_default_hermes_home", lambda: native_root
    )
    monkeypatch.setenv("HERMES_HOME", str(scratch))
    monkeypatch.delenv("HERMES_KANBAN_HOME", raising=False)
    monkeypatch.delenv("HERMES_KANBAN_DB", raising=False)
    monkeypatch.delenv("HERMES_KANBAN_TASK", raising=False)
    monkeypatch.delenv("HERMES_DELEGATED_CHILD_CONTEXT", raising=False)

    kb.create_board("isolated")
    monkeypatch.setenv("HERMES_KANBAN_DB", str(scratch / "pinned.db"))

    parser = argparse.ArgumentParser(prog="hermes", add_help=False)
    subparsers = parser.add_subparsers(dest="command")
    kc.build_parser(subparsers)
    args = parser.parse_args(["kanban", "--board", "isolated", "create", "scratch-only"])
    assert kc.kanban_command(args) == 0

    scratch_db = scratch / "kanban" / "boards" / "isolated" / "kanban.db"
    assert scratch_db.is_file()
    with sqlite3.connect(scratch_db) as conn:
        titles = [row[0] for row in conn.execute("SELECT title FROM tasks")]
    assert titles == ["scratch-only"]
    assert not (native_root / "kanban" / "boards" / "isolated" / "kanban.db").exists()
