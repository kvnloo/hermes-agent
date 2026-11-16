"""Regression for #137010: doctor checks enablement in one profile, not observed resets."""

import pytest

from hermes_cli import config_effective, profiles, session_reset_retirement
from hermes_cli.doctor_config import _check_retired_session_reset


@pytest.mark.parametrize(
    "detail",
    ["'routed'", "not a verified reset", "pre_gateway_dispatch", "CLI/TUI/Desktop"],
)
def test_doctor_names_profile_and_limits_of_plugin_check(monkeypatch, capsys, detail):
    monkeypatch.setattr(
        config_effective, "load_user_config_effective",
        lambda: {"session_reset": {"mode": "both", "idle_minutes": 1440}},
    )
    monkeypatch.setattr(session_reset_retirement, "reset_plugin_enabled", lambda: True)
    monkeypatch.setattr(profiles, "get_active_profile_name", lambda: "routed")

    _check_retired_session_reset(False)

    out = capsys.readouterr().out
    assert session_reset_retirement.PLUGIN_NAME in out
    assert detail in out
    assert "is applied by the session reset plugin" not in out
