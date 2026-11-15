"""Security-boundary regressions for the TUI ``shell.exec`` RPC."""

from __future__ import annotations

import subprocess

from agent import redact
from tui_gateway import server


def test_shell_exec_scrubs_child_env_and_force_redacts_rpc_output(monkeypatch):
    secret = "sk-shell-exec-secret-1234567890"
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=f"visible\n{secret}\n",
            stderr=f"diagnostic {secret}",
        )

    monkeypatch.setenv("OPENROUTER_API_KEY", secret)
    monkeypatch.setattr(redact, "_REDACT_ENABLED", False)
    monkeypatch.setattr(server.subprocess, "run", fake_run)

    response = server.handle_request(
        {"id": "security", "method": "shell.exec", "params": {"command": "echo safe"}}
    )

    assert "OPENROUTER_API_KEY" not in captured["env"]
    assert secret not in response["result"]["stdout"]
    assert secret not in response["result"]["stderr"]
    assert "visible" in response["result"]["stdout"]



def test_shell_exec_raw_stdout_preserves_plugin_json_without_exposing_stderr(monkeypatch):
    token = "1341a55f03ce51f23d46420e9bcd6226"
    structured = '{"snapshot_token":"' + token + '","snapshots":[]}\n'
    secret = "sk-shell-exec-secret-1234567890"

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command, 0, stdout=structured, stderr=f"diagnostic {secret}"
        )

    monkeypatch.setattr(server.subprocess, "run", fake_run)
    default = server.handle_request(
        {"id": "default", "method": "shell.exec", "params": {"command": "echo safe"}}
    )
    raw = server.handle_request(
        {"id": "raw", "method": "shell.exec",
         "params": {"command": "echo safe", "raw_stdout": True}}
    )

    assert token not in default["result"]["stdout"]
    assert raw["result"]["stdout"] == structured
    assert secret not in raw["result"]["stderr"]
