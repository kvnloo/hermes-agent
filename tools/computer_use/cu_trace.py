"""Append-only computer-use wall-clock tracer (Phase 9).

Design constraints:
- monotonic timestamps only during a turn (no wall-clock syscalls in the hot path
  beyond ``time.monotonic``)
- events append to an in-memory list; serialization happens AFTER the turn
- the tracer must not be synchronous/expensive — no file I/O, no locks on the
  happy path beyond a contextvar write
- never required for correctness; missing context is a no-op

A turn looks like::

    cu_turn
    ├─ admission / transport / perception / decision / execution / recovery

Every span carries ``duration_ms`` plus optional attributes (provider, model,
native_pixels, model_call_reason, …). Model calls are counted separately so a
trajectory can answer: how many network/model RTTs, why, which were avoidable.
"""

from __future__ import annotations

import json
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterator, List, Optional

_active: ContextVar[Optional["CuTrace"]] = ContextVar("cu_trace_active", default=None)


@dataclass
class SpanEvent:
    name: str
    start_ms: float
    end_ms: float = 0.0
    duration_ms: float = 0.0
    success: bool = True
    attrs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelCallEvent:
    reason: str  # primary_agent | auxiliary_vision | smart_approval | recovery | local_router | other
    provider: str = ""
    model: str = ""
    duration_ms: float = 0.0
    success: bool = True
    attrs: Dict[str, Any] = field(default_factory=dict)


class CuTrace:
    """One CU turn's in-memory event buffer."""

    __slots__ = (
        "turn_id", "warm", "provider", "model", "_t0", "spans", "model_calls",
        "attrs", "_closed", "_lock",
    )

    def __init__(
        self,
        *,
        turn_id: str = "",
        warm: bool = False,
        provider: str = "",
        model: str = "",
        **attrs: Any,
    ) -> None:
        self.turn_id = turn_id or f"cu-{int(time.time() * 1000)}"
        self.warm = warm
        self.provider = provider
        self.model = model
        self.attrs = dict(attrs)
        self._t0 = time.monotonic()
        self.spans: List[SpanEvent] = []
        self.model_calls: List[ModelCallEvent] = []
        self._closed = False
        # Spans are almost always single-threaded per turn; lock only protects
        # rare cross-thread aux callbacks from racing the list append.
        self._lock = threading.Lock()

    def _now_ms(self) -> float:
        return (time.monotonic() - self._t0) * 1000.0

    @contextmanager
    def span(self, name: str, **attrs: Any) -> Iterator[Dict[str, Any]]:
        if self._closed:
            yield {}
            return
        start = self._now_ms()
        bag: Dict[str, Any] = dict(attrs)
        ok = True
        try:
            yield bag
        except Exception:
            ok = False
            raise
        finally:
            end = self._now_ms()
            ev = SpanEvent(
                name=name,
                start_ms=round(start, 3),
                end_ms=round(end, 3),
                duration_ms=round(end - start, 3),
                success=ok and bag.pop("_success", True) is not False,
                attrs=bag,
            )
            with self._lock:
                self.spans.append(ev)

    def record_model_call(
        self,
        reason: str,
        *,
        provider: str = "",
        model: str = "",
        duration_ms: float = 0.0,
        success: bool = True,
        **attrs: Any,
    ) -> None:
        if self._closed:
            return
        ev = ModelCallEvent(
            reason=reason or "other",
            provider=provider or self.provider,
            model=model or self.model,
            duration_ms=round(float(duration_ms or 0.0), 3),
            success=success,
            attrs=dict(attrs),
        )
        with self._lock:
            self.model_calls.append(ev)

    def close(self, **attrs: Any) -> Dict[str, Any]:
        if self._closed:
            return self.to_dict()
        self.attrs.update(attrs)
        self.attrs.setdefault("total_ms", round(self._now_ms(), 3))
        self._closed = True
        return self.to_dict()

    def model_call_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for call in self.model_calls:
            counts[call.reason] = counts.get(call.reason, 0) + 1
        return counts

    def span_totals_ms(self) -> Dict[str, float]:
        totals: Dict[str, float] = {}
        for span in self.spans:
            totals[span.name] = round(totals.get(span.name, 0.0) + span.duration_ms, 3)
        return totals

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "warm": self.warm,
            "provider": self.provider,
            "model": self.model,
            "attrs": dict(self.attrs),
            "spans": [asdict(s) for s in self.spans],
            "model_calls": [asdict(c) for c in self.model_calls],
            "model_call_counts": self.model_call_counts(),
            "span_totals_ms": self.span_totals_ms(),
        }

    def dumps(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), default=str)


@contextmanager
def cu_turn(
    *,
    turn_id: str = "",
    warm: bool = False,
    provider: str = "",
    model: str = "",
    **attrs: Any,
) -> Iterator[CuTrace]:
    """Activate a trace for the current context. Nested turns replace, then restore."""
    trace = CuTrace(turn_id=turn_id, warm=warm, provider=provider, model=model, **attrs)
    token = _active.set(trace)
    try:
        yield trace
    finally:
        if not trace._closed:
            trace.close()
        _active.reset(token)


def current() -> Optional[CuTrace]:
    return _active.get()


@contextmanager
def span(name: str, **attrs: Any) -> Iterator[Dict[str, Any]]:
    """No-op when no turn is active."""
    trace = _active.get()
    if trace is None:
        yield {}
        return
    with trace.span(name, **attrs) as bag:
        yield bag


def record_model_call(reason: str, **kwargs: Any) -> None:
    trace = _active.get()
    if trace is not None:
        trace.record_model_call(reason, **kwargs)


def bind_media_route(decision: Any) -> Dict[str, Any]:
    """Extract Phase-8 provenance attrs from a NativeToolResultPixelsDecision-like object."""
    return {
        "native_pixels": bool(getattr(decision, "native", False)),
        "native_pixels_reason": getattr(decision, "reason", "") or "",
        "model_vision": getattr(decision, "model_can_understand_images", None),
        "model_vision_source": getattr(decision, "model_vision_source", "") or "",
        "tool_result_media": getattr(decision, "transport_accepts_images_in_tool_results", None),
        "transport_source": getattr(decision, "transport_source", "") or "",
    }
