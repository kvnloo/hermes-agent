"""E17 / F-micro: external memory prefetch fault probe (T1, $0, loopback only, no model inference).

Usage (fresh interpreter; the script isolates its own environment):
  python e17_prefetch_fault_probe.py --repo <hermes tree at the staging commit> --base-mm <main agent/memory_manager.py> \
      --out <receipt-data.json>

What it drives: the real turn-start path agent.turn_context._memory_turn_start_and_prefetch ->
MemoryManager.prefetch_all -> _prefetch_provider, with a MemoryProvider subclass whose prefetch() is a
plain HTTP GET against a loopback fake memory backend that injects faults (delay, slow-over-timeout,
hang, empty, HTTP 500, connection refused). Shared metrics run on the REAL NeMo Relay binding and the
real SharedMetricsStore in an isolated HERMES_HOME whose config.yaml turns collection on (send: false).

Arms: "head" = MemoryManager from --repo (the staging commit); "base" = main's agent/memory_manager.py
(--base-mm) loaded from source into the same tree. memory_manager.py is the only changed file on the
prefetch call path; the contract/loop/schema additions are inert without its record calls.

Pattern lifted from evals/memory/honcho_current_query.py (loopback fixture backend) and
evals/provider_fallback/probe_104260.py:11-39 (os.environ isolation + loopback-only connect guard).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True)
ap.add_argument("--base-mm", required=True)
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--reps", type=int, default=12)
ap.add_argument("--micro-blocks", type=int, default=12)
ap.add_argument("--micro-calls", type=int, default=400)
ap.add_argument("--skip-default-timeout", action="store_true")
args = ap.parse_args()

REPO = str(Path(args.repo).resolve())
sys.dont_write_bytecode = True
sandbox = tempfile.mkdtemp(prefix="e17-prefetch-", dir="$S")
os.environ.clear()
os.environ.update(
    HOME=sandbox, HERMES_HOME=sandbox + "/hermes", PATH="/usr/bin:/bin", PYTHONDONTWRITEBYTECODE="1",
    HERMES_DISABLE_MODEL_METADATA_FETCH="1", TZ="UTC", LANG="C.UTF-8",
)
HOMES = {name: Path(sandbox) / name for name in ("hermes", "profile_b", "profile_off")}
for name, home in HOMES.items():
    home.mkdir()
    enabled = "false" if name == "profile_off" else "true"
    (home / "config.yaml").write_text(
        f"telemetry:\n  shared_metrics:\n    enabled: {enabled}\n    send: false\n", encoding="utf-8")
os.chdir(sandbox)
sys.path.insert(0, REPO)

import socket  # noqa: E402

_original_connect = socket.socket.connect
blocked: list[str] = []


def loopback_only(self, address):
    if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
        blocked.append(str(address))
        raise RuntimeError("Probe blocks non-loopback network")
    return _original_connect(self, address)


socket.socket.connect = loopback_only

import logging  # noqa: E402
import urllib.error  # noqa: E402
import urllib.request  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402
from types import SimpleNamespace  # noqa: E402

logging.basicConfig(level=logging.ERROR)

release = threading.Event()
backend_calls: list[str] = []


class Backend(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        fault = self.path.strip("/").split("?")[0]
        backend_calls.append(fault)
        status, body = 200, "- fixture recalled fact"
        if fault.startswith("delay_"):
            time.sleep(float(fault.split("_", 1)[1]))
        elif fault == "hang":
            release.wait(30)
        elif fault == "empty":
            body = ""
        elif fault == "error":
            status, body = 500, "fixture failure"
        raw = body.encode()
        try:
            self.send_response(status)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except OSError:
            pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
threading.Thread(target=server.serve_forever, daemon=True).start()
closed = socket.socket()
closed.bind(("127.0.0.1", 0))
CLOSED_PORT = closed.getsockname()[1]
closed.close()  # nothing listens here: connection refused

from agent.memory_provider import MemoryProvider  # noqa: E402
from agent import memory_manager as head_mm  # noqa: E402
from agent.turn_context import _memory_turn_start_and_prefetch  # noqa: E402
from hermes_cli.observability import relay_shared_metrics  # noqa: E402
from hermes_cli.observability.shared_metrics import SharedMetricsStore  # noqa: E402
from hermes_constants import reset_hermes_home_override, set_hermes_home_override  # noqa: E402

spec = importlib.util.spec_from_file_location("agent._memory_manager_base", args.base_mm)
base_mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_mm)
ARMS = {"base": base_mm.MemoryManager, "head": head_mm.MemoryManager}


class FixtureHttpProvider(MemoryProvider):
    """A plugin-shaped provider (not bundled, so it reports as ``plugin``) backed by the fake server."""

    def __init__(self):
        self.fault = "ok"

    @property
    def name(self):
        return "fixture-http-memory"

    def is_available(self):
        return True

    def initialize(self, session_id, **kwargs):
        pass

    def get_tool_schemas(self):
        return []

    def prefetch(self, query, *, session_id=""):
        port = CLOSED_PORT if self.fault == "refused" else server.server_port
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/{self.fault}", timeout=60) as resp:
            return resp.read().decode()


class InstantProvider(FixtureHttpProvider):
    def prefetch(self, query, *, session_id=""):
        return "- fixture recalled fact"


def store_rows(home: Path, metric="hermes.memory.prefetch.count"):
    relay_shared_metrics._reset_for_tests()  # drain the Relay subscriber into the store (as the tests do)
    root = home / "telemetry" / "shared_metrics"
    if not (root / "metrics.sqlite3").exists():
        return []
    store = SharedMetricsStore(root / "metrics.sqlite3", root / "outbox")
    return [(row["dimensions"], row["value"]) for row in store.counter_snapshot() if row["metric_name"] == metric]


def wipe_store(home: Path):
    relay_shared_metrics._reset_for_tests()
    root = home / "telemetry" / "shared_metrics"
    if root.exists():
        for p in sorted(root.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()


def settle(manager):
    for t in list(manager._external_prefetch_threads.values()):
        t.join(35)


def turn(manager, provider, fault, turn_no):
    provider.fault = fault
    agent = SimpleNamespace(_memory_manager=manager, session_id="e17", _user_turn_count=turn_no,
                            _emit_status=lambda *_: None)
    t0 = time.perf_counter()
    context = _memory_turn_start_and_prefetch(agent, f"what do I prefer? ({fault})")
    return context, (time.perf_counter() - t0) * 1000


def pct(values, q):
    values = sorted(values)
    if not values:
        return None
    k = (len(values) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


EXPECTED = {
    "ok": "success", "delay_0.05": "success", "delay_0.4": "success", "slow_over_timeout": "timed_out",
    "empty": "empty", "error": "failed", "refused": "failed",
}
FAULT_PATH = {"slow_over_timeout": "delay_1.5"}
TIMEOUT_S = 1.0
result: dict = {
    "schema": "e17.prefetch_fault_probe.v1", "repo": REPO, "base_mm": args.base_mm, "python": sys.version.split()[0],
    "relay_native": None, "timeout_s": TIMEOUT_S, "reps": args.reps, "faults": {}, "checks": {},
}
import nemo_relay  # noqa: E402

result["relay_native"] = getattr(nemo_relay, "_native", None) is not None
default_home = HOMES["hermes"]

# ---- per-fault outcome + turn-blocking latency, base vs head interleaved (ABBA) -------------------
for fault, expected in EXPECTED.items():
    per_arm = {"base": [], "head": []}
    contexts = {"base": set(), "head": set()}
    rows_by_arm = {}
    for arm_order_rep in range(args.reps):
        order = ("base", "head") if arm_order_rep % 2 == 0 else ("head", "base")
        for arm in order:
            manager = ARMS[arm](external_prefetch_timeout=TIMEOUT_S)
            provider = FixtureHttpProvider()
            manager.add_provider(provider)
            ctx, ms = turn(manager, provider, FAULT_PATH.get(fault, fault), arm_order_rep + 1)
            settle(manager)
            per_arm[arm].append(ms)
            contexts[arm].add(ctx)
    # rows: run the head arm alone into a clean store to attribute rows per fault exactly
    wipe_store(default_home)
    for rep in range(args.reps):
        manager = ARMS["head"](external_prefetch_timeout=TIMEOUT_S)
        provider = FixtureHttpProvider()
        manager.add_provider(provider)
        turn(manager, provider, FAULT_PATH.get(fault, fault), rep + 1)
        settle(manager)
    head_rows = store_rows(default_home)
    wipe_store(default_home)
    for rep in range(args.reps):
        manager = ARMS["base"](external_prefetch_timeout=TIMEOUT_S)
        provider = FixtureHttpProvider()
        manager.add_provider(provider)
        turn(manager, provider, FAULT_PATH.get(fault, fault), rep + 1)
        settle(manager)
    base_rows = store_rows(default_home)
    wipe_store(default_home)
    result["faults"][fault] = {
        "backend_path": FAULT_PATH.get(fault, fault), "expected_outcome": expected,
        "turn_wait_ms": {arm: {"n": len(v), "p50": round(pct(v, 0.5), 2), "p95": round(pct(v, 0.95), 2),
                               "max": round(max(v), 2)} for arm, v in per_arm.items()},
        "returned_context_identical_across_arms": contexts["base"] == contexts["head"],
        "returned_context": sorted(contexts["head"]),
        "head_rows": [{"dims": d, "value": v} for d, v in head_rows],
        "base_rows": [{"dims": d, "value": v} for d, v in base_rows],
        "head_rows_total": sum(v for _, v in head_rows),
        "head_outcomes": sorted({d["outcome"] for d, _ in head_rows}),
    }

# ---- hang: first turn times out, later turns are skipped while the call is stuck ---------------
wipe_store(default_home)
manager = ARMS["head"](external_prefetch_timeout=TIMEOUT_S)
provider = FixtureHttpProvider()
manager.add_provider(provider)
release.clear()
hang_waits = [turn(manager, provider, "hang", i + 1)[1] for i in range(4)]
calls_while_hung = backend_calls.count("hang")
release.set()
settle(manager)
after_ctx, after_ms = turn(manager, provider, "ok", 5)
settle(manager)
hang_rows = store_rows(default_home)
result["faults"]["hang"] = {
    "expected_outcomes": ["timed_out", "skipped", "skipped", "skipped", "success(after release)"],
    "turn_wait_ms": [round(x, 2) for x in hang_waits], "after_release_ms": round(after_ms, 2),
    "backend_calls_while_hung": calls_while_hung,
    "head_rows": [{"dims": d, "value": v} for d, v in hang_rows],
}
wipe_store(default_home)

# ---- the shipped 8.0 s default: one hung turn ------------------------------------------------------
if not args.skip_default_timeout:
    manager = ARMS["head"]()
    provider = FixtureHttpProvider()
    manager.add_provider(provider)
    release.clear()
    _, default_wait = turn(manager, provider, "hang", 1)
    release.set()
    settle(manager)
    result["faults"]["hang_default_timeout"] = {
        "timeout_s": head_mm._EXTERNAL_PREFETCH_TIMEOUT_S, "turn_wait_ms": round(default_wait, 2),
        "head_rows": [{"dims": d, "value": v} for d, v in store_rows(default_home)],
    }
    wipe_store(default_home)

# ---- profile scope: the row lands in the profile that owns the turn ------------------------------
token = set_hermes_home_override(HOMES["profile_b"])
try:
    manager = ARMS["head"](external_prefetch_timeout=TIMEOUT_S)
    provider = InstantProvider()
    manager.add_provider(provider)
    turn(manager, provider, "ok", 1)
    settle(manager)
    rows_b = store_rows(HOMES["profile_b"])
finally:
    reset_hermes_home_override(token)
rows_default = store_rows(default_home)
result["checks"]["profile_scope"] = {
    "rows_in_owner_profile": sum(v for _, v in rows_b), "rows_in_default_home": sum(v for _, v in rows_default),
    "pass": sum(v for _, v in rows_b) == 1 and not rows_default,
}

# ---- collection off: nothing recorded -------------------------------------------------------------
token = set_hermes_home_override(HOMES["profile_off"])
try:
    manager = ARMS["head"](external_prefetch_timeout=TIMEOUT_S)
    provider = FixtureHttpProvider()
    manager.add_provider(provider)
    for i, fault in enumerate(("ok", "empty", "error", "delay_1.5")):
        turn(manager, provider, fault, i + 1)
        settle(manager)
    off_rows = store_rows(HOMES["profile_off"])
    off_store_exists = (HOMES["profile_off"] / "telemetry" / "shared_metrics" / "metrics.sqlite3").exists()
finally:
    reset_hermes_home_override(token)
result["checks"]["collection_off"] = {"rows": len(off_rows), "store_created": off_store_exists,
                                      "pass": not off_rows}


# ---- microbenchmark: per-call _prefetch_provider cost, base vs head, ABBA, collection on/off ------
def micro(arm, home, calls):
    token = set_hermes_home_override(home)
    try:
        manager = ARMS[arm](external_prefetch_timeout=TIMEOUT_S)
        provider = InstantProvider()
        manager.add_provider(provider)
        manager._prefetch_provider(provider, "warm")
        t0 = time.perf_counter_ns()
        for _ in range(calls):
            manager._prefetch_provider(provider, "what do I prefer?")
        return (time.perf_counter_ns() - t0) / calls / 1000  # us per call
    finally:
        reset_hermes_home_override(token)


micro_out = {}
for mode, home in (("collection_off", HOMES["profile_off"]), ("collection_on", HOMES["profile_b"])):
    blocks = {"base": [], "head": [], "base_aa": []}
    for b in range(args.micro_blocks):
        order = ("base", "head", "base_aa") if b % 2 == 0 else ("base_aa", "head", "base")
        for arm in order:
            blocks[arm].append(micro("base" if arm == "base_aa" else arm, home, args.micro_calls))
    deltas = [h - b for h, b in zip(blocks["head"], blocks["base"])]
    aa = [a - b for a, b in zip(blocks["base_aa"], blocks["base"])]
    micro_out[mode] = {
        "us_per_call_median": {k: round(statistics.median(v), 2) for k, v in blocks.items()},
        "us_per_call_p95": {k: round(pct(v, 0.95), 2) for k, v in blocks.items()},
        "delta_head_minus_base_us": {"median": round(statistics.median(deltas), 2), "p05": round(pct(deltas, 0.05), 2),
                                     "p95": round(pct(deltas, 0.95), 2)},
        "aa_base_minus_base_us": {"median": round(statistics.median(aa), 2), "p05": round(pct(aa, 0.05), 2),
                                  "p95": round(pct(aa, 0.95), 2)},
        "blocks": args.micro_blocks, "calls_per_block": args.micro_calls, "order": "ABA/ABA alternating",
    }
result["microbenchmark"] = micro_out
result["checks"]["egress_blocked_attempts"] = blocked
result["checks"]["outcome_classes_match_expected"] = {
    f: r["head_outcomes"] == [r["expected_outcome"]] for f, r in result["faults"].items() if "expected_outcome" in r
}
result["checks"]["one_row_per_turn_head"] = {
    f: r["head_rows_total"] == args.reps for f, r in result["faults"].items() if "head_rows_total" in r
}
result["checks"]["base_records_nothing"] = all(
    not r["base_rows"] for r in result["faults"].values() if "base_rows" in r)
result["checks"]["returned_context_identical_across_arms"] = all(
    r["returned_context_identical_across_arms"] for r in result["faults"].values()
    if "returned_context_identical_across_arms" in r)
result["load1_end"] = os.getloadavg()[0]
args.out.parent.mkdir(parents=True, exist_ok=True)
args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"checks": result["checks"], "micro": result["microbenchmark"]}, indent=2))
server.shutdown()
