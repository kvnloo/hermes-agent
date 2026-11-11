"""Regression for #153204: the Desktop panel names gateway drain work.

The gateway can keep a running turn alive for the full configured drain budget.
The status file must name that wait, rather than the preceding download stage.
"""

from __future__ import annotations

import json

from hermes_cli import update_cmd_posix_pause, update_pause_record, update_stage


def test_update_panel_names_gateway_drain_while_turn_is_active(monkeypatch, tmp_path):
    status = tmp_path / "update-status.json"
    status.write_text(json.dumps({"status": "running", "message": "Downloading updates"}),
                      encoding="utf-8")
    monkeypatch.setenv(update_stage.STATUS_FILE_ENV, str(status))
    entry = {"kind": "launchd", "label": "ai.hermes.gateway", "pid": 4242, "home": str(tmp_path)}
    monkeypatch.setattr(update_pause_record, "mark_stop_sent", lambda *_: None)
    monkeypatch.setattr(update_cmd_posix_pause, "_ask_to_drain", lambda _: True)
    monkeypatch.setattr(update_cmd_posix_pause, "_disarm", lambda _: None)
    observed = []

    def check_active_turn(_pid, _start):
        observed.append(json.loads(status.read_text(encoding="utf-8")))
        return False  # the turn has just finished; no forced stop required

    monkeypatch.setattr(update_cmd_posix_pause, "_alive", check_active_turn)
    update_cmd_posix_pause._stop_gateways({}, [entry])

    assert observed == [{"status": "running", "message": "Waiting for running tasks to finish"}]
