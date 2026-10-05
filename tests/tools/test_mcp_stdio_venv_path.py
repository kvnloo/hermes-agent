"""Bare MCP commands preserve user PATH precedence with a symlinked venv Python."""

import os
import subprocess
import sys

import pytest

from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from tools.mcp_tool_config import _resolve_stdio_command


@pytest.mark.platforms("posix")
@pytest.mark.parametrize("venv_has_command", [False, True])
def test_bare_command_skips_venv_but_not_interpreter_target_bin(
    tmp_path, monkeypatch, venv_has_command
):
    venv_bin = tmp_path / "checkout" / ".venv" / "bin"
    system_bin = tmp_path / "system-bin"
    later_bin = tmp_path / "later-bin"
    for directory in (venv_bin, system_bin, later_bin):
        directory.mkdir(parents=True)
    interpreter = system_bin / "python"
    interpreter.touch()
    (venv_bin / "python").symlink_to(interpreter)
    monkeypatch.setattr(sys, "executable", str(venv_bin / "python"))

    name = "mcp-fixture-command"
    for directory, marker in (
        (system_bin, "first-user"), (later_bin, "later-user"), (venv_bin, "managed")
    ):
        if directory == venv_bin and not venv_has_command:
            continue
        executable = directory / name
        executable.write_text(f"#!/bin/sh\nprintf '%s' '{marker}'\n")
        executable.chmod(0o755)

    child_path = os.pathsep.join(map(str, (venv_bin, system_bin, later_bin)))
    token = set_hermes_home_override(tmp_path / "hermes-home")
    try:
        command, env = _resolve_stdio_command(name, {"PATH": child_path})
    finally:
        reset_hermes_home_override(token)

    result = subprocess.run([command], env=env, capture_output=True, text=True, check=True)
    assert result.stdout == "first-user"
    assert env["PATH"] == child_path
