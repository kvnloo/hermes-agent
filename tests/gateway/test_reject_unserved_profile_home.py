"""A named source must never borrow the launch home in a multiplexed gateway."""

from pathlib import Path

import pytest

from gateway.config import GatewayConfig, Platform
from gateway.profile_routing import ProfileRouteRejected
from gateway.run import GatewayRunner
from gateway.session import SessionSource


@pytest.fixture
def runner(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    for name in ("served", "parked"):
        profile_home = home / "profiles" / name
        profile_home.mkdir(parents=True)
        (profile_home / "config.yaml").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))

    gateway = object.__new__(GatewayRunner)
    gateway.config = GatewayConfig(multiplex_profiles=True)
    # Live gateway roster: "parked" is still installed but no longer served.
    gateway.config._runtime_profile_homes = [
        ("default", home), ("served", home / "profiles" / "served"),
    ]
    return gateway, home


def _source(profile):
    return SessionSource(
        platform=Platform.TELEGRAM, chat_id="chat-1", chat_type="dm",
        user_id="user-1", profile=profile,
    )


@pytest.mark.parametrize("profile", ["missing", "parked"])
def test_unserved_explicit_profile_is_refused(runner, profile):
    gateway, _home = runner
    with pytest.raises(ProfileRouteRejected):
        gateway._resolve_profile_home_for_source(_source(profile))


def test_explicit_profile_roster_resolution_failure_is_refused(runner, monkeypatch):
    gateway, _home = runner

    def failed_roster(_config):
        raise OSError("served-profile roster unavailable")

    monkeypatch.setattr("gateway.run._multiplex_profile_homes", failed_roster)
    with pytest.raises(ProfileRouteRejected):
        gateway._resolve_profile_home_for_source(_source("served"))


def test_unstamped_and_standalone_fallback_still_works(runner):
    gateway, home = runner
    assert gateway._resolve_profile_home_for_source(_source("served")) == home / "profiles" / "served"
    assert gateway._resolve_profile_home_for_source(_source(None)) == home
    gateway.config.multiplex_profiles = False
    assert gateway._resolve_profile_home_for_source(_source("missing")) == home
