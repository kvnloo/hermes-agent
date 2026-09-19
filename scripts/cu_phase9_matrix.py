#!/usr/bin/env python3
"""Phase 9 CU wall-clock matrix — six trajectories × cold/warm.

Runs against a deterministic fake backend by default so spans and model-call
counts are attributable without perturbing Kevin's desktop. Set
``CU_PERF_LIVE=1`` to attempt live cua-driver paths (still must use hypr
isolation when headed).

Outputs JSONL + a ranked-span summary under ``.cu-perf-report/phase9/``.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / ".cu-perf-report" / "phase9"


def _png() -> str:
    return (
        "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAADUlEQVR4nG"
        "NgGAUgAAABCAABgukLHQAAAABJRU5ErkJggg=="
    )


def _fake_backend():
    import base64
    from tools.computer_use.backend import ActionResult, CaptureResult, UIElement

    class B:
        def __init__(self):
            self.n = 0

        def capture(self, mode="som", **kwargs):
            self.n += 1
            # Alternate digest material via window_title so "changed frame" can flip.
            title = kwargs.get("_title") or f"Win-{self.n}"
            raw = base64.b64decode(_png(), validate=False)
            return CaptureResult(
                mode=mode, width=8, height=8, png_b64=_png(),
                elements=[UIElement(index=0, role="AXButton", label="Go",
                                    bounds=(1, 1, 10, 10))],
                app=kwargs.get("app") or "App", window_title=title,
                png_bytes_len=len(raw),
            )

        def click(self, **kwargs):
            time.sleep(0.002)
            return ActionResult(ok=True, action="click", message="clicked")

        def type_text(self, text, **kwargs):
            time.sleep(0.002)
            return ActionResult(ok=True, action="type", message=f"typed {text!r}")

        def wait(self, seconds):
            time.sleep(min(float(seconds), 0.01))
            return ActionResult(ok=True, action="wait", message="waited")

        def focus_app(self, app, raise_window=False):
            return ActionResult(ok=True, action="focus_app", message=f"focus {app}")

        def list_apps(self):
            return [{"name": "App"}]

        def list_windows(self):
            return [{"title": "Win"}]

    return B()


def _run_tool(action: str, args: Dict[str, Any], *, warm: bool, turn_id: str,
              backend, route_aux: bool = False) -> Dict[str, Any]:
    from tools.computer_use import tool as cu_tool

    cu_tool._AUX_VISION_ROUTE_CACHE.clear()
    payload = {"action": action, **args}
    with patch.object(cu_tool, "_get_backend", return_value=backend), \
         patch.object(cu_tool, "_reject_unsafe", return_value=None), \
         patch.object(cu_tool, "_request_approval", return_value=None), \
         patch.object(cu_tool, "_should_route_through_aux_vision", return_value=route_aux):
        if route_aux:
            with patch("model_tools._run_async",
                       return_value=json.dumps({"analysis": "fake aux vision"})):
                t0 = time.perf_counter()
                cu_tool.handle_computer_use(
                    payload, session_id=f"phase9-{turn_id}",
                    cu_turn_id=turn_id, cu_warm=warm,
                )
                wall_ms = (time.perf_counter() - t0) * 1000.0
        else:
            t0 = time.perf_counter()
            cu_tool.handle_computer_use(
                payload, session_id=f"phase9-{turn_id}",
                cu_turn_id=turn_id, cu_warm=warm,
            )
            wall_ms = (time.perf_counter() - t0) * 1000.0
    tr = getattr(cu_tool.handle_computer_use, "last_trace", {}) or {}
    tr = dict(tr)
    tr["wall_ms"] = round(wall_ms, 3)
    tr["trajectory"] = turn_id.rsplit("-", 1)[0] if "-" in turn_id else turn_id
    return tr


def traj_warm_click_type(warm: bool) -> Dict[str, Any]:
    b = _fake_backend()
    # cold/warm: second call on same backend instance for warm
    label = "warm_click_type"
    tid = f"{label}-{'warm' if warm else 'cold'}"
    if warm:
        _run_tool("click", {"x": 1, "y": 2}, warm=False, turn_id=f"{label}-preheat", backend=b)
    return _run_tool("type", {"text": "hi"}, warm=warm, turn_id=tid, backend=b)


def traj_changed_visual(warm: bool, *, native: bool) -> Dict[str, Any]:
    b = _fake_backend()
    label = "changed_visual_native" if native else "changed_visual_aux"
    tid = f"{label}-{'warm' if warm else 'cold'}"
    if warm:
        _run_tool("capture", {"mode": "vision"}, warm=False, turn_id=f"{label}-preheat",
                  backend=b, route_aux=not native)
    return _run_tool("capture", {"mode": "vision"}, warm=warm, turn_id=tid,
                     backend=b, route_aux=not native)


def traj_approval_type(warm: bool) -> Dict[str, Any]:
    """Approval span + type. Smart-approval LLM is not invoked (gate mocked)."""
    from tools.computer_use import tool as cu_tool
    b = _fake_backend()
    label = "approval_type"
    tid = f"{label}-{'warm' if warm else 'cold'}"

    def _approve(scope, args):
        # Record an admission.approval span already wraps this in handle_computer_use.
        return None

    cu_tool._AUX_VISION_ROUTE_CACHE.clear()
    with patch.object(cu_tool, "_get_backend", return_value=b), \
         patch.object(cu_tool, "_reject_unsafe", return_value=None), \
         patch.object(cu_tool, "_request_approval", side_effect=_approve):
        # focus_app is destructive → approval path
        t0 = time.perf_counter()
        cu_tool.handle_computer_use(
            {"action": "focus_app", "app": "App", "raise_window": True},
            session_id=f"phase9-{tid}", cu_turn_id=tid, cu_warm=warm,
        )
        wall_ms = (time.perf_counter() - t0) * 1000.0
    tr = dict(getattr(cu_tool.handle_computer_use, "last_trace", {}) or {})
    tr["wall_ms"] = round(wall_ms, 3)
    return tr


def traj_run_goal_stub(warm: bool) -> Dict[str, Any]:
    """3 leaf actions under one outer cu_turn — stands in for run_goal until botscreen merge."""
    from tools.computer_use import cu_trace, tool as cu_tool
    b = _fake_backend()
    label = "run_goal_3step"
    tid = f"{label}-{'warm' if warm else 'cold'}"
    t0 = time.perf_counter()
    with cu_trace.cu_turn(turn_id=tid, warm=warm, trajectory=label) as tr:
        for i, (action, args) in enumerate([
            ("capture", {"mode": "ax"}),
            ("click", {"x": 5, "y": 5}),
            ("type", {"text": "ok"}),
        ], 1):
            with patch.object(cu_tool, "_get_backend", return_value=b), \
                 patch.object(cu_tool, "_reject_unsafe", return_value=None), \
                 patch.object(cu_tool, "_request_approval", return_value=None), \
                 patch.object(cu_tool, "_should_route_through_aux_vision", return_value=False):
                cu_tool.handle_computer_use(
                    {"action": action, **args},
                    session_id=f"phase9-{tid}",
                    cu_warm=warm or i > 1,
                )
        # Simulate local_jev decisions (no network)
        for _ in range(4):
            with cu_trace.span("decision.local_jev"):
                time.sleep(0.0005)
            cu_trace.record_model_call("local_jev", model="jev", model_call_reason="leaf_choice")
        out = tr.close(success=True)
    out["wall_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    return out


def traj_browser_stub(warm: bool) -> Dict[str, Any]:
    """Readiness/browser overhead placeholder — marks skipped_live unless CU_PERF_LIVE."""
    if os.environ.get("CU_PERF_LIVE") != "1":
        return {
            "turn_id": f"warm_browser-{'warm' if warm else 'cold'}",
            "warm": warm,
            "skipped": True,
            "skip_reason": "live browser trajectory requires CU_PERF_LIVE=1 + hypr isolation",
            "spans": [],
            "model_call_counts": {},
            "wall_ms": 0.0,
        }
    # Live path reserved for hypr-isolated runner.
    return traj_warm_click_type(warm)


def traj_mcp_recovery_stub(warm: bool) -> Dict[str, Any]:
    from tools.computer_use import cu_trace
    label = "mcp_child_recovery"
    tid = f"{label}-{'warm' if warm else 'cold'}"
    t0 = time.perf_counter()
    with cu_trace.cu_turn(turn_id=tid, warm=warm) as tr:
        with cu_trace.span("transport.mcp_wait"):
            time.sleep(0.001)
        with cu_trace.span("transport.reconnect"):
            time.sleep(0.002)
        with cu_trace.span("recovery.reconnect"):
            time.sleep(0.001)
        cu_trace.record_model_call("recovery", model_call_reason="mcp_child_stdio_dead")
        out = tr.close(success=True, simulated=True)
    out["wall_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    out["note"] = "simulated transport contamination spans; live MCP path not exercised"
    return out


TRAJECTORIES = [
    ("warm_click_type", traj_warm_click_type),
    ("changed_visual_native", lambda warm: traj_changed_visual(warm, native=True)),
    ("changed_visual_aux", lambda warm: traj_changed_visual(warm, native=False)),
    ("run_goal_3step", traj_run_goal_stub),
    ("approval_type", traj_approval_type),
    ("warm_browser", traj_browser_stub),
    ("mcp_child_recovery", traj_mcp_recovery_stub),
]


def _rank_spans(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    totals: Dict[str, float] = {}
    for row in rows:
        for name, ms in (row.get("span_totals_ms") or {}).items():
            totals[name] = totals.get(name, 0.0) + float(ms)
        # also accumulate from spans if totals missing
        if not row.get("span_totals_ms"):
            for s in row.get("spans") or []:
                totals[s["name"]] = totals.get(s["name"], 0.0) + float(s.get("duration_ms") or 0)
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    return [{"span": n, "total_ms": round(ms, 3)} for n, ms in ranked]


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    for name, fn in TRAJECTORIES:
        for warm in (False, True):
            try:
                row = fn(warm)
                row.setdefault("trajectory", name)
                row["ok"] = True
                rows.append(row)
                print(f"OK  {name} warm={warm} wall_ms={row.get('wall_ms')} "
                      f"models={row.get('model_call_counts')}")
            except Exception as exc:
                rows.append({
                    "trajectory": name, "warm": warm, "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "spans": [], "model_call_counts": {}, "wall_ms": 0.0,
                })
                print(f"ERR {name} warm={warm}: {exc}")

    jsonl = REPORT_DIR / "matrix.jsonl"
    with jsonl.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")

    ranked = _rank_spans(rows)
    summary = {
        "phase": 9,
        "rows": len(rows),
        "ok": sum(1 for r in rows if r.get("ok")),
        "model_call_totals": {},
        "ranked_spans": ranked,
        "attribution_note": (
            "Fake-backend matrix attributes CU tool spans. Live browser/MCP/"
            "run_goal need CU_PERF_LIVE + hypr isolation / botscreen merge."
        ),
    }
    for row in rows:
        for k, v in (row.get("model_call_counts") or {}).items():
            summary["model_call_totals"][k] = summary["model_call_totals"].get(k, 0) + int(v)

    (REPORT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    md = ["# Phase 9 matrix\n", f"Rows: {summary['rows']} ok={summary['ok']}\n",
          "## Model call totals\n",
          "```\n" + json.dumps(summary["model_call_totals"], indent=2) + "\n```\n",
          "## Spans ranked by total_ms\n",
          "| span | total_ms |\n| --- | ---: |\n"]
    for r in ranked[:25]:
        md.append(f"| `{r['span']}` | {r['total_ms']} |\n")
    (REPORT_DIR / "SUMMARY.md").write_text("".join(md))
    print(json.dumps(summary, indent=2))
    failed = sum(1 for r in rows if not r.get("ok"))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
