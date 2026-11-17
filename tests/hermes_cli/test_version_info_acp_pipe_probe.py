"""ACP stdin must not leak into Git version or dirty-status probes.

Regression for NousResearch/hermes-agent#156777. A Git launcher that waits for
stdin EOF models the Windows hang, with a real child process on POSIX CI.
"""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


@pytest.mark.platforms("linux", "macos")
def test_git_version_and_dirty_probes_detach_acp_stdin(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()

    # This stand-in Git executable models the Windows launcher that waits for
    # EOF on the inherited ACP pipe; other metadata commands return immediately.
    fake_git = bin_dir / "git"
    fake_git.write_text(
        f"#!{sys.executable}\n"
        + textwrap.dedent(
            """\
            import sys

            args = sys.argv[1:]
            if args in (
                ["rev-parse", "--is-inside-work-tree"],
                ["--no-optional-locks", "status", "--porcelain", "-uno"],
            ):
                sys.stdin.buffer.read()
            if args == ["rev-parse", "--is-inside-work-tree"]:
                print("true")
            elif args == ["--no-optional-locks", "status", "--porcelain", "-uno"]:
                print(" M tracked")
            elif args == ["rev-parse", "HEAD"]:
                print("a" * 40)
            elif args == ["branch", "--show-current"]:
                print("main")
            elif args == ["log", "-1", "--format=%ct", "HEAD"]:
                print("1700000000")
            elif args == ["rev-parse", "--short=7", "HEAD"]:
                print("aaaaaaa")
            """
        ),
        encoding="utf-8",
    )
    fake_git.chmod(0o755)

    # A pending ACP reader leaves the parent's stdin pipe open. Calling
    # communicate() here would close it and conceal the inherited-stdin bug.
    root = Path(__file__).resolve().parents[2]
    program = (
        "import json, os, sys, threading\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(root)!r})\n"
        "from hermes_cli.version_info import _run_git, _git_version_info\n"
        "ready = threading.Event()\n"
        "def reader():\n"
        "    sys.stdin.buffer.readline()\n"
        "    ready.set()\n"
        "    sys.stdin.buffer.readline()\n"
        "threading.Thread(target=reader, daemon=True).start()\n"
        "assert ready.wait(10)\n"
        f"repo = Path({str(repo)!r})\n"
        "result = {'probe': _run_git(repo, 'rev-parse', '--is-inside-work-tree'), "
        "'dirty': _git_version_info(repo).dirty}\n"
        "print(json.dumps(result), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))
    proc = subprocess.Popen(
        [sys.executable, "-c", program],
        cwd=repo,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        assert proc.stdin is not None
        proc.stdin.write("initialize\n")
        proc.stdin.flush()
        proc.wait(timeout=12)
        assert proc.stdout is not None
        assert proc.stderr is not None
        output = proc.stdout.read()
        errors = proc.stderr.read()
    finally:
        if proc.stdin is not None:
            proc.stdin.close()
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        if proc.stdout is not None:
            proc.stdout.close()
        if proc.stderr is not None:
            proc.stderr.close()

    assert proc.returncode == 0, errors
    assert json.loads(output.strip()) == {"probe": "true", "dirty": True}
