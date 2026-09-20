"""Content-free critical-path timing primitives for one Hermes turn.

This module deliberately knows nothing about prompts, messages, tool results, or
provider payloads. Runtime owners add spans around boundaries they already own;
consumers decide how to render or aggregate them.

The active trace is held in contextvars so normal async/context-propagating Hermes
paths inherit it without a process-global mutable "current turn".
"""

from __future__ import annotations

import contextlib
import contextvars
import threading
import time
from dataclasses import dataclass
from typing import Iterator, Optional


DEFAULT_MAX_SPANS_PER_TURN = 256
_MAX_LABEL_CHARS = 128

_ACTIVE_TRACE: contextvars.ContextVar["TurnLatencyTrace | None"] = contextvars.ContextVar(
    "hermes_turn_latency_trace", default=None
)
_ACTIVE_SPAN_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "hermes_turn_latency_parent_span", default=None
)


def _label(value: str, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    if "\n" in text or "\r" in text:
        raise ValueError(f"{field} must be one line")
    if len(text) > _MAX_LABEL_CHARS:
        raise ValueError(f"{field} must be <= {_MAX_LABEL_CHARS} characters")
    return text


@dataclass(frozen=True)
class CriticalPathSpan:
    """One completed, content-free runtime span."""

    span_id: str
    parent_span_id: Optional[str]
    turn_id: str
    owner_kind: str
    owner_id: str
    operation: str
    blocking: bool
    start_offset_ms: float
    duration_ms: float

    def as_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "turn_id": self.turn_id,
            "owner_kind": self.owner_kind,
            "owner_id": self.owner_id,
            "operation": self.operation,
            "blocking": self.blocking,
            "start_offset_ms": self.start_offset_ms,
            "duration_ms": self.duration_ms,
        }


class TurnLatencyTrace:
    """Bounded, thread-safe completed-span buffer for one turn."""

    def __init__(self, turn_id: str, *, max_spans: int = DEFAULT_MAX_SPANS_PER_TURN):
        self.turn_id = _label(turn_id, "turn_id")
        if isinstance(max_spans, bool) or not isinstance(max_spans, int) or max_spans <= 0:
            raise ValueError("max_spans must be a positive integer")
        self.max_spans = max_spans
        self._started_ns = time.monotonic_ns()
        self._lock = threading.Lock()
        self._sequence = 0
        self._spans: list[CriticalPathSpan] = []
        self._dropped_spans = 0

    def next_span_id(self) -> str:
        with self._lock:
            self._sequence += 1
            return f"s{self._sequence:04d}"

    def finish_span(
        self,
        *,
        span_id: str,
        parent_span_id: Optional[str],
        owner_kind: str,
        owner_id: str,
        operation: str,
        blocking: bool,
        started_ns: int,
        ended_ns: int,
    ) -> None:
        span = CriticalPathSpan(
            span_id=span_id,
            parent_span_id=parent_span_id,
            turn_id=self.turn_id,
            owner_kind=owner_kind,
            owner_id=owner_id,
            operation=operation,
            blocking=bool(blocking),
            start_offset_ms=max(0.0, (started_ns - self._started_ns) / 1_000_000.0),
            duration_ms=max(0.0, (ended_ns - started_ns) / 1_000_000.0),
        )
        with self._lock:
            if len(self._spans) >= self.max_spans:
                self._dropped_spans += 1
                return
            self._spans.append(span)

    @property
    def dropped_spans(self) -> int:
        with self._lock:
            return self._dropped_spans

    def snapshot(self) -> tuple[CriticalPathSpan, ...]:
        with self._lock:
            return tuple(self._spans)

    def receipt(self) -> dict:
        spans = self.snapshot()
        return {
            "turn_id": self.turn_id,
            "span_count": len(spans),
            "dropped_spans": self.dropped_spans,
            "spans": [span.as_dict() for span in spans],
        }


def current_turn_trace() -> Optional[TurnLatencyTrace]:
    return _ACTIVE_TRACE.get()


@contextlib.contextmanager
def bind_turn_trace(
    turn_id: str, *, max_spans: int = DEFAULT_MAX_SPANS_PER_TURN
) -> Iterator[TurnLatencyTrace]:
    """Bind one trace to the current context and restore the previous binding."""
    trace = TurnLatencyTrace(turn_id, max_spans=max_spans)
    trace_token = _ACTIVE_TRACE.set(trace)
    parent_token = _ACTIVE_SPAN_ID.set(None)
    try:
        yield trace
    finally:
        _ACTIVE_SPAN_ID.reset(parent_token)
        _ACTIVE_TRACE.reset(trace_token)


@contextlib.contextmanager
def trace_span(
    owner_kind: str,
    owner_id: str,
    operation: str,
    *,
    blocking: bool = True,
) -> Iterator[Optional[str]]:
    """Record a nested span when a turn trace is active; otherwise be a no-op."""
    trace = _ACTIVE_TRACE.get()
    if trace is None:
        yield None
        return

    # Validate metadata before entering the wrapped operation so trace bookkeeping
    # can never replace an exception raised by the operation itself.
    normalized_owner_kind = _label(owner_kind, "owner_kind")
    normalized_owner_id = _label(owner_id, "owner_id")
    normalized_operation = _label(operation, "operation")

    span_id = trace.next_span_id()
    parent_span_id = _ACTIVE_SPAN_ID.get()
    started_ns = time.monotonic_ns()
    parent_token = _ACTIVE_SPAN_ID.set(span_id)
    try:
        yield span_id
    finally:
        ended_ns = time.monotonic_ns()
        _ACTIVE_SPAN_ID.reset(parent_token)
        trace.finish_span(
            span_id=span_id,
            parent_span_id=parent_span_id,
            owner_kind=normalized_owner_kind,
            owner_id=normalized_owner_id,
            operation=normalized_operation,
            blocking=blocking,
            started_ns=started_ns,
            ended_ns=ended_ns,
        )
