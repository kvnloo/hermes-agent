"""Tests for subprocess HOME handling in profile mode.

Hermes state stays profile-scoped through HERMES_HOME. Host subprocesses should
keep the user's real HOME by default so external CLIs find existing credentials.
Containers still use the profile home for persistence, and users can explicitly
opt into profile HOME isolation on the host.

See: https://github.com/NousResearch/hermes-agent/issues/25114
See: https://github.com/NousResearch/hermes-agent/issues/36144
See: https://github.com/NousResearch/hermes-agent/issues/29015
"""

import os
import threading
from pathlib import Path

import hermes_constants



# ---------------------------------------------------------------------------
# get_subprocess_home()
# ---------------------------------------------------------------------------

class TestGetSubprocessHome:
    """Unit tests for hermes_constants.get_subprocess_home()."""

    def _host_mode(self, monkeypatch):
        monkeypatch.setattr(hermes_constants, "is_container", lambda: False)
        monkeypatch.delenv("TERMINAL_HOME_MODE", raising=False)
        monkeypatch.delenv("HERMES_REAL_HOME", raising=False)

    def _container_mode(self, monkeypatch):
        monkeypatch.setattr(hermes_constants, "is_container", lambda: True)
        monkeypatch.delenv("TERMINAL_HOME_MODE", raising=False)
        monkeypatch.delenv("HERMES_REAL_HOME", raising=False)



    def test_host_auto_keeps_real_home_when_profile_home_exists(self, tmp_path, monkeypatch):
        """Host installs should not hide real ~/.ssh, ~/.gitconfig, ~/.azure, etc."""
        self._host_mode(monkeypatch)
        real_home = tmp_path / "real-home"
        hermes_home = real_home / ".hermes" / "profiles" / "coder"
        profile_home = hermes_home / "home"
        profile_home.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(real_home))
        monkeypatch.setenv("HERMES_HOME", str(hermes_home))
        from hermes_constants import get_subprocess_home
        assert get_subprocess_home() is None

    def test_container_auto_uses_profile_home_when_home_dir_exists(self, tmp_path, monkeypatch):
        self._container_mode(monkeypatch)
        hermes_home = tmp_path / ".hermes"
        profile_home = hermes_home / "home"
        profile_home.mkdir(parents=True)
        monkeypatch.setenv("HERMES_HOME", str(hermes_home))
        from hermes_constants import get_subprocess_home
        assert get_subprocess_home() == str(profile_home)

    def test_returns_profile_specific_path(self, tmp_path, monkeypatch):
        """Explicit profile mode keeps the old per-profile HOME behavior."""
        self._host_mode(monkeypatch)
        profile_dir = tmp_path / ".hermes" / "profiles" / "coder"
        profile_dir.mkdir(parents=True)
        profile_home = profile_dir / "home"
        profile_home.mkdir()
        monkeypatch.setenv("TERMINAL_HOME_MODE", "profile")
        monkeypatch.setenv("HERMES_HOME", str(profile_dir))
        from hermes_constants import get_subprocess_home
        assert get_subprocess_home() == str(profile_home)

    def test_real_mode_repairs_parent_home_already_pointing_at_profile(self, tmp_path, monkeypatch):
        self._host_mode(monkeypatch)
        profile_dir = tmp_path / ".hermes" / "profiles" / "coder"
        profile_home = profile_dir / "home"
        profile_home.mkdir(parents=True)
        real_home = tmp_path / "real-home"
        real_home.mkdir()
        monkeypatch.setenv("TERMINAL_HOME_MODE", "real")
        monkeypatch.setenv("HERMES_HOME", str(profile_dir))
        monkeypatch.setenv("HOME", str(profile_home))
        monkeypatch.setenv("HERMES_REAL_HOME", str(real_home))

        from hermes_constants import get_subprocess_home, get_real_home

        assert get_real_home() == str(real_home)
        assert get_subprocess_home() == str(real_home)


    def test_two_profiles_get_different_homes(self, tmp_path, monkeypatch):
        self._container_mode(monkeypatch)
        base = tmp_path / ".hermes" / "profiles"
        for name in ("alpha", "beta"):
            p = base / name
            p.mkdir(parents=True)
            (p / "home").mkdir()

        from hermes_constants import get_subprocess_home

        monkeypatch.setenv("HERMES_HOME", str(base / "alpha"))
        home_a = get_subprocess_home()

        monkeypatch.setenv("HERMES_HOME", str(base / "beta"))
        home_b = get_subprocess_home()

        assert home_a is not None
        assert home_b is not None
        assert home_a != home_b
        assert home_a.endswith("alpha/home")
        assert home_b.endswith("beta/home")



# ---------------------------------------------------------------------------
# _make_run_env() injection
# ---------------------------------------------------------------------------

class TestMakeRunEnvHomeInjection:
    """Verify _make_run_env() applies the subprocess HOME policy."""

    def test_host_auto_preserves_real_home_when_profile_home_exists(self, tmp_path, monkeypatch):
        hermes_home = tmp_path / "hermes"
        hermes_home.mkdir()
        (hermes_home / "home").mkdir()
        real_home = tmp_path / "real-home"
        real_home.mkdir()
        monkeypatch.setattr(hermes_constants, "is_container", lambda: False)
        monkeypatch.setenv("HERMES_HOME", str(hermes_home))
        monkeypatch.setenv("HOME", str(real_home))
        monkeypatch.setenv("PATH", "/usr/bin:/bin")

        from tools.environments.local import _make_run_env
        result = _make_run_env({})

        assert result["HOME"] == str(real_home)
        assert result["HERMES_REAL_HOME"] == str(real_home)

    def test_profile_mode_injects_profile_home_when_profile_home_exists(self, tmp_path, monkeypatch):
        hermes_home = tmp_path / "hermes"
        hermes_home.mkdir()
        (hermes_home / "home").mkdir()
        real_home = tmp_path / "real-home"
        real_home.mkdir()
        monkeypatch.setattr(hermes_constants, "is_container", lambda: False)
        monkeypatch.setenv("TERMINAL_HOME_MODE", "profile")
        monkeypatch.setenv("HERMES_HOME", str(hermes_home))
        monkeypatch.setenv("HOME", str(real_home))
        monkeypatch.setenv("PATH", "/usr/bin:/bin")

        from tools.environments.local import _make_run_env
        result = _make_run_env({})

        assert result["HOME"] == str(hermes_home / "home")
        assert result["HERMES_REAL_HOME"] == str(real_home)

    def test_no_injection_when_home_dir_missing(self, tmp_path, monkeypatch):
        hermes_home = tmp_path / "hermes"
        hermes_home.mkdir()
        # No home/ subdirectory
        monkeypatch.setenv("HERMES_HOME", str(hermes_home))
        monkeypatch.setenv("HOME", "/root")
        monkeypatch.setenv("PATH", "/usr/bin:/bin")

        from tools.environments.local import _make_run_env
        result = _make_run_env({})

        assert result["HOME"] == "/root"

    def test_no_injection_when_hermes_home_unset(self, monkeypatch):
        monkeypatch.delenv("HERMES_HOME", raising=False)
        monkeypatch.setenv("HOME", "/home/user")
        monkeypatch.setenv("PATH", "/usr/bin:/bin")

        from tools.environments.local import _make_run_env
        result = _make_run_env({})

        assert result["HOME"] == "/home/user"



# ---------------------------------------------------------------------------
# _sanitize_subprocess_env() injection
# ---------------------------------------------------------------------------

class TestSanitizeSubprocessEnvHomeInjection:
    """Verify _sanitize_subprocess_env() applies the subprocess HOME policy."""

    def test_host_auto_preserves_real_home_when_profile_home_exists(self, tmp_path, monkeypatch):
        hermes_home = tmp_path / "hermes"
        hermes_home.mkdir()
        (hermes_home / "home").mkdir()
        real_home = tmp_path / "real-home"
        real_home.mkdir()
        monkeypatch.setattr(hermes_constants, "is_container", lambda: False)
        monkeypatch.setenv("HERMES_HOME", str(hermes_home))

        base_env = {"HOME": str(real_home), "PATH": "/usr/bin", "USER": "root"}
        from tools.environments.local import _sanitize_subprocess_env
        result = _sanitize_subprocess_env(base_env)

        assert result["HOME"] == str(real_home)
        assert result["HERMES_REAL_HOME"] == str(real_home)

    def test_profile_mode_injects_profile_home_when_profile_home_exists(self, tmp_path, monkeypatch):
        hermes_home = tmp_path / "hermes"
        hermes_home.mkdir()
        (hermes_home / "home").mkdir()
        real_home = tmp_path / "real-home"
        real_home.mkdir()
        monkeypatch.setattr(hermes_constants, "is_container", lambda: False)
        monkeypatch.setenv("TERMINAL_HOME_MODE", "profile")
        monkeypatch.setenv("HERMES_HOME", str(hermes_home))

        base_env = {"HOME": str(real_home), "PATH": "/usr/bin", "USER": "root"}
        from tools.environments.local import _sanitize_subprocess_env
        result = _sanitize_subprocess_env(base_env)

        assert result["HOME"] == str(hermes_home / "home")
        assert result["HERMES_REAL_HOME"] == str(real_home)

    def test_no_injection_when_home_dir_missing(self, tmp_path, monkeypatch):
        hermes_home = tmp_path / "hermes"
        hermes_home.mkdir()
        monkeypatch.setenv("HERMES_HOME", str(hermes_home))

        base_env = {"HOME": "/root", "PATH": "/usr/bin"}
        from tools.environments.local import _sanitize_subprocess_env
        result = _sanitize_subprocess_env(base_env)

        assert result["HOME"] == "/root"



# ---------------------------------------------------------------------------
# Profile bootstrap
# ---------------------------------------------------------------------------

class TestProfileBootstrap:
    """Verify new profiles get a home/ subdirectory."""

    def test_profile_dirs_includes_home(self):
        from hermes_cli.profiles import _PROFILE_DIRS
        assert "home" in _PROFILE_DIRS

    def test_create_profile_bootstraps_home_dir(self, tmp_path, monkeypatch):
        """create_profile() should create home/ inside the profile dir."""
        home = tmp_path / ".hermes"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("HERMES_HOME", str(home))

        from hermes_cli.profiles import create_profile
        profile_dir = create_profile("testbot", no_alias=True)
        assert (profile_dir / "home").is_dir()


# ---------------------------------------------------------------------------
# Scope-bound TERMINAL_HOME_MODE (profile multiplexing — #101242)
# ---------------------------------------------------------------------------

class TestGetSubprocessHomeScopeMode:
    """get_subprocess_home must read TERMINAL_HOME_MODE from the bound
    terminal scope under profile multiplexing, not the launch process's
    ambient os.environ value (#101242, commit 1cd736f)."""

    def _host(self, monkeypatch):
        monkeypatch.setattr(hermes_constants, "is_container", lambda: False)

    def _make_profile(self, tmp_path, monkeypatch):
        profile_dir = tmp_path / ".hermes" / "profiles" / "coder"
        profile_home = profile_dir / "home"
        profile_home.mkdir(parents=True)
        monkeypatch.setenv("HERMES_HOME", str(profile_dir))
        real_home = tmp_path / "real-home"
        real_home.mkdir()
        monkeypatch.setenv("HOME", str(real_home))
        return profile_dir, profile_home, real_home

    def test_scope_bound_profile_overrides_ambient_auto(self, tmp_path, monkeypatch):
        """A routed profile's ``home_mode=profile`` (scope-bound) wins over the
        launch process's ambient ``TERMINAL_HOME_MODE=auto``; subprocess HOME
        resolves to ``{HERMES_HOME}/home`` instead of the real account HOME."""
        self._host(monkeypatch)
        monkeypatch.setenv("TERMINAL_HOME_MODE", "auto")
        profile_dir, profile_home, real_home = self._make_profile(tmp_path, monkeypatch)

        from tools.terminal_scope import terminal_scope
        from hermes_constants import get_subprocess_home

        with terminal_scope({"TERMINAL_HOME_MODE": "profile"}):
            assert get_subprocess_home() == str(profile_home)
        assert get_subprocess_home() is None

    def test_scope_bound_auto_overrides_ambient_profile(self, tmp_path, monkeypatch):
        """The inverse: a routed profile at ``home_mode=auto`` must NOT inherit
        the launch process's ambient ``profile`` mode via os.environ."""
        self._host(monkeypatch)
        monkeypatch.setenv("TERMINAL_HOME_MODE", "profile")
        profile_dir, profile_home, real_home = self._make_profile(tmp_path, monkeypatch)

        from tools.terminal_scope import terminal_scope
        from hermes_constants import get_subprocess_home

        with terminal_scope({"TERMINAL_HOME_MODE": "auto"}):
            assert get_subprocess_home() is None
        assert get_subprocess_home() == str(profile_home)

    def test_omitted_home_mode_in_scope_resolves_to_auto_not_ambient(self, tmp_path, monkeypatch):
        """The scope's completeness contract: an omitted key under a scope
        resolves to the default (``auto``), never ambient ``os.environ``. A
        scope lacking ``TERMINAL_HOME_MODE`` must NOT inherit the launch
        process's ambient ``profile`` value."""
        self._host(monkeypatch)
        monkeypatch.setenv("TERMINAL_HOME_MODE", "profile")
        profile_dir, profile_home, real_home = self._make_profile(tmp_path, monkeypatch)

        from tools.terminal_scope import terminal_scope
        from hermes_constants import get_subprocess_home

        with terminal_scope({}):
            assert get_subprocess_home() is None
        assert get_subprocess_home() == str(profile_home)

    def test_no_scope_keeps_process_env_behavior(self, tmp_path, monkeypatch):
        """Single-process CLI/TUI (no scope bound) is unchanged: ``get_subprocess_home``
        reads ``TERMINAL_HOME_MODE`` from the process env exactly as before."""
        self._host(monkeypatch)
        profile_dir, profile_home, real_home = self._make_profile(tmp_path, monkeypatch)

        from hermes_constants import get_subprocess_home

        monkeypatch.setenv("TERMINAL_HOME_MODE", "profile")
        assert get_subprocess_home() == str(profile_home)
        monkeypatch.setenv("TERMINAL_HOME_MODE", "auto")
        assert get_subprocess_home() is None


# ---------------------------------------------------------------------------
# Python process HOME unchanged
# ---------------------------------------------------------------------------
