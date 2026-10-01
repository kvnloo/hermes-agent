"""#49773: a serving gateway must emit the [MEMORY] heartbeat, honour
``logging.memory_monitor`` and stop the heartbeat on every way out.

Drives the real ``start_gateway()`` lifecycle and the real
``gateway.memory_monitor`` thread. Only the pieces that would touch the host
(PID/lock files, host rendezvous, control socket, MCP, cron, auth keepalive)
are stubbed, using the same stubs as ``tests/gateway/test_startup_restart_race.py``,
so the contract holds wherever a fix places its start/stop calls inside
``start_gateway()``.
"""

from __future__ import annotations

import threading

import pytest

import gateway.run as gateway_run
from gateway import memory_monitor as mm
from gateway.config import GatewayConfig


@pytest.fixture(autouse=True)
def _monitor_stopped():
    mm.stop_memory_monitoring(timeout=1.0)
    yield
    mm.stop_memory_monitoring(timeout=1.0)


def _finished_thread() -> threading.Thread:
    t = threading.Thread(target=lambda: None, daemon=True)
    t.start()
    t.join()
    return t


def _make_runner_cls(seen: dict, *, running: bool, exit_with_failure: bool):
    class Runner:
        def __init__(self, config):
            self.config = config
            self.adapters = {}
            self._running = running
            self.should_exit_cleanly = False
            self.should_exit_with_failure = False
            self.exit_reason = None
            self.exit_code = None
            self._restart_requested = False
            self._restart_via_service = False
            self._draining = False
            self._external_drain_active = False
            self._signal_initiated_shutdown = False

        async def start(self):
            return True

        def _start_systemd_watchdog(self):
            return None

        async def wait_for_shutdown(self):
            seen["running_while_serving"] = mm.is_running()
            self.should_exit_with_failure = exit_with_failure

        async def stop(self):
            return None

    return Runner


def _boot(monkeypatch, tmp_path, monitor_cfg, runner_cls):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    if monitor_cfg is not None:
        (tmp_path / "config.yaml").write_text(
            "logging:\n  memory_monitor:\n" + monitor_cfg, encoding="utf-8"
        )

    intervals: list[float] = []
    real_start = mm.start_memory_monitoring

    def _spy_start(interval_seconds: float = 300.0, *args, **kwargs):
        intervals.append(float(interval_seconds))
        return real_start(interval_seconds, *args, **kwargs)

    monkeypatch.setattr(mm, "start_memory_monitoring", _spy_start)

    async def _none_async(*args, **kwargs):
        return None

    async def _no_mcp_shutdown(*args, **kwargs):
        return True

    monkeypatch.setattr("gateway.status.get_running_pid", lambda: None)
    monkeypatch.setattr("gateway.status.acquire_gateway_runtime_lock", lambda: True)
    monkeypatch.setattr("gateway.status.write_pid_file", lambda: None)
    monkeypatch.setattr("gateway.status.remove_pid_file", lambda: None)
    monkeypatch.setattr("gateway.status.release_gateway_runtime_lock", lambda: None)
    monkeypatch.setattr("tools.skills_sync.sync_skills", lambda quiet=True: None)
    monkeypatch.setattr("hermes_logging.setup_logging", lambda hermes_home, mode: None)
    monkeypatch.setattr("hermes_cli.nous_auth_keepalive.start_nous_auth_keepalive", lambda: None)
    monkeypatch.setattr("hermes_cli.nous_auth_keepalive.stop_nous_auth_keepalive", lambda: None)
    monkeypatch.setattr(gateway_run, "_host_attach_or_none", _none_async)
    monkeypatch.setattr(gateway_run, "_claim_host_gateway_role", lambda force=False: None)
    monkeypatch.setattr(gateway_run, "_start_gateway_start_control_socket", _none_async)
    monkeypatch.setattr(gateway_run, "_refresh_host_gateway_record", lambda runner: None)
    monkeypatch.setattr(gateway_run, "_discover_gateway_mcp_tools", _none_async)
    monkeypatch.setattr(gateway_run, "_recover_pending_flushes", lambda runner: 0)
    monkeypatch.setattr(gateway_run, "GatewayRunner", runner_cls)
    monkeypatch.setattr(
        gateway_run,
        "_start_gateway_start_cron_and_housekeeping",
        lambda runner: (threading.Event(), object(), _finished_thread(), _finished_thread()),
    )
    monkeypatch.setattr(gateway_run, "_stop_cron_provider", lambda provider: None)
    monkeypatch.setattr(gateway_run, "_shutdown_mcp_servers_nonblocking", _no_mcp_shutdown)
    return intervals


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("monitor_cfg", "exit_with_failure", "expect_running", "expect_interval"),
    [
        pytest.param("    enabled: true\n    interval_seconds: 42\n", False, True, 42.0, id="enabled"),
        pytest.param("    enabled: true\n    interval_seconds: 42\n", True, True, 42.0, id="enabled-failure-exit"),
        pytest.param("    enabled: false\n    interval_seconds: 42\n", False, False, None, id="disabled"),
        pytest.param(None, False, True, 300.0, id="unconfigured-default"),
    ],
)
async def test_serving_gateway_runs_memory_heartbeat_until_shutdown(
    tmp_path, monkeypatch, monitor_cfg, exit_with_failure, expect_running, expect_interval
):
    seen: dict = {}
    runner_cls = _make_runner_cls(seen, running=True, exit_with_failure=exit_with_failure)
    intervals = _boot(monkeypatch, tmp_path, monitor_cfg, runner_cls)

    ok = await gateway_run.start_gateway(config=GatewayConfig(), replace=False, verbosity=None)

    assert ok is (not exit_with_failure)
    assert seen["running_while_serving"] is expect_running, "[MEMORY] heartbeat state while serving"
    if expect_interval is not None:
        assert intervals == [expect_interval], "heartbeat must use logging.memory_monitor.interval_seconds"
    else:
        assert intervals == [], "enabled: false must not start the heartbeat"
    assert mm.is_running() is False, "heartbeat must stop when the gateway shuts down"


@pytest.mark.asyncio
async def test_aborted_startup_leaves_no_heartbeat_running(tmp_path, monkeypatch):
    seen: dict = {}
    runner_cls = _make_runner_cls(seen, running=False, exit_with_failure=False)
    _boot(monkeypatch, tmp_path, "    enabled: true\n    interval_seconds: 42\n", runner_cls)

    ok = await gateway_run.start_gateway(config=GatewayConfig(), replace=False, verbosity=None)

    assert ok is True
    assert mm.is_running() is False, "an aborted startup must not leave the heartbeat thread behind"
