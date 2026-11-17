"""The gateway puts each managed turn under the host's per-profile sandbox wrapper when one is set."""
import sys

from gateway import session_managed_worker as smw


def _no_scope(monkeypatch):
    import tools.process_registry as pr
    monkeypatch.setattr(pr, "turn_scope_argv", lambda argv, label: argv)


def test_unset_wrapper_leaves_worker_argv_unchanged(monkeypatch):
    _no_scope(monkeypatch)
    monkeypatch.delenv("HERMES_TURN_SANDBOX", raising=False)
    argv, _ = smw._turn_scoped({}, "s1", "/h/profiles/ayo")
    assert argv == [sys.executable, "-m", "agent.managed_worker"]


def test_named_profile_runs_inside_its_sandbox(monkeypatch):
    _no_scope(monkeypatch)
    monkeypatch.setenv("HERMES_TURN_SANDBOX", "/x/hermes-profile-sandbox")
    argv, _ = smw._turn_scoped({}, "s1", "/h/profiles/ayo")
    assert argv == ["/x/hermes-profile-sandbox", "run", "ayo", "--", sys.executable, "-m", "agent.managed_worker"]


def test_root_home_is_the_default_profile(monkeypatch):
    _no_scope(monkeypatch)
    monkeypatch.setenv("HERMES_TURN_SANDBOX", "/x/w")
    argv, _ = smw._turn_scoped({}, "s1", "/workspace/hermes-home")
    assert argv[:4] == ["/x/w", "run", "default", "--"]


def test_scope_wraps_the_sandbox_and_gets_the_bus(monkeypatch):
    import tools.process_registry as pr
    monkeypatch.setattr(pr, "turn_scope_argv", lambda argv, label: ["systemd-run", "--scope", "--", *argv])
    monkeypatch.setattr(pr, "systemd_user_bus_env", lambda env: {"XDG_RUNTIME_DIR": "/run/user/1"})
    monkeypatch.setenv("HERMES_TURN_SANDBOX", "/x/w")
    argv, env = smw._turn_scoped({}, "s1", "/h/profiles/clean")
    assert argv[:7] == ["systemd-run", "--scope", "--", "/x/w", "run", "clean", "--"]
    assert env["XDG_RUNTIME_DIR"] == "/run/user/1"


def _hello_from(argv):
    """Spawn ``argv`` the way the owner does and read the worker's hello (pid as IT sees itself)."""
    import json
    import subprocess
    code = ("import json,os,psutil;from hermes_cli.process_identity import worker_birth;"
            "print(json.dumps({'type':'hello','pid':os.getpid(),'birth':worker_birth(psutil.Process()),"
            "'ancestors':[]}),flush=True);import time;time.sleep(30)")
    proc = subprocess.Popen([*argv, sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    assert proc.stdout is not None
    return proc, json.loads(proc.stdout.readline())


def test_owner_maps_a_pid_namespace_worker_to_its_host_pid():
    import shutil
    import pytest
    from gateway.session_worker_reservation import verify_worker_identity
    if not shutil.which("bwrap") or sys.platform != "linux":
        pytest.skip("needs bwrap")
    proc, hello = _hello_from(["bwrap", "--unshare-user", "--unshare-pid", "--die-with-parent",
                               "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--"])
    try:
        pid, birth = verify_worker_identity(proc, hello)
        assert pid != hello["pid"] and birth == hello["birth"]  # host pid, proven by NSpid + birth
        import psutil
        assert psutil.Process(pid).parents()[0].pid in (proc.pid, *[c.pid for c in psutil.Process(proc.pid).children(True)])
    finally:
        proc.kill()


def test_a_namespace_pid_never_names_a_process_outside_the_spawned_tree():
    import os
    import pytest
    from gateway.session_worker_reservation import verify_worker_identity
    from hermes_state_runtime import RuntimeStoreError
    proc, hello = _hello_from([])
    try:
        forged = dict(hello, pid=os.getppid())  # a real process, but not ours
        with pytest.raises(RuntimeStoreError):
            verify_worker_identity(proc, forged)
    finally:
        proc.kill()
