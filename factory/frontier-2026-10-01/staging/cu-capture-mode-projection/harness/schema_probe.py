"""X1: what does a real cua-driver release advertise for get_window_state, as seen by Hermes' own session seam?

Runs the production ``_CuaDriverSession`` (stdio MCP, ``initialize`` + ``tools/list``) against one real driver
binary selected with HERMES_CUA_DRIVER_CMD, then records:
  - the get_window_state inputSchema property names (``_tool_schemas``),
  - whether a standalone ``screenshot`` tool is advertised (vision mode tries it BEFORE get_window_state),
  - ``supports_input_property`` for the two output selectors (the gate both #126447 and the donor use),
  - ``capabilities_discovered`` / ``capability_version``.
No window is captured: there is no display in the sandbox, and nothing here needs one.

Invoke inside bwrap --unshare-net with HOME/HERMES_HOME pointed at a scratch dir (see run_schema_probe.sh).
Prints one JSON object on stdout.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import time

# Loopback-only egress guard (lifted from evals/provider_fallback/probe_104260.py's pattern): the sandbox has no
# network namespace route anyway; this makes any attempt visible instead of silent.
_EGRESS: list = []
_real_connect = socket.socket.connect


def _guarded_connect(self, address):  # pragma: no cover - only fires on an egress attempt
    host = address[0] if isinstance(address, tuple) else str(address)
    if isinstance(address, tuple) and host not in ("127.0.0.1", "::1", "localhost"):
        _EGRESS.append(str(address))
        raise OSError(f"egress blocked by probe: {address}")
    return _real_connect(self, address)


socket.socket.connect = _guarded_connect


def main() -> int:
    worktree = os.environ["PROBE_WORKTREE"]
    sys.path.insert(0, worktree)
    for forbidden in filter(None, os.environ.get("PROBE_FORBIDDEN", "").split(os.pathsep)):  # live roots
        assert not os.path.realpath(os.environ["HERMES_HOME"]).startswith(os.path.realpath(forbidden))
    from tools.computer_use import cua_backend_capture, cua_backend_session
    from tools.computer_use.cua_backend_session import _AsyncBridge, _CuaDriverSession

    assert os.path.realpath(cua_backend_capture.__file__).startswith(os.path.realpath(worktree)), cua_backend_capture.__file__
    out = {"driver_cmd": os.environ.get("HERMES_CUA_DRIVER_CMD"),
           "module_file": os.path.relpath(cua_backend_session.__file__, worktree)}
    session = _CuaDriverSession(_AsyncBridge())
    t0 = time.monotonic()
    try:
        session.start()
        out["start_ok"] = True
    except Exception as exc:  # recorded, never hidden
        out["start_ok"] = False
        out["start_error"] = f"{type(exc).__name__}: {exc}"[:500]
    out["start_s"] = round(time.monotonic() - t0, 3)
    schema = session._tool_schemas.get("get_window_state", {})
    props = schema.get("properties") if isinstance(schema, dict) else None
    out.update({
        "capabilities_discovered": session.capabilities_discovered,
        "capability_version": session.capability_version,
        "tool_count": len(session._capabilities),
        "has_get_window_state": session._has_tool("get_window_state"),
        "has_screenshot_tool": session._has_tool("screenshot"),
        "gws_properties": sorted(props) if isinstance(props, dict) else None,
        "gws_additional_properties": schema.get("additionalProperties") if isinstance(schema, dict) else None,
        "gws_required": schema.get("required") if isinstance(schema, dict) else None,
        "supports_include_screenshot": session.supports_input_property("get_window_state", "include_screenshot"),
        "supports_include_accessibility_tree": session.supports_input_property(
            "get_window_state", "include_accessibility_tree"),
    })
    if out.get("start_ok") and os.environ.get("PROBE_DISPATCH") == "1":
        # Does the driver reject an UNADVERTISED selector? A non-existent pid/window keeps this display-free: a
        # driver that accepts the argument shape answers with its stale-target error; one that validates the
        # schema (additionalProperties:false) answers with an argument error first.
        base = {"pid": 999999, "window_id": 1}
        dispatch = {}
        for label, extra in (("base", {}), ("include_screenshot_false", {"include_screenshot": False}),
                             ("include_accessibility_tree_false", {"include_accessibility_tree": False}),
                             ("bogus_property", {"zz_not_a_property": False})):
            try:
                res = session.call_tool("get_window_state", {**base, **extra}, timeout=20.0)
                text = res.get("data") if isinstance(res.get("data"), str) else json.dumps(res.get("data"))[:300]
                dispatch[label] = {"isError": res.get("isError"), "text": (text or "")[:240]}
            except Exception as exc:
                dispatch[label] = {"exception": f"{type(exc).__name__}: {exc}"[:240]}
        out["dispatch"] = dispatch
    try:
        session.stop()
    except Exception as exc:
        out["stop_error"] = f"{type(exc).__name__}: {exc}"[:300]
    out["egress_attempts"] = _EGRESS
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
