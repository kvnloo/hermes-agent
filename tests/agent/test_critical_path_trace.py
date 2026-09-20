from __future__ import annotations

import pytest

from agent.critical_path_trace import (
    TurnLatencyTrace,
    bind_turn_trace,
    current_turn_trace,
    trace_span,
)


def test_trace_span_is_noop_without_active_turn_trace():
    assert current_turn_trace() is None
    with trace_span("core", "core", "noop") as span_id:
        assert span_id is None
    assert current_turn_trace() is None


def test_bind_turn_trace_records_content_free_span():
    with bind_turn_trace("turn-1") as trace:
        assert current_turn_trace() is trace
        with trace_span("memory", "hindsight", "prefetch") as span_id:
            assert span_id == "s0001"

    receipt = trace.receipt()
    assert receipt["turn_id"] == "turn-1"
    assert receipt["span_count"] == 1
    assert receipt["dropped_spans"] == 0
    span = receipt["spans"][0]
    assert span["owner_kind"] == "memory"
    assert span["owner_id"] == "hindsight"
    assert span["operation"] == "prefetch"
    assert span["blocking"] is True
    assert span["parent_span_id"] is None
    assert span["duration_ms"] >= 0
    assert "content" not in span
    assert "payload" not in span


def test_nested_spans_preserve_parent_identity():
    with bind_turn_trace("turn-2") as trace:
        with trace_span("plugin", "router", "llm_execution") as outer:
            with trace_span("provider", "openrouter", "inference") as inner:
                assert outer == "s0001"
                assert inner == "s0002"

    spans = {span.span_id: span for span in trace.snapshot()}
    assert spans["s0001"].parent_span_id is None
    assert spans["s0002"].parent_span_id == "s0001"
    assert spans["s0001"].duration_ms >= spans["s0002"].duration_ms


def test_nonblocking_span_is_explicit():
    with bind_turn_trace("turn-3") as trace:
        with trace_span("memory", "builtin", "sync_turn", blocking=False):
            pass

    [span] = trace.snapshot()
    assert span.blocking is False


def test_trace_is_bounded_and_counts_dropped_spans():
    with bind_turn_trace("turn-4", max_spans=2) as trace:
        for _ in range(3):
            with trace_span("core", "core", "work"):
                pass

    assert len(trace.snapshot()) == 2
    assert trace.dropped_spans == 1


def test_trace_restores_previous_context():
    outer = TurnLatencyTrace("outer")
    from agent import critical_path_trace as mod

    token = mod._ACTIVE_TRACE.set(outer)
    try:
        with bind_turn_trace("inner") as inner:
            assert current_turn_trace() is inner
        assert current_turn_trace() is outer
    finally:
        mod._ACTIVE_TRACE.reset(token)


def test_span_is_recorded_when_wrapped_work_raises():
    with pytest.raises(RuntimeError, match="boom"):
        with bind_turn_trace("turn-5") as trace:
            with trace_span("plugin", "broken", "pre_llm_call"):
                raise RuntimeError("boom")

    [span] = trace.snapshot()
    assert span.owner_id == "broken"
    assert span.duration_ms >= 0


@pytest.mark.parametrize("field,value", [
    ("turn_id", ""),
    ("turn_id", "a\nb"),
])
def test_turn_id_rejects_empty_or_multiline_labels(field, value):
    with pytest.raises(ValueError, match=field):
        TurnLatencyTrace(value)
