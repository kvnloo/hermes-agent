"""W1 salvage regression: a routed profile's terminal.home_mode must reach its
terminal scope (defect A) and drive subprocess HOME under that scope (defect B).
Adapted from kvnloo fork #40 (tests/tools/test_terminal_scope_multiplex.py,
tests/test_subprocess_home_isolation.py)."""

import pytest


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    monkeypatch.setattr("agent.secret_scope.build_profile_secret_scope", lambda _h: {})
    monkeypatch.setattr("hermes_cli.env_loader.hydrate_profile_secret_sources", lambda _h: None)
    import hermes_constants

    monkeypatch.setattr(hermes_constants, "is_container", lambda: False)
    yield


def _profile(tmp_path, name, config_yaml):
    home = tmp_path / "profiles" / name
    home.mkdir(parents=True)
    (home / "config.yaml").write_text(config_yaml, encoding="utf-8")
    return home


@pytest.mark.parametrize("cfg, expected", [
    ("terminal:\n  backend: local\n  home_mode: profile\n", "profile"),
    ("terminal:\n  backend: local\n", "auto"),
])
def test_profile_terminal_scope_projects_home_mode(tmp_path, monkeypatch, cfg, expected):
    """Defect A: build_profile_terminal_scope must carry TERMINAL_HOME_MODE
    (the profile's value, else the defined default) like every peer key."""
    from tools.terminal_scope import build_profile_terminal_scope

    monkeypatch.setenv("TERMINAL_HOME_MODE", "real")  # ambient launch value must not matter
    scope = build_profile_terminal_scope(_profile(tmp_path, "p", cfg))
    assert scope.get("TERMINAL_HOME_MODE") == expected


@pytest.mark.parametrize("routed_mode, ambient_mode, expect_profile_home", [
    ("profile", "auto", True),   # routed profile asks for its own HOME
    ("auto", "profile", False),  # routed profile must not inherit the launch profile's mode
])
def test_routed_profile_home_mode_drives_subprocess_home(
        tmp_path, monkeypatch, routed_mode, ambient_mode, expect_profile_home):
    """Defect B: under a multiplexed gateway turn, get_subprocess_home honours
    the routed profile's home_mode, not the launch process's TERMINAL_HOME_MODE."""
    import gateway.run as gw
    from hermes_constants import get_subprocess_home

    monkeypatch.setenv("TERMINAL_HOME_MODE", ambient_mode)
    home = _profile(tmp_path, "routed", f"terminal:\n  backend: local\n  home_mode: {routed_mode}\n")
    (home / "home").mkdir()
    real_home = tmp_path / "real-home"
    real_home.mkdir()
    monkeypatch.setenv("HOME", str(real_home))

    with gw._profile_runtime_scope(home):
        got = get_subprocess_home()
    assert got == (str(home / "home") if expect_profile_home else None)
