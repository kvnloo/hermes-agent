"""An awake server can miss a heartbeat without using CPU."""

import asyncio
import logging
import threading

from hermes_cli.web_server_lifecycle import arm_loop_heartbeat


def test_blocking_wait_is_not_reported_as_probable_suspend(caplog):
    logger = logging.getLogger(__name__)

    async def run():
        arm_loop_heartbeat(asyncio.get_running_loop(), logger)
        # A synchronous wait models blocking I/O on the event-loop thread.
        # The host is awake; the timeout is 5.2s past the heartbeat's due time.
        assert not threading.Event().wait(timeout=7.2)
        await asyncio.sleep(0.01)

    with caplog.at_level(logging.INFO, logger=logger.name):
        asyncio.run(run())
    heartbeat = [r.getMessage() for r in caplog.records if r.name == logger.name]
    assert len(heartbeat) == 1
    assert "probably asleep" not in heartbeat[0], heartbeat[0]
    assert "event loop paused" in heartbeat[0]
