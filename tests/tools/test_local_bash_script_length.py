"""Regression for Windows/MSYS2's long bash -c argument cliff (#156507)."""

import os
import stat
import subprocess
from pathlib import Path

import pytest

import tools.environments.local as local_module
from tools.environments.local import LocalEnvironment, _find_bash


def test_large_windows_bash_script_runs_from_file(tmp_path):
    """The real-size wrapper must be a script argument, not a long -c argument."""
    command = "#" * 9000 + "\nprintf 'MARKER_OK\\n'\n"
    argv, path = local_module._bash_script_argv(
        _find_bash(), command, login=False, windows=True, temp_dir=str(tmp_path)
    )
    assert path is not None
    try:
        assert "-c" not in argv
        assert Path(path).read_text(encoding="utf-8") == command
        if os.name != "nt":
            assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
        result = subprocess.run(argv, text=True, capture_output=True, check=True)
        assert result.stdout == "MARKER_OK\n"
    finally:
        Path(path).unlink()


def test_short_windows_script_remains_inline(tmp_path):
    argv, path = local_module._bash_script_argv(
        "bash", "printf short", login=True, windows=True, temp_dir=str(tmp_path)
    )
    assert argv == ["bash", "-l", "-c", "printf short"]
    assert path is None


@pytest.mark.platforms("windows")
def test_local_terminal_long_msys_wrapper_preserves_output_and_cleans_up(tmp_path, monkeypatch):
    """Exercise actual Windows subprocess behavior without faking the host OS."""
    monkeypatch.setenv("TERMINAL_TEMP_DIR", str(tmp_path))
    env = LocalEnvironment(cwd=str(tmp_path), timeout=20)
    result = env.execute("#" * 9000 + "\nprintf 'MARKER_OK\\n'\n")
    assert result["returncode"] == 0
    assert result["output"].strip() == "MARKER_OK"
    assert not list(tmp_path.glob("hermes-cmd-*.sh"))
