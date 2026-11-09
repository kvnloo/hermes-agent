"""A wedged dashboard loop must exit from a thread, not a timer on the wedged loop."""

import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, sentinel

from gateway.shutdown_watchdog import start_loop_liveness_watchdog
from hermes_cli import web_server


def test_dashboard_loop_stall_exits_without_overwriting_gateway_status(tmp_path):
    # A loop that accepts scheduled callbacks but never dispatches any: the
    # asyncio WS send deadline and the call_later drift logger cannot run.
    loop = MagicMock(spec=asyncio.AbstractEventLoop)
    ready = threading.Event()
    handle_ref = {}
    exit_codes = []

    def stop_at_exit(code):
        assert ready.wait(timeout=1)
        exit_codes.append(code)
        handle_ref["handle"].stop()  # patched hard-exit must not start a second probe

    with (
        patch("gateway.shutdown_watchdog._write_watchdog_dump") as dump,
        patch("gateway.shutdown_watchdog._mark_exited_quietly") as gateway_status,
        patch("gateway.shutdown_watchdog._hard_exit", side_effect=stop_at_exit),
    ):
        handle = start_loop_liveness_watchdog(
            loop, probe_interval=0.01, probe_timeout=0.01, max_strikes=1,
            service_name="Dashboard", record_gateway_exit=False,
            dump_path=tmp_path / "dashboard-loop-watchdog.log",
        )
        assert handle is not None
        handle_ref["handle"] = handle
        ready.set()
        handle.join(timeout=2)

    assert not handle.is_alive()
    assert exit_codes == [75]
    gateway_status.assert_not_called()
    dump.assert_called_once()
    assert dump.call_args.args[0] == tmp_path / "dashboard-loop-watchdog.log"
    assert dump.call_args.kwargs["event"] == "dashboard_loop_liveness_watchdog_fired"


def test_dashboard_post_bind_arms_watchdog_outside_loop(tmp_path):
    server = SimpleNamespace()
    loop = object()
    with (
        patch("hermes_constants.get_process_hermes_home", return_value=tmp_path),
        patch("gateway.shutdown_watchdog.start_loop_liveness_watchdog", return_value=sentinel.guard) as start,
    ):
        web_server._arm_web_loop_watchdog(server, loop, headless=False)

    assert server._loop_liveness_watchdog is sentinel.guard
    start.assert_called_once_with(
        loop, service_name="Dashboard", record_gateway_exit=False,
        dump_path=tmp_path / "logs/dashboard-loop-watchdog.log",
    )
