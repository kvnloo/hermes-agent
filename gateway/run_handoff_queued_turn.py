"""A handoff's synthetic turn that the runner queued instead of starting.

``_process_handoff`` calls ``_handle_message`` inline so a failing turn fails the handoff. Inline,
a turn that cannot start now — the compression new-turn gate (#134239) defers an internal event,
the busy path queues it behind a running turn — returns the same empty reply a streamed turn does,
and the event is left in the delivery adapter's pending slot. Only the adapter task that owns the
session drains that slot; an inline caller has none, so the event sat there until the user's next
message in that chat while the handoff was already reported ``completed``.

The queued event is handed to the adapter the way the adapter recovers an orphaned pending event
itself (``BasePlatformAdapter._handle_message_while_active``): start the session's owner task on
it. From there it is an ordinary deferred internal event — re-dispatched with back-off until the
turn can start, answered through the adapter — and the handoff waits for it instead of reporting a
turn that has not run.
"""

from __future__ import annotations

import asyncio
from typing import Any


async def run_queued_handoff_turn(runner: Any, source: Any, event: Any) -> None:
    """Return once the adapter has taken ``event`` out of the queue and its session went idle.

    Raises when nothing can run it. Cancellation (gateway stop) propagates, which leaves the row
    ``running`` for the next start's stale-handoff reclaim.
    """
    adapter = runner._delivery_adapter_for(source)
    if adapter is None:
        raise RuntimeError("handoff turn was queued but no adapter can run it")
    session_key = runner._session_key_for_source(source)
    while True:
        owner = adapter._session_tasks.get(session_key)
        if owner is not None and not owner.done():
            # Each re-dispatch hands the session to a fresh drain task; follow the chain.
            await asyncio.wait({owner})
            continue
        if adapter._pending_messages.get(session_key) is not event and not any(
            queued is event for queued in runner._overflow_queue(session_key) or ()
        ):
            return
        pending = adapter.get_pending_message(session_key)
        if pending is None:
            raise RuntimeError("handoff turn is queued behind a session nothing is draining")
        adapter._start_session_processing(pending, session_key)
