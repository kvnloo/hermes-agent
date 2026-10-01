"""Attribute the per-call cost of record_memory_prefetch: the shared enabled() gate vs the new code.

Usage: python micro_gate_cost.py --repo <tree> --out <json>   (isolated env, loopback guard, no network)
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True)
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--blocks", type=int, default=15)
ap.add_argument("--calls", type=int, default=2000)
a = ap.parse_args()
sandbox = tempfile.mkdtemp(prefix="e17-gate-", dir="$S")
os.environ.clear()
os.environ.update(HOME=sandbox, HERMES_HOME=sandbox + "/hermes", PATH="/usr/bin:/bin", TZ="UTC", LANG="C.UTF-8")
homes = {}
for mode, flag in (("off", "false"), ("on", "true")):
    home = Path(sandbox) / mode
    home.mkdir()
    (home / "config.yaml").write_text(f"telemetry:\n  shared_metrics:\n    enabled: {flag}\n    send: false\n", encoding="utf-8")
    homes[mode] = home
Path(os.environ["HERMES_HOME"]).mkdir()
sys.path.insert(0, str(Path(a.repo).resolve()))
import socket  # noqa: E402

_connect = socket.socket.connect
blocked = []


def loopback_only(self, address):
    if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
        blocked.append(str(address))
        raise RuntimeError("blocked")
    return _connect(self, address)


socket.socket.connect = loopback_only

from hermes_cli.observability import relay_shared_metrics, shared_metrics_loop as loop  # noqa: E402
from hermes_constants import reset_hermes_home_override, set_hermes_home_override  # noqa: E402


def per_call_us(fn, calls):
    t0 = time.perf_counter_ns()
    for _ in range(calls):
        fn()
    return (time.perf_counter_ns() - t0) / calls / 1000


CASES = {
    "noop_baseline": lambda: None,
    "enabled_gate_only": relay_shared_metrics.enabled,
    "record_memory_prefetch": lambda: loop.record_memory_prefetch("honcho", "success", time.monotonic()),
    "record_execution_backend_existing": lambda: loop.record_execution_backend("terminal", "local", '{"exit_code": 0}'),
    "record_provider_memory_call_existing": lambda: loop.record_provider_memory_call("honcho", "honcho_search", {}, "{}"),
}
out = {"blocks": a.blocks, "calls_per_block": a.calls, "load1_start": os.getloadavg()[0], "modes": {}}
for mode, home in homes.items():
    token = set_hermes_home_override(home)
    try:
        for fn in CASES.values():
            fn()  # warm (creates the runtime when on)
        samples = {k: [] for k in CASES}
        names = list(CASES)
        for b in range(a.blocks):
            for name in (names if b % 2 == 0 else list(reversed(names))):
                samples[name].append(per_call_us(CASES[name], a.calls))
        out["modes"][mode] = {k: {"median_us": round(statistics.median(v), 2),
                                  "p95_us": round(sorted(v)[int(0.95 * (len(v) - 1))], 2)} for k, v in samples.items()}
    finally:
        reset_hermes_home_override(token)
relay_shared_metrics._reset_for_tests()
out["egress_blocked_attempts"] = blocked
out["load1_end"] = os.getloadavg()[0]
a.out.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
