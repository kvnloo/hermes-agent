"""Scratch T1 probe (NOT part of the upstream commit): submit -> first visible delta per surface.

One process life per surface (tui_gateway stdio, api_server /v1/runs + SSE events, ACP stdio) against the
loopback FakeLLMServer streaming each answer with ``delay_per_chunk``. Per rep, all on one host clock:

  t_submit       client sends the turn
  t_arrival      the fake provider receives the turn's main request (record["t"])
  t_first_delta  the client receives the first answer delta (stamped on arrival by the reader thread)
  t_complete     the client sees the turn complete

Reports pre_api_ms = arrival - submit, first_delta_ms = first_delta - submit and
delivery_ms = first_delta - (arrival + delay), median / p95 / n per surface. The first ``--warmup``
turns of each life are recorded but excluded. Run from the worktree root inside harness/sandbox.sh.
The quiet-lane rule applies to real measurements: load1 < 4, nothing else running, ABBA order, A/A first.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import statistics
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, os.getcwd())

from tests.e2e.core.history._helpers import (  # noqa: E402
    NO_BACKGROUND_REVIEW, OFFLINE_CONFIG, AcpStdio, ApiServerRuns, Spawned, TuiGateway, child_env,
)
from tests.fakes.fake_llm_provider import FakeLLMServer, Text, write_hermes_home  # noqa: E402


class TimedTuiGateway(TuiGateway):
    """TuiGateway whose reader stamps every event with its arrival time (``_t``)."""

    def _read_stdout(self) -> None:
        for raw in self.proc.stdout:
            line = raw.strip()
            if not line:
                continue
            try:
                frame = json.loads(line)
            except json.JSONDecodeError:
                continue
            if frame.get("method") == "event":
                with self._cond:
                    self.events.append({**(frame.get("params") or {}), "_t": time.time()})
                    self._cond.notify_all()
            elif "method" in frame and "id" in frame:
                self._write({"jsonrpc": "2.0", "id": frame["id"], "error": {"code": -32601, "message": "declined"}})
            elif "id" in frame and frame["id"] in self._pending:
                self._pending[frame["id"]].put(frame)
        with self._cond:
            self._cond.notify_all()


def pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return round(s[min(len(s) - 1, int(round(q * (len(s) - 1))))], 1)


def summarize(rows: list[dict], key: str) -> dict:
    vals = [r[key] for r in rows if r.get(key) is not None]
    return {"median": round(statistics.median(vals), 1) if vals else None, "p95": pct(vals, 0.95), "n": len(vals)}


def arrival_after(srv: FakeLLMServer, seen: int) -> float | None:
    mains = [r for r in srv.requests if r["kind"] == "main"]
    return mains[seen]["t"] if len(mains) > seen else None


def run_gw(env, cwd, home, srv, spawned, reps):
    rows = []
    with TimedTuiGateway(env, cwd, spawned) as gw:
        live = gw.create()
        for n in range(reps):
            seen = len(srv.main_requests())
            start = gw.mark()
            t_submit = time.time()
            gw.call("prompt.submit", {"session_id": live, "text": f"e09 gw turn {n}"})
            delta = gw.wait_event("message.delta", live, start=start)
            done = gw.wait_event("message.complete", live, start=start)
            rows.append({"t_submit": t_submit, "t_arrival": arrival_after(srv, seen),
                         "t_first_delta": delta["_t"], "t_complete": done["_t"]})
    return rows


def run_api(env, cwd, home, srv, spawned, reps):
    rows = []
    sid = "e09-api"
    with ApiServerRuns(env, cwd, home, spawned) as api:
        for n in range(reps):
            seen = len(srv.main_requests())
            t_submit = time.time()
            req = urllib.request.Request(f"{api.base}/v1/runs", method="POST",
                                         data=json.dumps({"input": f"e09 api turn {n}", "session_id": sid}).encode())
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {api.key}")
            with urllib.request.urlopen(req, timeout=30) as resp:
                run_id = json.loads(resp.read())["run_id"]
            ev_req = urllib.request.Request(f"{api.base}/v1/runs/{run_id}/events")
            ev_req.add_header("Authorization", f"Bearer {api.key}")
            t_fd = t_done = server_fd = None
            with urllib.request.urlopen(ev_req, timeout=120) as stream:
                for raw in stream:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    now = time.time()
                    ev = json.loads(line[5:].strip() or "{}")
                    if ev.get("event") == "message.delta" and t_fd is None:
                        t_fd, server_fd = now, ev.get("timestamp")
                    if ev.get("event") in ("run.completed", "run.failed", "run.cancelled", "run.interrupted"):
                        t_done = now
                        break
            rows.append({"t_submit": t_submit, "t_arrival": arrival_after(srv, seen), "t_first_delta": t_fd,
                         "t_complete": t_done, "server_first_delta": server_fd})
    return rows


def run_acp(env, cwd, home, srv, spawned, reps):
    rows = []
    with AcpStdio(env, cwd, home, spawned) as acp:
        sid = acp.open(None)
        client = acp.client
        for n in range(reps):
            seen = len(srv.main_requests())
            client._next_id += 1
            rid = client._next_id
            t_submit = time.time()
            client._send({"jsonrpc": "2.0", "id": rid, "method": "session/prompt",
                          "params": {"sessionId": sid, "prompt": [{"type": "text", "text": f"e09 acp turn {n}"}]}})
            t_fd = t_done = None
            deadline = time.monotonic() + 120
            while t_done is None and time.monotonic() < deadline:
                try:
                    msg = client._inbox.get(timeout=1)
                except queue.Empty:
                    continue
                now = time.time()
                if msg is None:
                    raise AssertionError("acp closed stdout")
                if "method" in msg:
                    upd = (msg.get("params") or {}).get("update") or {}
                    if t_fd is None and upd.get("sessionUpdate") == "agent_message_chunk":
                        t_fd = now
                    client._handle_incoming(msg)
                elif msg.get("id") == rid:
                    t_done = now
            rows.append({"t_submit": t_submit, "t_arrival": arrival_after(srv, seen), "t_first_delta": t_fd,
                         "t_complete": t_done})
    return rows


DRIVERS = {"gw": run_gw, "api": run_api, "acp": run_acp}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--surfaces", default="gw,api,acp")
    ap.add_argument("--reps", type=int, default=30)
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--delay", type=float, default=0.05)
    ap.add_argument("--order", default="AB", help="AB, or ABBA to run the surface list forward then reversed")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    surfaces = args.surfaces.split(",")
    sequence = surfaces + (surfaces[::-1] if args.order == "ABBA" else [])
    root = Path(tempfile.mkdtemp(prefix="e09-", dir=os.environ.get("PROBE_TMP") or None))
    out = {"label": args.label, "delay_s": args.delay, "reps": args.reps, "warmup": args.warmup,
           "order": sequence, "load1_start": os.getloadavg()[0], "runs": []}
    for k, surface in enumerate(sequence):
        d = root / f"{k}-{surface}"
        home, hermes_home, cwd = d / "home", d / "hermes_home", d / "work"
        for p in (home, hermes_home, cwd):
            p.mkdir(parents=True)
        spawned = Spawned()
        responder = lambda _rec: Text("e09 answer " + "lorem ipsum " * 40, chunk_chars=16,  # noqa: E731
                                      delay_per_chunk=args.delay, prompt_tokens=2000, completion_tokens=40,
                                      cached_tokens=1500)
        with FakeLLMServer(responder) as srv:
            write_hermes_home(hermes_home, srv.base_url, extra_config=OFFLINE_CONFIG + NO_BACKGROUND_REVIEW)
            env = child_env(home, hermes_home, cwd)
            t0 = time.monotonic()
            try:
                rows = DRIVERS[surface](env, cwd, hermes_home, srv, spawned, args.reps + args.warmup)
                err = None
            except Exception as exc:  # noqa: BLE001
                rows, err = [], f"{type(exc).__name__}: {str(exc)[:500]}"
            finally:
                leaked = spawned.reap()
        for r in rows:
            if r.get("t_arrival") and r.get("t_first_delta"):
                r["pre_api_ms"] = 1000 * (r["t_arrival"] - r["t_submit"])
                r["first_delta_ms"] = 1000 * (r["t_first_delta"] - r["t_submit"])
                r["delivery_ms"] = 1000 * (r["t_first_delta"] - (r["t_arrival"] + args.delay))
                r["complete_ms"] = 1000 * (r["t_complete"] - r["t_submit"]) if r.get("t_complete") else None
        timed = rows[args.warmup:]
        out["runs"].append({
            "surface": surface, "position": k, "error": err, "leaked": leaked,
            "life_wall_s": round(time.monotonic() - t0, 1),
            "warmup_rows": rows[:args.warmup], "rows": timed,
            "pre_api_ms": summarize(timed, "pre_api_ms"), "first_delta_ms": summarize(timed, "first_delta_ms"),
            "delivery_ms": summarize(timed, "delivery_ms"), "complete_ms": summarize(timed, "complete_ms"),
        })
        print(json.dumps({"surface": surface, "error": err, "first_delta_ms": out["runs"][-1]["first_delta_ms"],
                          "pre_api_ms": out["runs"][-1]["pre_api_ms"]}), flush=True)
    out["load1_end"] = os.getloadavg()[0]
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
