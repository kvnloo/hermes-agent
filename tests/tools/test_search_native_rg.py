"""Local POSIX content/file search runs rg as a direct argv subprocess.

The shell path pays two bash spawns per search (``test -e`` probe + ``set -o
pipefail; rg ... | head``). On a ``LocalEnvironment`` the same rg argv can run
natively with a bounded stdout read; the parser and every argument builder are
shared, so the two transports must agree on results.
"""

import contextlib
import json
import os
import shlex
import time

import pytest

from tools.environments.local import LocalEnvironment
from tools.file_operations import ShellFileOperations

pytestmark = pytest.mark.platforms("posix")  # native rg lane is POSIX-only


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "a.py").write_text("needle one\nplain\nneedle two\n")
    (tmp_path / "b.txt").write_text("needle three\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.py").write_text("needle four\n")
    return tmp_path


@pytest.fixture(scope="module")
def _local_env(tmp_path_factory):
    """One real LocalEnvironment per module (constructing one costs ~0.8 s)."""
    return LocalEnvironment(cwd=str(tmp_path_factory.mktemp("native-rg")))


@pytest.fixture
def ops_factory(_local_env):
    """``make(tree, spy)`` → ShellFileOperations over the shared env, every execute recorded in ``spy``."""
    real = type(_local_env).execute.__get__(_local_env, type(_local_env))

    def make(tree, spy):
        _local_env.cwd = str(tree)

        def recording(command, *a, **kw):
            spy.append(command)
            return real(command, *a, **kw)

        _local_env.execute = recording
        return ShellFileOperations(_local_env, cwd=str(tree))

    yield make
    _local_env.__dict__.pop("execute", None)


def _normalized(result):
    d = result.to_dict()
    for key in ("matches", "files"):
        if key in d:
            d[key] = sorted(json.dumps(item, sort_keys=True) for item in d[key])
    return d


def test_native_search_never_touches_the_shell_and_matches_shell_results(tree, ops_factory, monkeypatch):
    if not ops_factory(tree, [])._has_command("rg"):
        pytest.skip("native search parity requires ripgrep in the search environment")
    cases = [
        dict(pattern="needle", path=str(tree)),
        # (no offset/limit slicing here: rg's parallel walk orders files
        # nondeterministically, so a page differs run-to-run on either transport)
        dict(pattern="needle", path=str(tree), output_mode="count"),
        dict(pattern="needle", path=str(tree), output_mode="files_only", file_glob="*.py"),
        dict(pattern="NEEDLE_NOPE", path=str(tree)),  # zero-match probes
        dict(pattern="*.py", path=str(tree), target="files"),
        dict(pattern="needle", path=str(tree / "missing")),
    ]
    for case in cases:
        monkeypatch.setenv("HERMES_NATIVE_FILE_READ", "0")
        shell = _normalized(ops_factory(tree, []).search(**case))
        monkeypatch.setenv("HERMES_NATIVE_FILE_READ", "1")
        calls = []
        native = _normalized(ops_factory(tree, calls).search(**case))
        assert native == shell, case
        # rg resolution (``command -v rg``) still goes through the shell once; the
        # existence probe and the rg pipeline itself must not.
        assert not [c for c in calls if "pipefail" in c or c.startswith("test -e")], case


def test_native_runner_honours_deadline_and_interrupt_while_rg_is_silent(tree, ops_factory, monkeypatch):
    """A search producing no output must still stop at the deadline / on /stop
    (the shell path gets this from ``_wait_for_process``)."""
    import threading
    import time

    from tools import interrupt

    ops = ops_factory(tree, [])
    started = time.monotonic()
    result = ops._run_rg_native(["sh", "-c", "'sleep 30'"], 5, timeout=1)
    assert result.exit_code == 124 and time.monotonic() - started < 5

    tid = threading.get_ident()
    threading.Timer(0.3, lambda: interrupt.set_interrupt(True, tid)).start()
    try:
        started = time.monotonic()
        result = ops._run_rg_native(["sh", "-c", "'sleep 30'"], 5, timeout=30)
    finally:
        interrupt.set_interrupt(False, tid)
    assert result.exit_code == 130 and time.monotonic() - started < 5


def test_kill_switch_routes_search_back_to_the_shell(tree, ops_factory, monkeypatch):
    monkeypatch.setenv("HERMES_NATIVE_FILE_READ", "0")
    calls = []
    result = ops_factory(tree, calls).search(pattern="needle", path=str(tree))
    assert result.total_count == 4
    assert any(c.startswith("test -e") for c in calls)
    assert any(c.startswith("set -o pipefail; ") for c in calls)


def test_limit_hit_keeps_drained_matches_when_group_kill_is_refused(tree, ops_factory, monkeypatch):
    """Reaching ``limit`` takes the early-stop branch that TERMs rg's group. macOS answers
    ``killpg`` with EPERM (not ESRCH) for a zombie-only group; that must not surface as a tool
    error nor discard the matches already drained (#116855)."""
    import os

    monkeypatch.setenv("HERMES_NATIVE_FILE_READ", "1")
    ops = ops_factory(tree, [])
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: (_ for _ in ()).throw(PermissionError(1, "Operation not permitted")))
    result = ops.search(pattern="needle", path=str(tree), limit=2)
    assert not result.error and len(result.matches) == 2, result.to_dict()


def test_local_search_runs_the_pinned_ripgrep_not_the_first_on_path(_local_env, tmp_path, monkeypatch):
    """The terminal PATH puts the user's tools first; Hermes's own search still runs PM's rg."""
    import pm
    from pm.install import InstalledPackage

    pinned = tmp_path / "store" / "ripgrep" / "rg"
    pinned.parent.mkdir(parents=True)
    pinned.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(pm, "installed_package",
                        lambda name: InstalledPackage(pinned.parent, "15", pinned) if name == "ripgrep" else None)
    ops = ShellFileOperations(_local_env, cwd=str(tmp_path))
    assert ops._resolve_command("rg") == str(pinned).replace("\\", "/")


# --- parent-death coverage for the native rg lane -------------------------
# `_run_rg_native` starts rg in its own session/group. On a graceful deadline or
# /stop it kills the group itself, but a caller killed mid-wait (a worker reclaim
# or a turn interrupt that SIGKILLs us) runs no Python cleanup: the #797
# measurement watched such an rg reparent and read 2.34 GiB in 2 m. The group is
# now handed to this process's owner-death supervisor (own_process_groups), so a
# SIGKILL/OOM/crash of the caller reaps the search subprocess like MCP's stdio
# children. This test spawns a fresh caller, kills it -9, and asserts the subprocess
# it left behind is gone.

def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _gone_within(pid: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.1)
    return not _pid_alive(pid)


@pytest.mark.live_system_guard_bypass
def test_rg_child_dies_with_a_sigkilled_caller(tree, ops_factory, tmp_path):
    """A caller SIGKILLed mid-wait must take the rg subprocess down with it (the
    #797 orphan class). The group is owned by this process's owner-death
    supervisor, so a worker reclaim / turn interrupt that kills us -9 still reaps
    the search subprocess even though no Python cleanup ran."""
    pytest.importorskip("psutil")
    import signal
    import subprocess
    import sys

    import tools as _tools_pkg
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(_tools_pkg.__file__)))
    pid_file = tmp_path / "rg-child.pid"
    # A fresh caller runs the REAL transport on a long sleep stand-in (rg would
    # read nothing for 300 s), writes its own $$ then execs sleep, so the spawned
    # child IS the sleeper and leads its own group; the fixed transport registers
    # that group with ITS owner-death supervisor and then blocks in the wait.
    script = f"echo $$ > {shlex.quote(str(pid_file))}; exec sleep 300"
    child_argv = [
        sys.executable, "-c",
        "import sys\n"
        "sys.path.insert(0, sys.argv[3])\n"
        "from tools.environments.local import LocalEnvironment\n"
        "from tools.file_operations import ShellFileOperations\n"
        "ops = ShellFileOperations(LocalEnvironment(cwd=sys.argv[2]), cwd=sys.argv[2])\n"
        "ops._run_rg_native(['sh', '-c', sys.argv[4]], 5, timeout=300)\n",
        "_caller", str(tree), repo_root, shlex.quote(script),
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = repo_root + os.pathsep + env.get("PYTHONPATH", "")
    caller = subprocess.Popen(child_argv, cwd=repo_root, env=env,
                              stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not pid_file.exists():
            time.sleep(0.05)
        assert pid_file.exists(), "search subprocess never reported its pid"
        child_pid = int(pid_file.read_text().strip())
        assert _pid_alive(child_pid), f"search subprocess {child_pid} never started"
        time.sleep(0.5)  # let the owner-death supervisor consume the register line
        # SIGKILL the caller: no atexit / finally / interrupt handler runs.
        caller.kill()
        caller.wait(timeout=10)
        assert caller.returncode == -int(signal.SIGKILL)
        assert _gone_within(child_pid, timeout=15.0), (
            f"search subprocess {child_pid} SURVIVED a SIGKILLed caller — the #797 "
            f"2.3 GiB rg orphan class. Its group must be owned by the process's "
            f"owner-death supervisor (own_process_groups) so it dies with the caller."
        )
    finally:
        try:
            if pid_file.exists():
                os.kill(int(pid_file.read_text().strip()), signal.SIGKILL)
        except (OSError, ValueError, ProcessLookupError):
            pass
        if caller.poll() is None:
            caller.kill()
            with contextlib.suppress(Exception):
                caller.wait(timeout=5)
