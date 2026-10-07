"""Sandbox (env-backed) background jobs: worker PID capture + tree-kill.

spawn_via_env wraps the user's command in a wrapper subshell and stores that
subshell's PID as session.pid. The real worker (``nohup bash -lc CMD``) is a
descendant of the wrapper, so signaling only session.pid SIGTERMs the wrapper
and leaves the worker (and its children) reparented to PID 1 inside the sandbox
and still running. The fix captures the worker's own PID into a separate
``.worker_pid`` file and has kill_process tree-kill that worker before reaping
the wrapper subshell.
"""

import os
import shlex
import shutil
import subprocess
import time

import pytest
from unittest.mock import MagicMock, patch

from tools.process_registry import ProcessRegistry, ProcessSession


@pytest.fixture()
def registry():
    """Create a fresh ProcessRegistry."""
    return ProcessRegistry()


@pytest.fixture(autouse=True)
def _reset_systemd_scope_cache():
    """Reset the cached ``systemd-run --user --scope`` availability flag
    before each test so a probe run on a real systemd host (where
    ``INVOCATION_ID`` is set) doesn't leak into tests that mock
    ``subprocess.Popen``."""
    import tools.process_registry as _pr

    original = _pr._SYSTEMD_SCOPE_AVAILABLE
    _pr._SYSTEMD_SCOPE_AVAILABLE = False
    yield
    _pr._SYSTEMD_SCOPE_AVAILABLE = original


def _make_session(
    sid="proc_test123",
    command="echo hello",
    task_id="t1",
    exited=False,
    exit_code=None,
    output="",
    started_at=None,
) -> ProcessSession:
    """Helper to create a ProcessSession for testing."""
    s = ProcessSession(
        id=sid,
        command=command,
        task_id=task_id,
        started_at=started_at or time.time(),
        exited=exited,
        exit_code=exit_code,
        output_buffer=output,
    )
    return s


class _FakeSandboxEnv:
    """Stub environment that records every execute() call and returns canned
    output for the worker-PID file read. Used to assert the kill command
    structure without spawning real processes."""

    def __init__(self, cat_output="99\n", execute_raises_on=()):
        self.commands = []
        self._cat = cat_output
        self._raises_on = tuple(execute_raises_on)

    def execute(self, command, timeout=10, **kwargs):
        self.commands.append((command, kwargs))
        for pat in self._raises_on:
            if pat in command:
                raise RuntimeError(f"injected failure matching {pat!r}")
        if command.startswith("cat ") and ".worker_pid" in command:
            return {"output": self._cat, "returncode": 0}
        return {"output": "", "returncode": 0}


class TestSpawnViaEnvWorkerPid:
    """spawn_via_env must record the nohup'd worker PID separately from the
    wrapper subshell PID it stores as session.pid, so the kill path can target
    the real worker."""

    def test_records_worker_pid_path_and_waits_on_worker(self, registry):
        class FakeEnv:
            def __init__(self):
                self.commands = []

            def get_temp_dir(self):
                return "/tmp"

            def execute(self, command, **kwargs):
                self.commands.append(command)
                return {"output": "123\n", "returncode": 0}

        env = FakeEnv()
        fake_thread = MagicMock()
        with patch("tools.process_registry.threading.Thread",
                   return_value=fake_thread), \
             patch.object(registry, "_write_checkpoint"):
            session = registry.spawn_via_env(env, "echo hello")

        assert session.pid == 123
        assert session.worker_pid_path == f"/tmp/hermes_bg_{session.id}.worker_pid"
        bg = env.commands[0]
        # The worker is backgrounded inside the wrapper subshell and its PID
        # captured to its own file, then waited on so the wrapper stays alive
        # (and ``kill -0 $session.pid`` keeps reflecting worker liveness).
        assert "WPID=$!" in bg
        assert 'echo "$WPID"' in bg
        assert ".worker_pid" in bg
        assert 'wait "$WPID"' in bg
        # Exit-code capture path is unchanged.
        assert "printf '%s\\n' \"$rc\"" in bg
        # The wrapper subshell PID is still echoed to the .pid file.
        assert "echo $!" in bg
        fake_thread.start.assert_called_once()


class TestKillProcessSandbox:
    """kill_process for pid_scope='sandbox' must tree-kill the nohup'd worker
    (read from session.worker_pid_path) and only then reap the wrapper subshell
    stored as session.pid. Killing only the wrapper leaks the worker."""

    @staticmethod
    def _sandbox_session(registry, sid, worker_pid_path):
        s = _make_session(sid=sid, command="sleep 999")
        s.pid = 4242
        s.pid_scope = "sandbox"
        s.worker_pid_path = worker_pid_path
        registry._running[s.id] = s
        return s

    def test_tree_kills_worker_then_wrapper(self, registry):
        env = _FakeSandboxEnv(cat_output="99\n")
        s = self._sandbox_session(
            registry, "proc_sb", "/tmp/hermes_bg_proc_sb.worker_pid"
        )
        s.env_ref = env
        with patch.object(registry, "_write_checkpoint"):
            result = registry.kill_process(s.id)
        assert result["status"] == "killed"
        cmds = [c for c, _ in env.commands]
        # 1) read the worker pid from its file
        assert any(c.startswith("cat ") and ".worker_pid" in c for c in cmds)
        # 2) SIGTERM the worker + direct children, then SIGKILL survivors
        tree_kill = [c for c in cmds if "pkill -P 99" in c and "kill 99" in c]
        assert tree_kill, f"expected a worker tree-kill command, got {cmds}"
        assert "pkill -9 -P 99" in tree_kill[0]
        assert "kill -9 99" in tree_kill[0]
        assert "sleep 0.5" in tree_kill[0]
        # 3) then reap the wrapper subshell
        assert "kill 4242 2>/dev/null" in cmds
        # The worker tree-kill must run before the wrapper kill.
        assert cmds.index(tree_kill[0]) < cmds.index("kill 4242 2>/dev/null")

    def test_legacy_session_without_worker_pid_falls_back_to_wrapper_kill(self, registry):
        # A session spawned before the fix has no worker_pid_path: must still
        # terminate the wrapper (historical behavior) and report killed.
        env = _FakeSandboxEnv()
        s = _make_session(sid="proc_legacy", command="sleep 999")
        s.pid = 4242
        s.pid_scope = "sandbox"
        s.env_ref = env
        s.worker_pid_path = ""
        registry._running[s.id] = s
        with patch.object(registry, "_write_checkpoint"):
            result = registry.kill_process(s.id)
        assert result["status"] == "killed"
        cmds = [c for c, _ in env.commands]
        assert "kill 4242 2>/dev/null" in cmds
        assert not any("pkill" in c for c in cmds), \
            "no worker tree-kill should be attempted without a worker pid"
        assert not any(c.startswith("cat ") and ".worker_pid" in c for c in cmds)

    def test_corrupt_worker_pid_skips_tree_kill(self, registry):
        # A non-numeric worker pid must not be interpolated into a kill command
        # (no shell injection) and must not skip the wrapper kill.
        env = _FakeSandboxEnv(cat_output="not-a-pid\n")
        s = self._sandbox_session(
            registry, "proc_corrupt", "/tmp/hermes_bg_proc_corrupt.worker_pid"
        )
        s.env_ref = env
        with patch.object(registry, "_write_checkpoint"):
            result = registry.kill_process(s.id)
        assert result["status"] == "killed"
        cmds = [c for c, _ in env.commands]
        assert not any("pkill" in c for c in cmds)
        assert "kill 4242 2>/dev/null" in cmds

    def test_worker_pid_read_failure_still_kills_wrapper(self, registry):
        # If execute() raises while reading the worker pid (dead sandbox,
        # transient error), the wrapper kill must still run and kill_process
        # must not crash.
        env = _FakeSandboxEnv(execute_raises_on=(".worker_pid",))
        s = self._sandbox_session(
            registry, "proc_raise", "/tmp/hermes_bg_proc_raise.worker_pid"
        )
        s.env_ref = env
        with patch.object(registry, "_write_checkpoint"):
            result = registry.kill_process(s.id)
        assert result["status"] == "killed"
        cmds = [c for c, _ in env.commands]
        assert "kill 4242 2>/dev/null" in cmds
        assert not any("pkill" in c for c in cmds)


class _RealBashEnv:
    """Executes sandbox commands in a real local ``bash -c`` so the actual
    spawn/kill bg_command is exercised against real processes — the gap the
    FakeEnv tests can't cover (they never spawn a real process tree).

    stdout is redirected to a regular file (not a pipe) so the wait returns
    as soon as the foreground command exits; the backgrounded worker inherits
    the file's fd but never blocks on it, mimicking how ``docker exec`` returns
    at foreground-exit rather than waiting for the inherited stdout pipe to
    reach EOF.
    """

    def __init__(self, temp_dir):
        self.temp_dir = temp_dir
        self._counter = 0

    def get_temp_dir(self):
        return self.temp_dir

    def execute(self, command, timeout=10, **kwargs):
        out_path = os.path.join(self.temp_dir, f"_execout_{os.getpid()}_{self._counter}")
        self._counter += 1
        with open(out_path, "wb") as outf:
            proc = subprocess.Popen(
                ["bash", "-c", command],
                stdout=outf,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
        try:
            with open(out_path, "rb") as f:
                out = f.read()
        finally:
            try:
                os.remove(out_path)
            except OSError:
                pass
        return {"output": out.decode("utf-8", "replace"), "returncode": proc.returncode}


def _read_env_pid(env, path, attempts=60, delay=0.1):
    """Poll a sandbox PID file until it contains a numeric PID (the wrapper
    subshell writes it asynchronously after backgrounding the worker)."""
    quoted = shlex.quote(path)
    for _ in range(attempts):
        out = env.execute(f"cat {quoted} 2>/dev/null", timeout=5)
        val = (out.get("output", "") or "").strip()
        if val.isdigit():
            return int(val)
        time.sleep(delay)
    return None


@pytest.mark.skipif(not shutil.which("bash"), reason="needs a POSIX bash")
class TestSandboxKillEndToEnd:
    """Spawn a real worker through the actual spawn_via_env bg_command and
    confirm kill_process terminates it. On the buggy code the wrapper dies but
    the nohup'd worker is reparented to PID 1 and survives — these tests
    fail against that version."""

    @staticmethod
    def _spawn(registry, env, command):
        fake_thread = MagicMock()
        with patch("tools.process_registry.threading.Thread",
                   return_value=fake_thread), \
             patch.object(registry, "_write_checkpoint"):
            return registry.spawn_via_env(env, command)

    @staticmethod
    def _alive(env, pid):
        out = env.execute(f"kill -0 {pid} 2>/dev/null; echo $?", timeout=5)
        return out["output"].strip().splitlines()[-1] == "0"

    def test_kill_terminates_real_worker(self, registry, tmp_path):
        env = _RealBashEnv(str(tmp_path))
        session = self._spawn(registry, env, "sleep 120")
        try:
            assert session.pid is not None
            worker_pid = _read_env_pid(env, session.worker_pid_path)
            assert worker_pid is not None, "worker pid file was never written"
            assert worker_pid != session.pid, \
                "worker pid must be distinct from the wrapper subshell pid"
            assert self._alive(env, worker_pid), "worker should be running"

            with patch.object(registry, "_write_checkpoint"):
                result = registry.kill_process(session.id)

            assert result["status"] == "killed"
            assert not self._alive(env, worker_pid), \
                "worker survived kill_process — the sandbox kill leaked it"
        finally:
            try:
                env.execute(f"kill -9 {worker_pid} 2>/dev/null", timeout=5)
            except Exception:
                pass

    def test_kill_terminates_real_worker_and_its_child(self, registry, tmp_path):
        # A worker that spawns its own child: ``pkill -P <worker>`` must reap
        # the direct child too, not only the worker itself.
        env = _RealBashEnv(str(tmp_path))
        session = self._spawn(registry, env, "sleep 120 & wait")
        worker_pid = None
        try:
            assert session.pid is not None
            worker_pid = _read_env_pid(env, session.worker_pid_path)
            assert worker_pid is not None
            assert self._alive(env, worker_pid)
            # Find the worker's direct child (the backgrounded sleep). Poll
            # until a LIVE child is found: ``bash -lc`` login-shell startup
            # sources profile scripts that fork transient subprocesses, and a
            # ``pgrep`` that lands during that window can return a PID that
            # has already exited by the time we probe liveness — a false
            # flake rather than a real bug. Filter to ``sleep`` to skip
            # profile-script stragglers outright.
            child_pid = None
            for _ in range(60):
                cout = env.execute(
                    f"pgrep -P {worker_pid} -x sleep 2>/dev/null | head -n1",
                    timeout=5,
                )
                cand = cout["output"].strip().splitlines()
                cand = cand[0] if cand else ""
                if cand.isdigit() and self._alive(env, int(cand)):
                    child_pid = int(cand)
                    break
                time.sleep(0.1)
            assert child_pid is not None, "worker should have a live child to reap"

            with patch.object(registry, "_write_checkpoint"):
                result = registry.kill_process(session.id)

            assert result["status"] == "killed"
            assert not self._alive(env, worker_pid), "worker leaked"
            assert not self._alive(env, child_pid), "worker's child leaked"
        finally:
            try:
                if worker_pid:
                    env.execute(
                        f"pkill -9 -P {worker_pid} 2>/dev/null; "
                        f"kill -9 {worker_pid} 2>/dev/null",
                        timeout=5,
                    )
            except Exception:
                pass


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
