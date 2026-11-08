"""An ACP stdin reader must not stall the full Windows Git version/dirty-status walk.

Regression companion to mjcity's real-process _run_git test in
NousResearch/hermes-agent#151212. A version User-Agent can resolve while
the ACP transport keeps its stdin pipe open; both the commit and tracked
working-tree changes must still be detected.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_cli._subprocess_compat import kill_and_drain, windows_hide_flags
from hermes_cli.local_runtime.processes import spawn_server


@pytest.mark.platforms("windows")
def test_full_version_metadata_with_pending_acp_stdin_reader(tmp_path):
    repo = tmp_path / "repo"
    git_opts = {
        "check": True,
        "stdin": subprocess.DEVNULL,
        "capture_output": True,
        "creationflags": windows_hide_flags(),
    }
    subprocess.run(["git", "init", "-q", str(repo)], **git_opts)
    tracked = repo / "tracked.txt"
    tracked.write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], **git_opts)
    subprocess.run(
        [
            "git", "-C", str(repo), "-c", "user.name=Hermes Test",
            "-c", "user.email=hermes-test@example.invalid",
            "commit", "-qm", "initial",
        ],
        **git_opts,
    )
    tracked.write_text("modified\n", encoding="utf-8")
    expected_commit = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True, encoding="utf-8", **git_opts,
    ).stdout.strip()

    root = Path(__file__).resolve().parents[2]
    program = tmp_path / "acp_reader.py"
    program.write_text(
        "import json, os, sys, threading\n"
        f"sys.path.insert(0, {str(root)!r})\n"
        "from pathlib import Path\n"
        "from hermes_cli.version_info import _git_version_info\n"
        "ready = threading.Event()\n"
        "def reader():\n"
        "    sys.stdin.buffer.readline()\n"
        "    ready.set()\n"
        "    sys.stdin.buffer.readline()\n"
        "threading.Thread(target=reader, daemon=True).start()\n"
        "assert ready.wait(15)\n"
        f"info = _git_version_info(Path({str(repo)!r}))\n"
        "print(json.dumps({'commit': info.commit, 'dirty': info.dirty}), flush=True)\n"
        # The deliberate pending stdin read must not keep this child alive at shutdown.
        "os._exit(0)\n",
        encoding="utf-8",
    )

    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    output = tmp_path / "result.txt"
    with output.open("w", encoding="utf-8") as stream:
        proc, job = spawn_server(
            [sys.executable, str(program)], stdin=subprocess.PIPE,
            stdout=stream, stderr=stream, startupinfo=startup,
        )
        try:
            assert proc.stdin is not None
            proc.stdin.write(b"initialize\n")
            proc.stdin.flush()  # ACP's pipe remains open during all Git probes.
            proc.wait(timeout=30)
            assert proc.returncode == 0, output.read_text(encoding="utf-8")
        finally:
            if job is not None:
                job.close()
            kill_and_drain(proc, 1)

    assert json.loads(output.read_text(encoding="utf-8").strip()) == {
        "commit": expected_commit,
        "dirty": True,
    }
