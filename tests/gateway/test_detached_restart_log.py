"""Regression for #152714: a failed detached /restart must leave a readable log."""

import os
import shutil
import subprocess
import sys

import pytest

from gateway.run_shutdown import GatewayShutdownMixin


@pytest.mark.platforms("posix")
@pytest.mark.asyncio
async def test_detached_restart_failure_leaves_log(tmp_path, monkeypatch):
    home = tmp_path / "home with spaces"
    home.mkdir()
    monkeypatch.setattr("hermes_constants.get_hermes_home", lambda: home)
    # The old gateway is already gone, so its watcher should restart immediately.
    monkeypatch.setattr("gateway.run_shutdown.os.getpid", lambda: 2147483647)
    monkeypatch.setattr(
        "gateway.run._resolve_hermes_bin",
        lambda: [
            sys.executable, "-c",
            "import sys; sys.stderr.write('No module named hermes_cli\\n'); sys.exit(19)",
        ],
    )
    monkeypatch.setattr(
        GatewayShutdownMixin, "_restart_watcher_env", staticmethod(os.environ.copy),
    )
    original_which = shutil.which
    monkeypatch.setattr(
        shutil, "which", lambda name: None if name == "setsid" else original_which(name),
    )

    real_popen = subprocess.Popen

    def run_watcher(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        process.wait(timeout=5)
        return process

    monkeypatch.setattr(subprocess, "Popen", run_watcher)
    runner = GatewayShutdownMixin()
    runner._detached_restart_helper_started = False
    runner._restart_drain_timeout = 0
    await runner._launch_detached_restart_command()

    log = (home / "logs" / "detached-restart.log").read_text(encoding="utf-8")
    assert "No module named hermes_cli" in log
    assert "Detached /restart failed (exit 19)" in log
