"""Phase 9: handle_computer_use / capture path emit cu_trace spans + model calls."""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tools.computer_use import cu_trace
from tools.computer_use.backend import CaptureResult, UIElement
from tools.computer_use import tool as cu_tool

_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAADUlEQVR4nG"
    "NgGAUgAAABCAABgukLHQAAAABJRU5ErkJggg=="
)


@pytest.fixture(autouse=True)
def _clear_route_cache():
    cu_tool._AUX_VISION_ROUTE_CACHE.clear()
    yield
    cu_tool._AUX_VISION_ROUTE_CACHE.clear()


def _make_capture(**kwargs):
    raw = base64.b64decode(_PNG_B64, validate=False)
    return CaptureResult(
        mode=kwargs.get("mode", "vision"),
        width=kwargs.get("width", 8),
        height=kwargs.get("height", 8),
        png_b64=kwargs.get("png_b64", _PNG_B64),
        elements=kwargs.get("elements", [
            UIElement(index=0, role="AXButton", label="Go", bounds=(1, 1, 10, 10)),
        ]),
        app=kwargs.get("app", "App"),
        window_title=kwargs.get("window_title", "Win"),
        png_bytes_len=len(raw),
    )


class _FakeBackend:
    def capture(self, mode="som", **kwargs):
        return _make_capture(mode=mode, app=kwargs.get("app") or "App")


def test_handle_computer_use_records_admission_and_dispatch_spans():
    backend = _FakeBackend()
    with patch.object(cu_tool, "_get_backend", return_value=backend), \
         patch.object(cu_tool, "_reject_unsafe", return_value=None), \
         patch.object(cu_tool, "_request_approval", return_value=None), \
         patch.object(cu_tool, "_dispatch", return_value=json.dumps({"ok": True})):
        out = cu_tool.handle_computer_use(
            {"action": "click", "x": 1, "y": 2},
            session_id="s1",
            cu_turn_id="traj-warm-click",
            cu_warm=True,
        )
    assert json.loads(out)["ok"] is True
    tr = cu_tool.handle_computer_use.last_trace
    assert tr["turn_id"] == "traj-warm-click"
    assert tr["warm"] is True
    names = [s["name"] for s in tr["spans"]]
    assert "admission.unsafe_check" in names
    assert "admission.backend_resolve" in names
    assert "execution.dispatch" in names


def test_capture_action_records_perception_spans():
    backend = _FakeBackend()

    def _dispatch(b, action, args, session_id=None):
        return cu_tool._do_capture(b, action, args, session_id=session_id)

    with patch.object(cu_tool, "_get_backend", return_value=backend), \
         patch.object(cu_tool, "_reject_unsafe", return_value=None), \
         patch.object(cu_tool, "_request_approval", return_value=None), \
         patch.object(cu_tool, "_dispatch", side_effect=_dispatch), \
         patch.object(cu_tool, "_should_route_through_aux_vision", return_value=False):
        out = cu_tool.handle_computer_use(
            {"action": "capture", "mode": "vision"},
            session_id="s-cap",
            cu_turn_id="traj-visual",
            cu_warm=False,
        )
    assert isinstance(out, (dict, str))
    tr = cu_tool.handle_computer_use.last_trace
    names = [s["name"] for s in tr["spans"]]
    assert "perception.capture" in names
    assert "perception.accessibility_projection" in names
    assert tr["attrs"].get("capture_changed") is True
    assert tr["attrs"].get("native_pixels") is True or tr["attrs"].get("route") == "native_pixels"


def test_aux_vision_records_model_call(tmp_path):
    cap = _make_capture()

    def _fake_get(*_a, **_k):
        return tmp_path

    with cu_trace.cu_turn(turn_id="aux") as tr, \
         patch("hermes_constants.get_hermes_dir", _fake_get), \
         patch("model_tools._run_async", return_value=json.dumps({"analysis": "a button"})):
        routed = cu_tool._route_capture_through_aux_vision(cap, summary="sum")
        out = tr.close(success=True)

    assert routed is not None
    payload = json.loads(routed) if isinstance(routed, str) else routed
    assert "a button" in json.dumps(payload)
    assert out["model_call_counts"].get("auxiliary_vision") == 1
    assert any(s["name"] == "perception.aux_vision" for s in out["spans"])


def test_media_route_resolve_span_carries_provenance():
    cu_tool._AUX_VISION_ROUTE_CACHE.clear()
    decision = SimpleNamespace(
        native=True,
        reason="both_axes_positive",
        model_can_understand_images=True,
        model_vision_source="catalog",
        transport_accepts_images_in_tool_results=True,
        transport_source="explicit_attestation:deepseek-flash",
    )
    with cu_trace.cu_turn(turn_id="route") as tr, \
         patch("agent.auxiliary_client._read_main_provider", return_value="deepseek"), \
         patch("agent.auxiliary_client._read_main_model", return_value="deepseek-flash"), \
         patch("hermes_cli.config.load_config", return_value={}), \
         patch("tools.computer_use.vision_routing.should_route_capture_to_aux_vision",
               return_value=False), \
         patch("tools.vision_tools.resolve_native_tool_result_pixels", return_value=decision):
        assert cu_tool._should_route_through_aux_vision() is False
        out = tr.close()

    route_spans = [s for s in out["spans"] if s["name"] == "perception.media_route_resolve"]
    assert len(route_spans) == 1
    attrs = route_spans[0]["attrs"]
    assert attrs["native_pixels"] is True
    assert attrs["model_vision_source"] == "catalog"
    assert attrs["transport_source"] == "explicit_attestation:deepseek-flash"
    assert attrs["route"] == "native_pixels"
