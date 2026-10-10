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
turn can start, answered through the adapter — and the handoff waits for it.

Success is the turn's own receipt (``_gateway_turn_task``, stamped by ``_run_post_turn_hooks``
with the task the turn returned in), never the queue being empty: a gateway stop, a session reset
and an adapter replacement all empty the queue without running anything, and the adapter contains a
turn that raises. Each of those fails the handoff with a reason instead.
"""

from __future__ import annotations

import asyncio
from typing import Any

_RETRY = "Re-run /handoff to try again."
# A command or a teardown holds the session with no task to wait on; re-read at this interval.
_HELD_SESSION_POLL_SECONDS = 0.05


def _still_queued(runner: Any, adapter: Any, session_key: str, event: Any) -> bool:
    return adapter._pending_messages.get(session_key) is event or any(
        queued is event for queued in runner._overflow_queue(session_key) or ()
    )


async def run_queued_handoff_turn(runner: Any, source: Any, event: Any) -> None:
    """Return once ``event``'s turn has returned and the task it ran in (which also delivers the
    reply) has finished.

    Raises when the turn did not run or nothing can run it (the watcher marks the row ``failed``).
    Cancellation propagates, which leaves the row ``running`` for the next start's stale-handoff
    reclaim.
    """
    adapter = runner._delivery_adapter_for(source)
    if adapter is None:
        raise RuntimeError(f"no delivery adapter can run the handoff turn. {_RETRY}")
    session_key = runner._session_key_for_source(source)
    while True:
        ran_in = getattr(event, "_gateway_turn_task", None)
        if ran_in is not None:
            if ran_in is not asyncio.current_task():
                await asyncio.wait({ran_in})
            return
        owner = adapter._session_tasks.get(session_key)
        if owner is not None and not owner.done():
            # Each re-dispatch hands the session to a fresh drain task; follow the chain.
            await asyncio.wait({owner})
            continue
        if not runner._running:
            raise RuntimeError(f"gateway stopped before the handoff turn could run. {_RETRY}")
        if session_key in adapter._active_sessions:
            # Guard without an owner task: /stop, /new or a teardown is between cancelling the
            # owner and deciding the queue's fate. Starting a task here would resurrect a turn
            # that is being discarded.
            await asyncio.sleep(_HELD_SESSION_POLL_SECONDS)
            continue
        if not _still_queued(runner, adapter, session_key, event):
            raise RuntimeError(
                "handoff turn did not run: it failed, or was discarded from the destination chat's "
                f"queue (session cancelled, adapter restarted). {_RETRY}"
            )
        pending = adapter.get_pending_message(session_key)
        if pending is None:
            raise RuntimeError("handoff turn is queued behind a session nothing is draining")
        adapter._start_session_processing(pending, session_key)
