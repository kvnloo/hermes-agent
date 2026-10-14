"""Independent scanner-warning evidence for Hermes #138349 / owner PR #138353.

deadczarvc reported the dead fallback; KoNit-K owns the production repair.
These tests exercise filesystem discovery and its emitted warning, not source text.
"""

import logging

import pytest


def _scan_skill(name, tmp_path, monkeypatch, caplog):
    from agent.skill_commands import scan_skill_commands
    from hermes_constants import get_hermes_home

    # The canonical conftest binds a fresh Hermes home before this fixture runs.
    home = get_hermes_home()
    assert home.is_relative_to(tmp_path)
    (home / "config.yaml").write_text("skills:\n  external_dirs: []\n", encoding="utf-8")
    skill_dir = home / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: A local evidence fixture.\n---\nDo the task.\n",
        encoding="utf-8",
    )
    # A real empty workspace keeps project discovery away from ambient repositories.
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    with caplog.at_level(logging.WARNING, logger="agent.skill_commands"):
        commands = scan_skill_commands()
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.name == "agent.skill_commands" and record.levelno >= logging.WARNING
    ]
    return commands, warnings


@pytest.mark.parametrize("name,collides", [("handoff", True), ("tidy-notes", False)])
def test_scanner_preserves_builtin_and_ordinary_skill(name, collides, tmp_path, monkeypatch, caplog):
    from hermes_cli.commands import resolve_command

    assert (resolve_command(name) is not None) == collides
    commands, warnings = _scan_skill(name, tmp_path, monkeypatch, caplog)
    assert (f"/{name}" in commands) != collides
    assert bool(warnings) == collides


def test_scanner_warning_does_not_recommend_an_unregistered_loader(tmp_path, monkeypatch, caplog):
    from agent.skill_commands import skill_command_collision_note
    from hermes_cli.commands import resolve_command

    commands, warnings = _scan_skill("handoff", tmp_path, monkeypatch, caplog)
    assert "/handoff" not in commands
    assert warnings, "The collision must remain visible to the user."
    assert resolve_command("skill") is None
    # The owner already corrected listing guidance; the scanner must not retain
    # the unusable route whose failure is independently reported in #138349.
    assert "/skill handoff" not in skill_command_collision_note("handoff")
    assert all("/skill handoff" not in warning for warning in warnings), warnings
