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

    Mixed into ``ProcessRegistry``. Callers never hold ``self._lock``: each helper
    builds the redacted notice unlocked and takes the lock only for the queue swap/put.
    """

    def _completion_notification(self, session: "ProcessSession") -> dict:
        """The redacted completion notice for ``session``'s current fields.

        Caller must NOT hold ``self._lock``: redaction can look the owner up through
        the registry (``process_registry.get``) and run transform hooks."""
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
        return _redact_process_result(notification)

    def _enqueue_completion_notification(self, session: "ProcessSession") -> None:
        """Publish ``session``'s completion notice (the owner, after its checkpoint).

        Caller must NOT hold ``self._lock``. The notice is built outside the lock and put
        under it only while its exit fields still match the session, so a kill that
        stamps ``killed`` and then drains the queue (``_replace_stale_completion_notification``)
        either finds and swaps the reader's ``exited`` notice or makes the reader rebuild.
        That closes the durable-but-stale race on the live ``completion_queue`` payload."""
        while True:
            notification = self._completion_notification(session)
            with self._lock:
                if all(notification.get(k) == v for k, v in self._exit_fields(session).items()):
                    self.completion_queue.put(notification)
                    return

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
        ``_move_to_finished``.

        A corrected event is enqueued only when this session's stale
        ``completion`` was actually found and dropped: a consumer that already
        drained it (the TUI's ``queue.get`` does not take ``self._lock``) has
        already shown the stale ``exited`` payload, and a second event would
        duplicate the completion rather than correct the displayed one. With no
        stale event to swap, the durable ``save_completed_result`` re-stamp is
        the only correction the kill path can still make — fixing the live
        payload for an already-consumed event needs the consumer to respect a
        per-session kill gate (outside this queue helper)."""
        corrected = self._completion_notification(session)
        with self._lock:
            keep: list = []
            dropped_stale = False
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
                    dropped_stale = True
                    continue
                keep.append(evt)
            for evt in keep:
                self.completion_queue.put(evt)
            # Only enqueue a corrected event when the stale one was still on the
            # queue. If a consumer already drained it, a second event would
            # duplicate the completion (the TUI dedups by session, so the
            # corrected payload would be silently dropped and the stale
            # ``exited`` text would stay visible).
            if dropped_stale:
                self.completion_queue.put(corrected)
