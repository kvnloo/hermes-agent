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
