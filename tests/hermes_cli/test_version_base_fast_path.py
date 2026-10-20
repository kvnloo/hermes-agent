"""``get_base_version()``: the release base version without the working-tree dirty scan.

Import-time User-Agent/client strings only need ``base_version``, but ``get_version_info()``
also runs ``git status`` to compute ``dirty``. On large checkouts on slow filesystems
(Android/proot) that index refresh takes seconds, and modules such as ``auth_constants`` paid
it at import time, delaying the TUI gateway's ``gateway.ready``.
"""

import subprocess

import pytest

from hermes_cli import version_info


@pytest.fixture
def git_calls(monkeypatch):
    calls = []
    real_run = subprocess.run

    def run(cmd, *a, **k):
        if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "git":
            calls.append(list(cmd[1:]))
        return real_run(cmd, *a, **k)

    monkeypatch.setattr(version_info.subprocess, "run", run)
    version_info._reset_version_info_cache()
    yield calls
    version_info._reset_version_info_cache()


def test_base_version_matches_full_info_without_a_status_scan(git_calls, monkeypatch):
    monkeypatch.setattr(version_info, "_stamp_version_info", lambda: None)

    base = version_info.get_base_version()

    assert not any(call[:1] == ["status"] for call in git_calls)
    assert base == version_info.get_version_info().base_version


def test_base_version_reuses_an_already_resolved_full_info(git_calls):
    version_info._cached_version_info = version_info.VersionInfo(
        "9.9.9", "9.9.9", 0, "a" * 40, "main", "git")

    assert version_info.get_base_version() == "9.9.9"
    assert git_calls == []


def test_base_version_prefers_the_install_stamp(git_calls, monkeypatch):
    stamp = version_info.VersionInfo("1.2.3", "1.2.3", None, "b" * 40, None, "build")
    monkeypatch.setattr(version_info, "_stamp_version_info", lambda: stamp)

    assert version_info.get_base_version() == "1.2.3"
    assert git_calls == []


def test_reset_drops_the_cached_base_version(git_calls, monkeypatch):
    monkeypatch.setattr(version_info, "_stamp_version_info",
                        lambda: version_info.VersionInfo("1.0.0", "1.0.0", None, None, None, "build"))
    assert version_info.get_base_version() == "1.0.0"
    version_info._reset_version_info_cache()
    monkeypatch.setattr(version_info, "_stamp_version_info",
                        lambda: version_info.VersionInfo("2.0.0", "2.0.0", None, None, None, "build"))
    assert version_info.get_base_version() == "2.0.0"


def test_import_time_user_agents_do_not_scan_the_worktree(git_calls, monkeypatch):
    import importlib

    import hermes_cli.auth_constants as auth_constants

    monkeypatch.setattr(version_info, "_stamp_version_info", lambda: None)
    importlib.reload(auth_constants)

    assert not any(call[:1] == ["status"] for call in git_calls)
    assert auth_constants.CODEX_OAUTH_USER_AGENT == f"hermes-cli/{version_info.get_base_version()}"
