"""Regression for #142122: explicitly browse gateway sessions from the CLI."""

from unittest.mock import Mock

import pytest

from cli import HermesCLI
from hermes_cli.gateway_session_store import SurfaceLabelReader
from hermes_state import SessionDB


@pytest.mark.parametrize("command", ["/sessions all", "/sessions --all"])
def test_sessions_all_lists_human_sources_and_keeps_numbered_resume_aligned(
    tmp_path, capsys, command,
):
    db = SessionDB(db_path=tmp_path / "state.db")
    rows = [
        ("legacy-cli", "cli", "cli"),
        ("gateway-cli", "local", "cli"),
        ("gateway-tui", "local", "tui"),
        ("gateway-desktop", "local", "desktop"),
        ("telegram-chat", "telegram", "telegram"),
        ("kanban-worker", "kanban", "kanban"),
        ("tool-run", "tool", "tool"),
        ("oneshot-run", "oneshot", "oneshot"),
        ("current-chat", "local", "cli"),
    ]
    for index, (sid, source, surface) in enumerate(rows):
        db.create_session(sid, source=source)
        db.append_message(sid, role="user", content="hello")
        db._conn.execute(
            "UPDATE sessions SET created_source=?, started_at=? WHERE id=?",
            (surface, 1_000_000 + index, sid),
        )
    db._conn.commit()
    cli = HermesCLI.__new__(HermesCLI)
    cli._session_db = SurfaceLabelReader(db)
    cli.session_id = "current-chat"
    cli._handle_resume_command = Mock()
    try:
        cli._handle_sessions_command(command)
        cli._handle_resume_command.assert_not_called()
        output = capsys.readouterr().out
        for sid in ["legacy-cli", "gateway-cli", "gateway-tui", "gateway-desktop", "telegram-chat"]:
            assert sid in output
        for sid in ["kanban-worker", "tool-run", "oneshot-run", "current-chat"]:
            assert sid not in output
        # Selection follows the displayed all-source table, rather than re-querying CLI-only rows.
        assert cli._resolve_resume_target("2")[0] == "gateway-desktop"

        cli._handle_sessions_command("/sessions")
        default_output = capsys.readouterr().out
        assert "gateway-cli" in default_output
        assert "legacy-cli" in default_output
        assert "gateway-tui" not in default_output
        assert "telegram-chat" not in default_output
        assert cli._resolve_resume_target("1")[0] == "gateway-cli"
    finally:
        db.close()


def test_sessions_target_still_delegates_to_resume():
    cli = HermesCLI.__new__(HermesCLI)
    cli._handle_resume_command = Mock()
    cli._handle_sessions_command("/sessions all hands")
    cli._handle_resume_command.assert_called_once_with("/resume all hands")


@pytest.mark.parametrize("command", ["/resume all", "/resume --all"])
def test_resume_all_discovers_gui_sessions_without_widening_default(tmp_path, capsys, command):
    """Regression for #151584: a Desktop gui row is discoverable via /resume all."""
    db = SessionDB(db_path=tmp_path / "state.db")
    try:
        for index, (sid, source) in enumerate([
            ("classic-cli", "cli"),
            ("desktop-gui", "gui"),
            ("tool-run", "tool"),
            ("current-chat", "cli"),
        ]):
            db.create_session(sid, source=source)
            db.append_message(sid, role="user", content="hello")
            db._conn.execute(
                "UPDATE sessions SET started_at=? WHERE id=?",
                (1_000_000 + index, sid),
            )
        db._conn.commit()

        cli = HermesCLI.__new__(HermesCLI)
        cli._session_db = SurfaceLabelReader(db)
        cli.session_id = "current-chat"

        cli._handle_resume_command("/resume")
        assert "desktop-gui" not in capsys.readouterr().out

        cli._handle_resume_command(command)
        output = capsys.readouterr().out
        assert "desktop-gui" in output
        assert "classic-cli" in output
        assert "tool-run" not in output
        assert "current-chat" not in output

        rows = cli._last_session_listing
        assert cli._pending_resume_sessions == rows
        number = next(i for i, row in enumerate(rows, 1) if row["id"] == "desktop-gui")
        assert cli._resolve_resume_target(str(number))[0] == "desktop-gui"
    finally:
        db.close()
