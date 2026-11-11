"""A replacement gateway must not inherit a previous multiplexer's ownership.

Regression for NousResearch/hermes-agent#153313, reported by alt-glitch.
"""

import json

from gateway import status


def test_startup_discards_previous_gateway_multiplex_ownership(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    path = tmp_path / "gateway_state.json"
    path.write_text(json.dumps({
        "served_profiles": ["default", "coder"],
        "platforms": {
            "telegram": {"state": "connected"},
            "coder:discord": {"state": "connected"},
        },
    }), encoding="utf-8")

    assert status.write_runtime_status(
        gateway_state="starting",
        exit_reason=None,
        clear_profile_platforms=True,
        reload_existing=True,
        wait_timeout=2.0,
    ) is True

    runtime = status.read_runtime_status(path)
    assert runtime is not None
    assert runtime["gateway_state"] == "starting"
    assert runtime["served_profiles"] == []
    assert runtime["platforms"] == {"telegram": {"state": "connected"}}
