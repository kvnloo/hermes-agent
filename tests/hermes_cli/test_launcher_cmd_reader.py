"""Regression for issue #131093: shared .cmd reader must understand delayed HPY.

The Windows launcher fallback for non-ASCII profiles first stores the Python
path relative to %~dp0 and only then invokes !HPY!. This parser test is
host-independent; it does not claim cmd.exe was executed on Windows.
"""

from pathlib import Path

from hermes_cli._launchers import _launcher_python


def test_cmd_launcher_reader_resolves_delayed_python(tmp_path: Path) -> None:
    home = tmp_path / "张三"
    bin_dir = home / "bin"
    bin_dir.mkdir(parents=True)
    python = home / "tools" / "python.exe"
    python.parent.mkdir()
    python.write_bytes(b"MZ")

    launcher = bin_dir / "hermes.cmd"
    launcher.write_bytes(
        b"@echo off\r\n"
        b"setlocal EnableDelayedExpansion\r\n"
        b'set "HPY=%~dp0..\\\\tools\\\\python.exe"\r\n'
        b'"!HPY!" -I -c "print(1)" %*\r\n'
    )

    assert _launcher_python(launcher) == python
