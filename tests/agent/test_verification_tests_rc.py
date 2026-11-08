"""Regression for #151338: verifier stdout cannot invent an exit status."""

import pytest

from agent.verification_evidence import record_terminal_result, verification_status


@pytest.mark.parametrize(
    ("command", "output", "expected"),
    [
        (
            'sh scripts/run_tests.sh; echo "TESTS_RC=$?"',
            "2 failed, 41 passed\nTESTS_RC=1\n",
            "failed",
        ),
        (
            "sh scripts/run_tests.sh",
            "2 passed\nTESTS_RC=1\n",
            "passed",
        ),
    ],
)
def test_echoed_status_requires_matching_command(tmp_path, monkeypatch, command, output, expected):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    monkeypatch.setenv("HERMES_VERIFY_ON_STOP", "1")
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run_tests.sh").write_text("#!/bin/sh\nexit 0\n")

    event = record_terminal_result(
        command=command, cwd=tmp_path, session_id="tests-rc", exit_code=0, output=output,
    )

    assert event is not None
    assert event["canonical_command"] == "scripts/run_tests.sh"
    assert event["status"] == expected
    status = verification_status(session_id="tests-rc", cwd=tmp_path)
    assert status["status"] == expected
    assert status["evidence"]["id"] == event["id"]
