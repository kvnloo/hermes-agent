"""Managed-install permanent approval persistence and isolated revocation tests."""

from unittest.mock import patch as mock_patch

import pytest

import tools.approval as approval_module
from tools.approval import is_approved


class TestManagedAllowlistStateDb:
    """Managed install: config.yaml is package-manager owned, so "always" grants persist to the
    profile's state.db ``command_approvals`` table and are unioned with ``command_allowlist``."""

    @pytest.fixture(params=["env", "env-nixos", "env-home-manager", "marker"])
    def managed_home(self, request, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        from hermes_cli.config import _HERMES_HOME_SUBDIRS
        for sub in _HERMES_HOME_SUBDIRS:
            (home / sub).mkdir(parents=True, exist_ok=True)
        (home / "config.yaml").write_text("command_allowlist:\n  - config-pattern\n", encoding="utf-8")
        monkeypatch.setenv("HERMES_HOME", str(home))
        if request.param != "marker":
            monkeypatch.setenv("HERMES_MANAGED", {"env": "true", "env-nixos": "nixos", "env-home-manager": "home-manager"}[request.param])
        else:
            monkeypatch.delenv("HERMES_MANAGED", raising=False)
            (home / ".managed").write_text("nixos\n", encoding="utf-8")
        self._restart(monkeypatch)
        return home

    @staticmethod
    def _restart(monkeypatch):
        """Simulate a fresh process: drop every in-memory permanent-approval structure."""
        monkeypatch.setattr(approval_module, "_permanent_approved", set())
        monkeypatch.setattr(approval_module, "_permanent_approved_by_home", {})
        monkeypatch.setattr(approval_module, "_permanent_baseline_by_home", {})
        monkeypatch.setattr(approval_module, "_managed_approvals_cache", {})

    @staticmethod
    def _db_rows(home):
        import sqlite3
        conn = sqlite3.connect(home / "state.db")
        try:
            return {row[0] for row in conn.execute("SELECT pattern_key FROM command_approvals")}
        finally:
            conn.close()

    @staticmethod
    def _always(key, session="managed-session"):
        approval_module._persist_choice(session, "always", [key])

    def test_read_without_state_db_does_not_create_it(self, managed_home):
        assert approval_module.load_permanent_allowlist() == {"config-pattern"}
        assert is_approved("managed-read", "config-pattern") is True
        assert not (managed_home / "state.db").exists()

    def test_read_with_state_db_lacking_table(self, managed_home):
        import sqlite3
        sqlite3.connect(managed_home / "state.db").close()
        assert approval_module.load_permanent_allowlist() == {"config-pattern"}

    def test_always_persists_to_state_db_and_not_config(self, managed_home):
        config = managed_home / "config.yaml"
        before = (config.read_bytes(), config.stat().st_mtime_ns)
        approval_module.load_permanent_allowlist()
        with mock_patch("hermes_cli.config.save_config", side_effect=AssertionError("config written")):
            self._always("granted-pattern")
            self._always("config-pattern")  # already in config.yaml: not duplicated into state.db
        assert self._db_rows(managed_home) == {"granted-pattern"}
        assert (config.read_bytes(), config.stat().st_mtime_ns) == before
        assert is_approved("other-session", "granted-pattern") is True

    def test_grant_survives_restart_and_unions_with_config(self, managed_home, monkeypatch):
        approval_module.load_permanent_allowlist()
        self._always("granted-pattern")
        self._restart(monkeypatch)
        assert approval_module.load_permanent_allowlist() == {"config-pattern", "granted-pattern"}
        assert is_approved("fresh", "granted-pattern") is True
        assert is_approved("fresh", "config-pattern") is True
        assert is_approved("fresh", "never-granted") is False

    def test_deleting_row_revokes_live(self, managed_home):
        import sqlite3
        approval_module.load_permanent_allowlist()
        self._always("granted-pattern")
        assert is_approved("fresh", "granted-pattern") is True
        conn = sqlite3.connect(managed_home / "state.db")
        with conn:
            conn.execute("DELETE FROM command_approvals WHERE pattern_key = ?", ("granted-pattern",))
        conn.close()
        assert is_approved("fresh", "granted-pattern") is False
        # A later grant of something else must not resurrect the revoked row.
        self._always("second-pattern")
        assert self._db_rows(managed_home) == {"second-pattern"}
        assert is_approved("fresh", "granted-pattern") is False

    def test_profiles_are_isolated(self, managed_home, tmp_path):
        from hermes_constants import reset_hermes_home_override, set_hermes_home_override
        other = tmp_path / "other-profile"
        other.mkdir()
        from hermes_cli.config import _HERMES_HOME_SUBDIRS
        for sub in _HERMES_HOME_SUBDIRS:
            (other / sub).mkdir(parents=True, exist_ok=True)
        (other / "config.yaml").write_text("command_allowlist: []\n", encoding="utf-8")
        (other / ".managed").write_text("nixos\n", encoding="utf-8")
        approval_module.load_permanent_allowlist()
        self._always("launch-grant")
        token = set_hermes_home_override(other)
        try:
            assert is_approved("routed", "launch-grant") is False
            self._always("routed-grant", session="routed")
            assert is_approved("routed", "routed-grant") is True
        finally:
            reset_hermes_home_override(token)
        assert self._db_rows(managed_home) == {"launch-grant"}
        assert self._db_rows(other) == {"routed-grant"}
        assert is_approved("launch", "routed-grant") is False
        assert is_approved("launch", "launch-grant") is True


class TestUnmanagedAllowlistIgnoresStateDb:
    def test_unmanaged_always_writes_config_not_state_db(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HERMES_HOME", str(home))
        monkeypatch.delenv("HERMES_MANAGED", raising=False)
        monkeypatch.setattr(approval_module, "_permanent_approved", set())
        monkeypatch.setattr(approval_module, "_permanent_baseline_by_home", {})
        saved = {}
        with mock_patch("hermes_cli.config.load_config", return_value={"command_allowlist": ["a"]}), \
             mock_patch("hermes_cli.config.save_config", side_effect=lambda cfg: saved.update(cfg)):
            approval_module.save_permanent_allowlist({"b"})
        assert saved["command_allowlist"] == ["a", "b"]
        assert not (home / "state.db").exists()
