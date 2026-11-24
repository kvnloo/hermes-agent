"""Opt-in memory cap for foreground local terminal commands (#56865), on every platform.

Field case (macOS, where no cgroup exists): an agent ran ``timeout 560 npm run verify:room``.
A Node ``assert.deepEqual`` over two PNG screenshot Buffers built a diff that grew to
~395 GB of footprint. Jetsam SIGKILLed the ``timeout`` wrapper, so bash returned
``rc=137`` and the tool call ended. But ``timeout`` had put node in its own process group,
and node ran on for 19 h with the host in swap. ``TERMINAL_LOCAL_MEMORY_MAX_MB`` stops the
command while it is still in flight, escaped process groups included.
"""
import contextlib
import os
import sys
import textwrap
import time

import pytest

from tools.environments.local import LocalEnvironment

pytestmark = pytest.mark.skipif(os.name == "nt", reason="the escape uses POSIX setpgid")


@pytest.fixture(autouse=True)
def _isolate_hermes_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "logs").mkdir(exist_ok=True)


def _hog(tmp_path, mb: int, hold_s: int) -> str:
    """A command that leaves the shell's process group (as ``timeout`` does), touches ``mb``
    MiB, writes its pid, then holds the memory for ``hold_s`` seconds."""
    script = tmp_path / "hog.py"
    pidfile = tmp_path / "hog.pid"
    script.write_text(textwrap.dedent(f"""
        import os, time
        os.setpgid(0, 0)
        held = b"\\x01" * ({mb} << 20)
        open({str(pidfile)!r}, "w").write(str(os.getpid()))
        time.sleep({hold_s})
    """))
    return f"{sys.executable} {script} > /dev/null 2>&1; echo after-hog"


def _alive(pid: int) -> bool:
    import psutil
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


@pytest.mark.live_system_guard_bypass  # the hog escapes to its own group; the cap (or a red run's cleanup) must kill it
def test_cap_kills_a_command_tree_over_the_limit(tmp_path, monkeypatch):
    import psutil
    monkeypatch.setenv("TERMINAL_LOCAL_MEMORY_MAX_MB", "128")
    env = LocalEnvironment(cwd=str(tmp_path))
    pidfile = tmp_path / "hog.pid"
    try:
        t0 = time.monotonic()
        result = env.execute(_hog(tmp_path, 400, 30), timeout=60)
        elapsed = time.monotonic() - t0
        pid = int(pidfile.read_text())
        assert result.get("hermes_memory_capped") is True, result
        assert "TERMINAL_LOCAL_MEMORY_MAX_MB=128" in result["output"], result["output"]
        assert elapsed < 20, f"command ran {elapsed:.1f}s: the cap did not stop it"
        deadline = time.monotonic() + 5
        while _alive(pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not _alive(pid), "the process that escaped the shell's group outlived the cap"
    finally:
        if pidfile.exists():
            with contextlib.suppress(psutil.Error, ValueError):
                psutil.Process(int(pidfile.read_text())).kill()
        env.cleanup()


def test_no_cap_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("TERMINAL_LOCAL_MEMORY_MAX_MB", raising=False)
    env = LocalEnvironment(cwd=str(tmp_path))
    try:
        result = env.execute(_hog(tmp_path, 200, 1), timeout=60)
        assert result["returncode"] == 0, result
        assert "after-hog" in result["output"]
        assert not result.get("hermes_memory_capped")
    finally:
        env.cleanup()


@pytest.mark.parametrize("value", ["", "0", "-5", "abc", "32"])
def test_unset_invalid_or_tiny_values_leave_the_guard_off(monkeypatch, value):
    from tools.environments import local as local_mod
    monkeypatch.setenv("TERMINAL_LOCAL_MEMORY_MAX_MB", value)
    assert local_mod._foreground_memory_cap_mb() is None
