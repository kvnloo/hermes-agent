"""Gateway startup names every served profile whose config still declares a retired timed reset."""
import contextlib
import logging
from types import SimpleNamespace

import pytest

from gateway.run_startup import GatewayStartupMixin
from hermes_cli import session_reset_retirement


@pytest.mark.parametrize("plugin_enabled", [False, True])
def test_startup_warns_on_timed_session_reset_unless_plugin_enabled(tmp_path, monkeypatch, caplog, plugin_enabled):
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.yaml").write_text("session_reset:\n  mode: idle\n  idle_minutes: 60\n", encoding="utf-8")
    monkeypatch.setattr("hermes_cli.profiles.profiles_to_serve", lambda multiplex: [("default", home)])
    monkeypatch.setattr(session_reset_retirement, "reset_plugin_enabled", lambda: plugin_enabled)
    runner = object.__new__(GatewayStartupMixin)
    runner.config = SimpleNamespace(multiplex_profiles=False)

    with caplog.at_level(logging.WARNING, logger="gateway.run"):
        runner._start_log_retired_session_reset()

    warned = [r.getMessage() for r in caplog.records if "session_reset.mode: idle" in r.getMessage()]
    assert (warned == []) is plugin_enabled
    if not plugin_enabled:
        assert session_reset_retirement.PLUGIN_NAME in warned[0]


def test_only_timed_modes_count_as_retired_policy():
    find = session_reset_retirement.retired_reset_policy
    assert find({"session_reset": {"mode": "both"}}) == ("session_reset", "both")
    assert find({"gateway": {"session_reset": {"mode": "Daily"}}}) == ("gateway.session_reset", "daily")
    assert find({"session_reset": {"mode": "none"}}) is None
    assert find({"session_reset": {"idle_minutes": 60}}) is None
    assert find({}) is None


@pytest.mark.parametrize(
    ("enabled_on", "warned_profile"),
    [("default", "b"), ("b", "default")],
)
def test_startup_checks_each_profile_plugin_scope(
    tmp_path, monkeypatch, caplog, enabled_on, warned_profile
):
    """#137010: only the routed profile's own plugin set controls its warning."""
    root = tmp_path / "root"
    routed = tmp_path / "profiles" / "b"
    for home in (root, routed):
        home.mkdir(parents=True)
        (home / "config.yaml").write_text(
            "session_reset:\\n  mode: both\\n".replace("\\n", "\n"),
            encoding="utf-8",
        )
    homes = {"default": root, "b": routed}
    monkeypatch.setattr(
        "hermes_cli.profiles.profiles_to_serve",
        lambda multiplex: list(homes.items()),
    )

    checked = []
    active = [None]

    @contextlib.contextmanager
    def profile_scope(home):
        previous = active[0]
        active[0] = home
        checked.append(home)
        try:
            yield
        finally:
            active[0] = previous

    monkeypatch.setattr("gateway.run._profile_runtime_scope", profile_scope)
    monkeypatch.setattr(
        session_reset_retirement, "reset_plugin_enabled",
        lambda: active[0] == homes[enabled_on],
    )
    runner = object.__new__(GatewayStartupMixin)
    runner.config = SimpleNamespace(multiplex_profiles=True)

    with caplog.at_level(logging.WARNING, logger="gateway.run"):
        runner._start_log_retired_session_reset()

    warned = [r.getMessage() for r in caplog.records if "session_reset.mode: both" in r.getMessage()]
    assert checked == [root, routed]
    assert active[0] is None
    assert len(warned) == 1
    assert warned[0].startswith(f"Profile {warned_profile}: ")
