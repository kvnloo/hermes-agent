"""Verification evidence must resolve shell-relative cd from the session cwd."""

from agent.verification_evidence import (
    mark_workspace_edited,
    record_terminal_result,
    verification_status,
)


def test_relative_cd_attributes_passing_suite_to_project(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_VERIFY_ON_STOP", "1")
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))

    session_cwd = tmp_path / "docs"
    session_cwd.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[tool.pytest.ini_options]")

    mark_workspace_edited(session_id="relative-cd", cwd=project, paths=["src/example.py"])
    evidence = record_terminal_result(
        command="cd ../project && pytest -q",
        cwd=session_cwd,
        session_id="relative-cd",
        exit_code=0,
        output="1 passed",
    )

    assert evidence is not None
    assert evidence["root"] == str(project.resolve())
    status = verification_status(session_id="relative-cd", cwd=project)
    assert status["status"] == "passed"
    assert status["changed_paths"] == []
    assert verification_status(session_id="relative-cd", cwd=session_cwd)["status"] == "not_applicable"
