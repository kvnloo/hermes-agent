"""Unit tests for tools.computer_use.cu_trace (Phase 9)."""

from __future__ import annotations

import json
import time
from types import SimpleNamespace

from tools.computer_use import cu_trace


def test_span_records_duration_without_active_io():
    with cu_trace.cu_turn(turn_id="t1", warm=False) as tr:
        with tr.span("admission.backend_resolve"):
            time.sleep(0.01)
        with tr.span("perception.capture", capture_changed=True):
            pass
        with tr.span("execution.dispatch", action="click"):
            pass
        tr.record_model_call("auxiliary_vision", provider="openrouter", model="g", duration_ms=12.5)
        out = tr.close(success=True)

    assert out["turn_id"] == "t1"
    assert out["warm"] is False
    names = [s["name"] for s in out["spans"]]
    assert names == [
        "admission.backend_resolve",
        "perception.capture",
        "execution.dispatch",
    ]
    assert out["spans"][0]["duration_ms"] >= 8.0
    assert out["model_call_counts"] == {"auxiliary_vision": 1}
    assert "admission.backend_resolve" in out["span_totals_ms"]


def test_span_helper_is_noop_without_active_turn():
    with cu_trace.span("should_not_record", x=1) as bag:
        bag["y"] = 2
    assert cu_trace.current() is None


def test_nested_turn_restores_outer():
    with cu_trace.cu_turn(turn_id="outer") as outer:
        with cu_trace.cu_turn(turn_id="inner") as inner:
            with cu_trace.span("inner_only"):
                pass
            assert cu_trace.current() is inner
        assert cu_trace.current() is outer
        assert [s.name for s in outer.spans] == []
        assert [s.name for s in inner.spans] == ["inner_only"]


def test_bind_media_route_provenance():
    d = SimpleNamespace(
        native=True,
        reason="both_axes_positive",
        model_can_understand_images=True,
        model_vision_source="catalog",
        transport_accepts_images_in_tool_results=True,
        transport_source="explicit_attestation:deepseek-flash",
    )
    attrs = cu_trace.bind_media_route(d)
    assert attrs == {
        "native_pixels": True,
        "native_pixels_reason": "both_axes_positive",
        "model_vision": True,
        "model_vision_source": "catalog",
        "tool_result_media": True,
        "transport_source": "explicit_attestation:deepseek-flash",
    }


def test_dumps_is_json_and_cheap():
    with cu_trace.cu_turn(turn_id="j") as tr:
        with tr.span("perception.media_route_resolve", **cu_trace.bind_media_route(
            SimpleNamespace(
                native=False, reason="transport_not_attested",
                model_can_understand_images=True, model_vision_source="catalog",
                transport_accepts_images_in_tool_results=False, transport_source="unknown",
            )
        )):
            pass
        payload = json.loads(tr.dumps())
    assert payload["model_call_counts"] == {}
    assert payload["spans"][0]["attrs"]["native_pixels"] is False
