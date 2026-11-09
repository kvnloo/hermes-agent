"""Regression for #151339: an explicit cd must attribute tests to its target project."""

from agent.verification_evidence import (
    mark_workspace_edited,
    record_terminal_result,
    verification_status,
)


def test_explicit_cd_attributes_suite_to_other_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    monkeypatch.setenv("HERMES_VERIFY_ON_STOP", "1")

    origin = tmp_path / "origin"
    target = tmp_path / "target"
    for project in (origin, target):
        project.mkdir()
        (project / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")

    mark_workspace_edited(
        session_id="cross-project", cwd=target, paths=["src/changed.py"],
    )
    evidence = record_terminal_result(
        command=f'cd "{target}" && pytest -q',
        cwd=origin, session_id="cross-project", exit_code=0, output="1 passed\n",
    )

    assert evidence is not None
    assert evidence["root"] == str(target.resolve())
    assert verification_status(session_id="cross-project", cwd=target)["status"] == "passed"
    assert verification_status(session_id="cross-project", cwd=origin)["status"] == "unverified"
