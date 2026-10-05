"""Owner-branch consumer for #73717; real local shell, no delegation claim."""

from pathlib import Path
import shutil
import subprocess
import sys
import textwrap

import pytest


@pytest.mark.skipif(sys.platform != "linux", reason="Linux local-shell consumer")
def test_transient_workdir_restores_real_shell_before_directory_removal(tmp_path):
    """Only authored temporary paths and a clean child environment are used."""
    bash = shutil.which("bash")
    assert bash is not None
    home = tmp_path / "home"
    home.mkdir()
    hermes_home = home / ".hermes"
    hermes_home.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    transient = tmp_path / "transient"
    transient.mkdir()
    # Keep real Bash execution while excluding workstation login/rc files.
    shell = tmp_path / "clean-bash"
    shell.write_text(f'#!/bin/sh\nexec "{bash}" --noprofile --norc "$@"\n')
    shell.chmod(0o700)
    script = textwrap.dedent('''
        import json
        import os
        from pathlib import Path
        import socket
        from unittest.mock import patch

        attempts = []
        def deny_network(sock, address):
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                attempts.append(str(address))
                raise AssertionError("unexpected network attempt")
            raise AssertionError("unexpected socket connection")
        socket.socket.connect = deny_network
        socket.socket.connect_ex = deny_network

        import tools.terminal_tool as terminal
        from tools.environments.local import LocalEnvironment

        project = os.environ["TERMINAL_CWD"]
        transient = Path(os.environ["TEST_TRANSIENT"])
        task = "real-workdir-consumer"
        with patch("tools.environments.local._find_bash", return_value=os.environ["TEST_BASH"]):
            env = LocalEnvironment(cwd=project, timeout=10, env=dict(os.environ))
            terminal._active_environments["default"] = env
            terminal.record_session_cwd(task, project)
            try:
                override = json.loads(terminal.terminal_tool("pwd", task_id=task, workdir=str(transient)))
                assert override["exit_code"] == 0, override
                assert override["output"].strip() == str(transient), override
                # Observe the real backend state, not a stubbed execute result.
                assert env.cwd == project, (env.cwd, project)
                assert terminal.get_session_cwd(task) == project
                transient.rmdir()
                ordinary = json.loads(terminal.terminal_tool("pwd", task_id=task))
                assert ordinary["exit_code"] == 0, ordinary
                assert ordinary["output"].strip() == project, ordinary
                assert env.cwd == project
                assert terminal.get_session_cwd(task) == project
                assert not attempts, attempts
                print("real-shell transient restoration and post-removal pwd passed")
            finally:
                terminal._stop_cleanup_thread()
                terminal._active_environments.clear()
                env.cleanup()
    ''')
    child_env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "HERMES_HOME": str(hermes_home),
        "TERMINAL_ENV": "local",
        "TERMINAL_CWD": str(project),
        "TEST_TRANSIENT": str(transient),
        "TEST_BASH": str(shell),
        "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
    }
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=project, env=child_env,
        capture_output=True, text=True, timeout=45, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "post-removal pwd passed" in result.stdout
