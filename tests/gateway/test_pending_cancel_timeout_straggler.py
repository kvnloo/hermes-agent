"""A cancelled turn that outlives the stop bound keeps its unclaimed head."""

import asyncio

import pytest

from gateway.platforms.base_pending import release_pending_dispatch
from tests.gateway.test_pending_queue_admission import _events, _setup


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "straggler-unclaimed",
        "straggler-durable",
        "straggler-claims-late",
        "straggler-drained",
        "straggler-requeued",
    ],
)
async def test_cancel_timeout_restores_unclaimed_head_once(path, monkeypatch):
    adapter, runner, expected = _setup(4, monkeypatch)
    attempted = adapter._pending_messages.pop("shared")
    adapter._stage_next_queued_event("shared", attempted)
    entered, unwind = asyncio.Event(), asyncio.Event()

    async def handler(event):
        if event is not attempted:
            await asyncio.Event().wait()
        if path == "straggler-durable":
            release_pending_dispatch(adapter, "shared", event, claimed=True)
        entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            if path == "straggler-requeued":
                runner._queue_or_replace_pending_event("shared", event)
            # Outlive the 5s bound in cancel_session_processing.
            await unwind.wait()
            if path == "straggler-claims-late":
                release_pending_dispatch(adapter, "shared", event, claimed=True)

    adapter.set_message_handler(handler)
    try:
        adapter._start_session_processing(attempted, "shared")
        straggler = adapter._session_tasks["shared"]
        await asyncio.wait_for(entered.wait(), 2)
        command_guard = asyncio.Event()
        adapter._active_sessions["shared"] = command_guard
        await adapter.cancel_session_processing(
            "shared", release_guard=False, discard_pending=False
        )
        assert not straggler.done()
        if path == "straggler-drained":
            await adapter._drain_pending_after_session_command("shared", command_guard)
        if path == "straggler-requeued":
            # The requeued head is dispatched again and claimed by that turn
            # before the straggler finishes unwinding.
            head = adapter._pending_messages.pop("shared")
            adapter._stage_next_queued_event("shared", head)
            release_pending_dispatch(adapter, "shared", head, claimed=True)
        unwind.set()
        await asyncio.wait_for(straggler, 2)
        await asyncio.sleep(0)
        reserved = {
            key: record.event
            for key, record in adapter._pending_dispatch_reservations.items()
        }
        if path == "straggler-drained":
            # The drain dispatched msg-1 while the straggler unwound; msg-0 is
            # back at the FIFO head, ahead of everything still queued.
            recoverable, in_flight = (
                [expected[0], *expected[2:]],
                {"shared": expected[1]},
            )
        elif path == "straggler-unclaimed":
            recoverable, in_flight = expected, {}
        else:
            recoverable, in_flight = expected[1:], {}
        events = _events(adapter, runner)
        assert (
            [event.message_id for event in events],
            {key: event.message_id for key, event in reserved.items()},
        ) == (
            [event.message_id for event in recoverable],
            {key: event.message_id for key, event in in_flight.items()},
        )
        assert (events, reserved) == (recoverable, in_flight)
    finally:
        unwind.set()
        adapter._discard_text_debounce("shared")
        await adapter.cancel_background_tasks()
