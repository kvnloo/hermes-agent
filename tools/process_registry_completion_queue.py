"""Autonomous completion-queue notification helpers for ProcessRegistry.

The facade (``tools/process_registry.py``) keeps the public surface; the live
``completion_queue`` payload build/swap lives here so the registry file stays
under its size cap. ``ProcessCompletionQueueMixin`` is mixed into
``ProcessRegistry`` and assumes the registry supplies ``self._lock``,
``self.completion_queue``, ``self._exit_fields`` and ``self._running``.
"""

import queue
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.process_registry import ProcessSession


class ProcessCompletionQueueMixin:
    """Build and swap autonomous completion notifications on the live queue.

    Mixed into ``ProcessRegistry``; callers invoke these helpers while holding
    ``self._lock`` (or acquire it themselves) so the snapshot-then-put is
    atomic with the kill path's drain-and-swap.
    """

    def _enqueue_completion_notification(self, session: "ProcessSession") -> None:
        """Build and enqueue the autonomous completion notification for ``session``.

        Caller MUST hold ``self._lock``. The notification snapshots the *current*
        session fields, so a kill that just stamped ``completion_reason="killed"``
        and called this from ``_replace_stale_completion_notification`` emits the
        corrected ``killed`` payload; the reader calling it from
        ``_move_to_finished`` before the kill stamps it sees the reader's
        ``exited`` view (which the kill then swaps out under the same lock).
        Holding the lock makes the snapshot-then-put atomic with the kill's
        drain-and-swap, which is the property that closes the durable-but-stale
        race on the live ``completion_queue`` payload."""
        from tools.process_registry import _completion_output, _redact_process_result

        notification = {
            "type": "completion",
            "session_id": session.id,
            "session_key": session.session_key,
            "task_id": session.task_id,
            "owner_task_id": session.owner_task_id,
            "command": session.command,
            **({"handoff_note": session.handoff_note} if session.handoff_note else {}),
            **self._exit_fields(session),
            # A consumer that relays the output (a bot DM's reply) must know it is not whole.
            **_completion_output(session),
            # Stable producer identity across checkpoint recovery (unlike a
            # consumer-observed completion timestamp).
            "started_at": session.started_at,
        }
        _redact_process_result(notification)
        self.completion_queue.put(notification)

    def _replace_stale_completion_notification(self, session: "ProcessSession") -> None:
        """Swap the reader's stale completion event for ``session`` out of the
        queue and re-enqueue a corrected one built from the now-stamped session.

        Used by ``kill_process`` when the reader thread finalised the session
        while the SIGKILL grace window was still draining: the reader's
        ``_move_to_finished`` enqueued a ``completion_reason="exited"`` payload
        *before* the kill path stamped the session ``killed``, and the kill
        path's own ``_move_to_finished`` returns False (``was_running=False``),
        so it can't enqueue a corrected one itself. The durable receipt is
        re-saved separately (``save_completed_result``); this method fixes the
        LIVE ``completion_queue`` payload delivered to CLI/TUI drain surfaces.

        Foreign sessions' events are drained to a keep-list and re-put
        unchanged; the ``Queue`` is thread-safe, and ``self._lock`` (acquired
        here) is what serialises this swap against the reader's enqueue inside
        ``_move_to_finished``."""
        with self._lock:
            keep: list = []
            while True:
                try:
                    evt = self.completion_queue.get_nowait()
                except queue.Empty:
                    break
                # Drop only this session's stale "completion"; preserve
                # watch_match events, async-delegation completions, and every
                # other session's completion verbatim. The reader's stale
                # event predates the kill stamp on the session, so rebuild it.
                if evt.get("type") == "completion" and evt.get("session_id") == session.id:
                    continue
                keep.append(evt)
            for evt in keep:
                self.completion_queue.put(evt)
            self._enqueue_completion_notification(session)
