"""E23 block runner: time Hermes' real capture path per mode against one cua-driver, for ONE arm tree.

Run from the host with PYTHONPATH=<arm worktree> and HERMES_CUA_DRIVER_CMD pointing at e23_driver_wrapper.sh
(cua-driver runs inside the sandbox-desktop container; the transport is stdio over `docker exec -i`, the same
transport Hermes uses for a terminal-backend desktop). One process = one block; e23_run.sh interleaves blocks
A B B A ... so drift on the shared host hits both arms alike.

Every capture goes through CuaDriverBackend.capture(); the session's call_tool is wrapped only to time the
get_window_state round trip and record which selectors were sent. Rows are JSONL, one per capture.

--fake replaces the driver with an in-process stand-in that sleeps a fixed tree/grab cost and honours the
selectors. It exists ONLY to check this harness (positive control: a known difference must show up; A/A: none
must). Its numbers are MODELED and never evidence for the feature.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from types import SimpleNamespace

MODES = ("ax", "vision", "som")
_GWS_0_28_2 = ("capture_mode", "include_accessibility_tree", "include_screenshot", "max_depth", "max_dimension",
               "max_elements", "pid", "query", "screenshot_out_file", "session", "window_id")
_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAADUlEQVR4nGNgGAUgAAABCAABgukLHQAAAABJRU5ErkJggg=="


def _install_fake(backend, tree_ms: float, grab_ms: float) -> None:
    listed = SimpleNamespace(model_extra={}, tools=[SimpleNamespace(
        name="get_window_state", capabilities=None, model_extra={},
        inputSchema={"type": "object", "properties": {p: {} for p in _GWS_0_28_2}})])

    class _Mcp:
        async def list_tools(self):
            return listed

    asyncio.run(backend._session._populate_capabilities(_Mcp()))

    def call_tool(name, args, timeout=30.0):
        if name != "get_window_state":
            return {"isError": False, "structuredContent": {}}
        out = {"isError": False, "structuredContent": {"window_title": "Fake", "pid": 1, "window_id": 1}}
        if args.get("include_accessibility_tree") is not False:
            time.sleep(tree_ms / 1000)
            out["data"] = 'window_id=1 pid=1 elements=1\n\n- [0] push button "OK" [actions=[click]]\n'
            out["structuredContent"]["elements"] = [{"element_index": 0, "role": "push button", "label": "OK",
                                                     "frame": {"x": 1, "y": 1, "w": 2, "h": 2}}]
        if args.get("include_screenshot") is not False:
            time.sleep(grab_ms / 1000)
            out["images"], out["image_mime_types"] = [_PNG_B64], ["image/png"]
        return out

    backend._session.call_tool = call_tool
    backend._session.start = lambda: None


def _targets(backend, wanted):
    windows = backend.list_windows()
    out = []
    for name in wanted:
        hit = [w for w in windows if name.lower() in f"{w.get('app_name', '')} {w.get('title', '')}".lower()]
        if not hit:
            raise SystemExit(f"no window matches {name!r}; saw {[(w.get('app_name'), w.get('title')) for w in windows]}")
        out.append((name, hit[0]["pid"], hit[0]["window_id"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--block", required=True)
    ap.add_argument("--n", type=int, default=10, help="timed captures per (target, mode) in this block")
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--targets", default="Terminal,Chromium")
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--out", required=True)
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--fake-tree-ms", type=float, default=30.0)
    ap.add_argument("--fake-grab-ms", type=float, default=10.0)
    a = ap.parse_args()

    from tools.computer_use import cua_backend_capture
    from tools.computer_use.cua_backend import CuaDriverBackend

    tree_file = os.path.realpath(cua_backend_capture.__file__)
    backend = CuaDriverBackend()
    if a.fake:
        _install_fake(backend, a.fake_tree_ms, a.fake_grab_ms)
        targets = [(t, 1, 1) for t in a.targets.split(",")]
    else:
        backend.start()
        targets = _targets(backend, a.targets.split(","))

    real_call = backend._session.call_tool
    last = {}

    def timed_call(name, args, timeout=30.0):
        t0 = time.perf_counter()
        try:
            return real_call(name, args, timeout)
        finally:
            if name == "get_window_state":
                last["gws_ms"] = last.get("gws_ms", 0.0) + (time.perf_counter() - t0) * 1000
                last["gws_calls"] = last.get("gws_calls", 0) + 1
                last["sent"] = sorted(k for k in ("include_screenshot", "include_accessibility_tree") if k in args)

    backend._session.call_tool = timed_call
    modes = a.modes.split(",")
    cells = [(t, m) for t in targets for m in modes]
    with open(a.out, "a", encoding="utf-8") as fh:
        for i in range(-a.warmup, a.n):
            rot = i % len(cells)
            for (name, pid, wid), mode in cells[rot:] + cells[:rot]:  # rotate order so no cell always runs first
                last.clear()
                row = {"arm": a.arm, "block": a.block, "target": name, "mode": mode, "i": i, "warmup": i < 0,
                       "fake": a.fake, "tree_file": tree_file}
                t0 = time.perf_counter()
                try:
                    cap = backend.capture(mode=mode, pid=pid, window_id=wid)
                    row.update(ok=True, png_bytes=cap.png_bytes_len, n_elements=len(cap.elements),
                               width=cap.width, height=cap.height, title_nonempty=bool(cap.window_title))
                except Exception as exc:
                    msg = f"{type(exc).__name__}: {exc}"
                    row.update(ok=False, error=msg[:300], timeout=("timed out" in msg or "timeout" in msg.lower()))
                row["wall_ms"] = round((time.perf_counter() - t0) * 1000, 3)
                row.update({k: (round(v, 3) if isinstance(v, float) else v) for k, v in last.items()})
                fh.write(json.dumps(row, sort_keys=True) + "\n")
    if not a.fake:
        backend.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
