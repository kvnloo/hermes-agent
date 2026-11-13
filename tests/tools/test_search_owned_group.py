"""The native rg search lane dies with the Hermes process that started it.

``_run_rg_native`` puts rg in its own session/process group so a killpg aimed at the group can
never reach Hermes, and kills that group when its own waiter sees the deadline or a /stop. Both
run in the OWNER: a caller timeout, a worker reclaim or a turn interrupt that kills the Hermes
process leaves the group nothing to kill it, and rg reparents to init still walking the tree
(measured: ``timeout 58 python real_call.py`` on a whole-disk root left an ``rg --files`` reading
for 2 m 11 s, 2.34 GiB, until it was killed by hand). The group now goes to the per-process
owner-death supervisor, exactly as ``LocalEnvironment._run_bash`` does for shell commands, and is
handed back once the search's wait returns.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import psutil
import pytest

from tools.environments.local import LocalEnvironment
from tools.file_operations import ShellFileOperations
from tools.file_operations_search import SearchMixin
from hermes_cli import process_identity
from tests.waiting import wait_until

pytestmark = pytest.mark.platforms("posix")  # native rg lane is POSIX-only

REPO = str(Path(__file__).resolve().parents[2])
CHILD = "sleep 300"  # a silent rg: no output, so only the owner's death can stop it


@pytest.fixture(scope="module")
def _local_env(tmp_path_factory):
    return LocalEnvironment(cwd=str(tmp_path_factory.mktemp("owned-search")))


@pytest.fixture
def ops(_local_env, tmp_path):
    for name in ("a.py", "b.py"):
        (tmp_path / name).write_text("needle\n", encoding="utf-8")
    _local_env.cwd = str(tmp_path)
    return ShellFileOperations(_local_env, cwd=str(tmp_path))


def _alive(pid: int) -> bool:
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def test_the_search_group_is_owned_on_spawn_and_released_after_the_wait(ops, monkeypatch):
    """The real ``rg --files`` path: own on spawn, hand back once the search returned."""
    calls: list = []
    monkeypatch.setattr(SearchMixin, "_own_group", lambda self, pgid: calls.append(("own", pgid)), raising=False)
    monkeypatch.setattr(SearchMixin, "_release_group", lambda self, pgid, proc=None: calls.append(("release", pgid)), raising=False)
    result = ops.search(pattern="*.py", path=ops.cwd, target="files")
    assert not result.error and result.total_count == 2, result.to_dict()
    owned = [pgid for verb, pgid in calls if verb == "own"]
    assert len(owned) == 1, calls
    assert os.getpgid(0) != owned[0], "the search child must lead its own group"
    assert calls[-1] == ("release", owned[0]), calls


def test_a_sigkilled_owner_takes_the_search_child_with_it(tmp_path):
    """End to end through the real supervisor: the owner dies by SIGKILL while awaiting rg.
    No Python cleanup runs in it, so nothing but the supervisor can stop the walk."""
    owner_src = textwrap.dedent(f"""
        import os, sys, threading, time
        sys.path.insert(0, {REPO!r})
        from tools.environments.local import LocalEnvironment
        from tools.file_operations import ShellFileOperations
        cwd = {str(tmp_path)!r}
        env = LocalEnvironment(cwd=cwd)
        ops = ShellFileOperations(env, cwd=cwd)
        threading.Thread(target=lambda: ops._run_rg_native(["sh", "-c", {CHILD!r}], 5, timeout=600),
                         daemon=True).start()
        import psutil
        me = psutil.Process()
        child = None
        deadline = time.monotonic() + 15
        while child is None and time.monotonic() < deadline:
            for kid in me.children(recursive=True):
                if {CHILD!r} in " ".join(kid.cmdline()):
                    child = kid
                    break
            time.sleep(0.05)
        if child is None:
            sys.exit("owner never saw the search child")
        print(child.pid, os.getpgid(child.pid), flush=True)
        time.sleep(300)
    """)
    home = tmp_path / "home"
    home.mkdir()
    env = dict(os.environ, HERMES_HOME=str(home), HOME=str(home),
               PYTHONPATH=REPO, PYTHONUNBUFFERED="1")
    owner = subprocess.Popen([sys.executable, "-c", owner_src], env=env, cwd=REPO,
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
    line = owner.stdout.readline().split()
    if len(line) != 2:
        owner.kill()
        pytest.fail(f"owner did not start the search: {line!r} {owner.communicate(timeout=10)[1][-2000:]}")
    child, pgid = int(line[0]), int(line[1])
    assert pgid == child, "the search child leads its own group"
    try:
        owner.kill()
        owner.wait(timeout=10)
        wait_until(lambda: not _alive(child) and not _alive(pgid), timeout=15,
                   what="the rg child and its group to die with the kill -9'd owner")
    finally:
        for pid in (pgid, child):
            try:
                os.kill(pid, 9)  # windows-footgun: ok — posix-marked test
            except (ProcessLookupError, PermissionError):
                pass
        if owner.poll() is None:
            owner.kill()
        owner.communicate(timeout=10)
        process_identity._supervised_pgids.clear()


def test_a_live_owner_keeps_the_search_child(tmp_path):
    """Control: while the owner lives, the supervisor touches nothing."""
    owner_src = textwrap.dedent(f"""
        import os, sys, threading, time
        sys.path.insert(0, {REPO!r})
        from tools.environments.local import LocalEnvironment
        from tools.file_operations import ShellFileOperations
        cwd = {str(tmp_path)!r}
        env = LocalEnvironment(cwd=cwd)
        ops = ShellFileOperations(env, cwd=cwd)
        threading.Thread(target=lambda: ops._run_rg_native(["sh", "-c", {CHILD!r}], 5, timeout=600),
                         daemon=True).start()
        import psutil
        me = psutil.Process()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            kids = [k for k in me.children(recursive=True) if {CHILD!r} in " ".join(k.cmdline())]
            if kids:
                print(kids[0].pid, flush=True)
                break
            time.sleep(0.05)
        else:
            sys.exit("owner never saw the search child")
        time.sleep(300)
    """)
    home = tmp_path / "home"
    home.mkdir()
    env = dict(os.environ, HERMES_HOME=str(home), HOME=str(home),
               PYTHONPATH=REPO, PYTHONUNBUFFERED="1")
    owner = subprocess.Popen([sys.executable, "-c", owner_src], env=env, cwd=REPO,
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
    line = owner.stdout.readline().split()
    if len(line) != 1:
        owner.kill()
        pytest.fail(f"owner did not start the search: {line!r} {owner.communicate(timeout=10)[1][-2000:]}")
    child = int(line[0])
    supervisor = [p for p in psutil.Process(owner.pid).children()
                  if "process_supervisor.sh" in " ".join(p.cmdline())]
    try:
        assert supervisor, "the owner should have started its owner-death supervisor"
        # Give a wrongly-armed supervisor its full TERM -> 3 s -> KILL window to act.
        with pytest.raises(AssertionError):
            wait_until(lambda: not _alive(child), timeout=5, what="(control) a search-child death")
        assert _alive(child) and owner.poll() is None
    finally:
        try:
            os.kill(child, 9)  # windows-footgun: ok — posix-marked test
        except (ProcessLookupError, PermissionError):
            pass
        owner.kill()
        owner.communicate(timeout=10)
        process_identity._supervised_pgids.clear()
