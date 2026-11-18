"""Regression for the macOS sibling launchd drain (#126883).

PID existence does not prove identity: an obsolete gateway_state.json can name
a live, unrelated process after PID reuse. The sibling restart must not signal it.
"""

import json
import os

from hermes_cli.update_cmd_fleet import _launchd_real_gateway_pid


def test_recycled_gateway_state_pid_is_not_a_drain_target(tmp_path):
    home = tmp_path / "sibling"
    home.mkdir()
    (home / "gateway_state.json").write_text(
        json.dumps({
            "pid": os.getpid(),  # alive, but this pytest process is not a gateway
            "start_time": 0.0,  # not the live process's birth time
            "hermes_home": str(home),
            "gateway_state": "running",
        }),
        encoding="utf-8",
    )

    assert _launchd_real_gateway_pid(str(home)) is None
