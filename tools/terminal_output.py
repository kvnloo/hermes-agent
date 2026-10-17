"""Call-scoped foreground output tap; internal commands and background jobs never inherit it."""
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
import logging
import uuid

_output: ContextVar[Callable[[str], None] | None] = ContextVar("terminal_output", default=None)


def current_output_callback() -> Callable[[str], None] | None:
    return _output.get()


@contextmanager
def tool_output_scope(callback, name: str, call_id: str) -> Iterator[None]:
    sink = None
    if callback is not None and name in {"terminal", "bash", "shell"}:
        stream_id = uuid.uuid4().hex

        def emit(event, text=None):
            try:
                callback(event, name, text, None, tool_call_id=call_id, stream_id=stream_id)
            except Exception:
                logging.debug("Terminal output callback failed", exc_info=True)

        emit("tool.output.open")
        sink = lambda text: emit("tool.output.delta", text)
    token = _output.set(sink)
    try:
        yield
    finally:
        _output.reset(token)


class TerminalOutputTap:
    """Strip the shell's private CWD trailer even when its prefix crosses read boundaries."""

    def __init__(self, callback: Callable[[str], None], marker: str):
        self.callback = callback
        self.prefix = "\n" + marker
        self.pending = ""
        self.trailer = False

    def feed(self, text: str) -> None:
        if self.trailer:
            return
        text = self.pending + text
        self.pending = ""
        marker_at = text.find(self.prefix)
        if marker_at >= 0:
            self.trailer = True
            self._send(text[:marker_at])
            return
        retained = min(len(text), len(self.prefix) - 1)
        while retained and not self.prefix.startswith(text[-retained:]):
            retained -= 1
        if retained:
            self.pending = text[-retained:]
            text = text[:-retained]
        self._send(text)

    def _send(self, text: str) -> None:
        if text:
            try:
                self.callback(text)
            except Exception:
                logging.debug("Terminal output tap failed", exc_info=True)

    def finish(self) -> None:
        self._send(self.pending)
        self.pending = ""
