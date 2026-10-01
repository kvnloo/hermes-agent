"""Capture lanes negotiated from the ``get_window_state`` schema a real cua-driver advertises.

vision discards the accessibility tree and ax discards the screenshot, so neither should be produced when the
driver's ``tools/list`` schema offers the matching selector. The capability map is filled through the
production ``_CuaDriverSession._populate_capabilities``; only the driver calls (MCP and the CLI re-fetch) are
faked, and they answer the way the Linux driver does (a ``false`` selector drops that half of the result).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

# get_window_state input properties from `tools/list` of the Linux x86_64 release binaries.
_GWS_0_21_0 = ("capture_mode", "include_screenshot", "max_depth", "max_elements", "pid", "query",
               "screenshot_out_file", "session", "window_id")
_GWS_0_28_2 = (*_GWS_0_21_0, "include_accessibility_tree", "max_dimension")
_SELECTORS = ("include_accessibility_tree", "include_screenshot")

_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAADUlEQVR4nGNgGAUgAAABCAABgukLHQAAAABJRU5ErkJggg=="


def _driver_reply(args):
    out = {"isError": False, "structuredContent": {"window_id": 456, "pid": 123, "window_title": "Terminal"}}
    if args.get("include_accessibility_tree") is not False:
        out["data"] = 'window_id=456 pid=123 elements=1\n\n- [0] push button "OK" [actions=[click]]\n'
        out["structuredContent"]["elements"] = [
            {"element_index": 0, "role": "push button", "label": "OK", "frame": {"x": 10, "y": 20, "w": 30, "h": 40}}]
    if args.get("include_screenshot") is not False:
        out["images"], out["image_mime_types"] = [_PNG_B64], ["image/png"]
    return out


def _backend(monkeypatch, gws_properties, mcp_images=True):
    from tools.computer_use.cua_backend import CuaDriverBackend

    backend = CuaDriverBackend()
    listed = SimpleNamespace(tools=[SimpleNamespace(
        name="get_window_state", capabilities=None, model_extra={},
        inputSchema={"type": "object", "additionalProperties": False,
                     "properties": {name: {} for name in gws_properties}})], model_extra={})

    class _McpSession:
        async def list_tools(self):
            return listed

    asyncio.run(backend._session._populate_capabilities(_McpSession()))
    calls = []

    def _driver(name, args, images=True):
        calls.append((name, dict(args)))
        out = _driver_reply(args)
        if not images:  # an imageless MCP reply sends vision to the CLI re-fetch
            out.pop("images", None)
        return out

    monkeypatch.setattr(backend._session, "call_tool", lambda name, args, timeout=30.0: _driver(name, args, mcp_images))
    monkeypatch.setattr(backend._session, "_call_tool_via_cli", lambda name, args, timeout: _driver(name, args))
    return backend, calls


@pytest.mark.parametrize("mode, selector, mcp_images", [
    pytest.param("ax", "include_screenshot", True, id="ax"),
    pytest.param("vision", "include_accessibility_tree", True, id="vision"),
    pytest.param("vision", "include_accessibility_tree", False, id="vision-cli-refetch"),
])
def test_capture_skips_the_half_its_mode_discards(monkeypatch, mode, selector, mcp_images):
    backend, calls = _backend(monkeypatch, _GWS_0_28_2, mcp_images)

    cap = backend.capture(mode=mode, pid=123, window_id=456)

    sent = [args for name, args in calls if name == "get_window_state"]
    assert sent and all(args.get(selector) is False for args in sent)
    assert not any(all(key in args for key in _SELECTORS) for args in sent)
    if mode == "ax":
        assert cap.png_b64 is None and [e.label for e in cap.elements] == ["OK"]
    else:  # no tree to read the title from: it has to come from the structured window metadata
        assert cap.png_b64 == _PNG_B64 and cap.elements == [] and cap.window_title == "Terminal"


@pytest.mark.parametrize("mode, gws_properties", [("som", _GWS_0_28_2), ("vision", _GWS_0_21_0), ("ax", ())])
def test_som_and_drivers_without_the_selector_keep_the_full_request(monkeypatch, mode, gws_properties):
    backend, calls = _backend(monkeypatch, gws_properties)

    backend.capture(mode=mode, pid=123, window_id=456)

    sent = [args for name, args in calls if name == "get_window_state"]
    assert sent and not any(selector in args for args in sent for selector in _SELECTORS)
