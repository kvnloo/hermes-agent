"""PROBE (not the regression contract): a sandbox command that ignores SIGTERM.

Host kills escalate to SIGKILL after terminal.daemon_term_grace_seconds; does the
sandbox kill path?  Original docstring of the regression file follows.

#125003: killing a sandbox background process stops the command it launched.

``spawn_via_env`` records the PID of a wrapper subshell. A kill that signals only
that PID orphans the user's ``nohup bash -lc CMD`` and everything it started:
they keep running inside the sandbox while Hermes reports ``killed``, and the
exit file is never written.

Drives the real ``spawn_via_env`` and ``kill_process`` against real bash: the
real ``LocalEnvironment`` (fresh ``bash -c`` per call in its own session, the
spawn model every remote backend uses) and a plain ``bash -c`` env that shares
the caller's process group.
"""

import subprocess
import time
from unittest.mock import patch

import psutil
import pytest

import tools.process_registry as process_registry_mod
from tools.process_registry import ProcessRegistry

pytestmark = pytest.mark.platforms("posix")

_BOUND_S = 5.0


class _PlainBashEnv:
    """``bash -c`` per call in the caller's own process group (output via a file,
    so a backgrounded wrapper holding stdout cannot stall the call)."""

    def __init__(self, temp_dir):
        self._temp_dir = temp_dir
        self._calls = 0

    def get_temp_dir(self):
        return self._temp_dir

    def execute(self, command, timeout=10, **_kw):
        self._calls += 1
        out = f"{self._temp_dir}/exec-{self._calls}.out"
        with open(out, "w") as fh:
            rc = subprocess.run(["bash", "-c", command], stdin=subprocess.DEVNULL, stdout=fh,
                                stderr=subprocess.STDOUT, timeout=timeout).returncode
        with open(out) as fh:
            return {"output": fh.read(), "returncode": rc}

    def cleanup(self):
        pass


def _local_env(tmp_path, temp_dir):
    from tools.environments.local import LocalEnvironment

    env = LocalEnvironment(cwd=str(tmp_path), timeout=30)
    env.get_temp_dir = lambda: temp_dir
    return env


def _alive(pid):
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def _wait_for(predicate, bound=_BOUND_S):
    deadline = time.monotonic() + bound
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


@pytest.fixture(autouse=True)
def _no_systemd_scope():
    original = process_registry_mod._SYSTEMD_SCOPE_AVAILABLE
    process_registry_mod._SYSTEMD_SCOPE_AVAILABLE = False
    yield
    process_registry_mod._SYSTEMD_SCOPE_AVAILABLE = original


@pytest.fixture(params=["local_env", "plain_bash"])
def sandbox(request, tmp_path):
    art = tmp_path / "sandbox_tmp"
    art.mkdir()
    env = _local_env(tmp_path, str(art)) if request.param == "local_env" else _PlainBashEnv(str(art))
    yield env, art
    env.cleanup()


@pytest.fixture()
def spawn_and_kill(sandbox, tmp_path):
    """Spawn ``command`` through spawn_via_env (sandbox poller stubbed), wait for its
    PID markers, kill it through the registry. Leftover marker PIDs are SIGKILLed."""
    env, art = sandbox
    registry = ProcessRegistry()
    recorded = []

    def _run(command, markers):
        paths = [tmp_path / name for name in markers]
        with patch.object(registry, "_env_poller_loop", lambda *a, **k: None), \
                patch.object(registry, "_write_checkpoint"):
            session = registry.spawn_via_env(env, command.format(*paths))
            assert session.pid, f"launch failed: {session.output_buffer!r}"
            assert _wait_for(lambda: all(p.exists() and p.read_text().strip() for p in paths))
            pids = [int(p.read_text()) for p in paths]
            recorded.extend(psutil.Process(pid) for pid in pids)
            assert all(_alive(pid) for pid in pids)
            result = registry.kill_process(session.id)
        return session, pids, result, art / f"hermes_bg_{session.id}.exit"

    yield _run
    # Survivors are reparented outside the test's subtree, where the conftest
    # live-system guard refuses os.kill; kill(1) them, identity-checked first.
    for proc in recorded:
        if proc.is_running():
            subprocess.run(["kill", "-9", str(proc.pid)], check=False)



def test_probe_kill_stops_a_command_that_ignores_sigterm(spawn_and_kill):
    _session, pids, result, exit_file = spawn_and_kill(
        "trap '' TERM; echo $$ > {0}; sleep 300 & echo $! > {1}; wait", ["shell.pid", "child.pid"])

    assert result["status"] == "killed"
    assert _wait_for(lambda: not any(_alive(p) for p in pids), bound=8.0), (
        "survived: " + ", ".join(n for n, p in zip(("shell", "child"), pids) if _alive(p)))
