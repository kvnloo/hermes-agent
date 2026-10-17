"""Read-only process observers. Sinks must never change process lifecycle outcomes."""

from contextlib import suppress


class ProcessEventsMixin:
    on_change = None

    def _emit_output(self, session, chunk: str) -> None:
        """Forward a chunk to the live-output sink; called from reader threads, never raises."""
        sink = self.on_output
        if sink is None or not chunk:
            return
        with suppress(Exception):
            sink(session, chunk)

    def _emit_process_changed(self, session) -> None:
        """Metadata invalidation, including quiet jobs without completion notifications."""
        sink = self.on_change
        if sink is not None:
            with suppress(Exception):
                sink(session)
