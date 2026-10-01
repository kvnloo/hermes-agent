"""E17d (round 3, amended head): attribute the per-call cost the staging commit adds to MemoryManager._prefetch_provider.

Round 3 changes: the no-op stand-in takes the amended signature (``recalled=`` keyword), and the standalone
record call passes a recalled string like the success exit does. Arms and contrasts are unchanged.

Round 1 (E17/r20261001-02) measured +47 us/call with collection off, of which the standalone
record_memory_prefetch call explained 26.7 us. This splits the delta in place, inside _prefetch_provider:

  base          main's agent/memory_manager.py (--base-mm), loaded from source into the head tree
  base_aa       the same base class again (A/A noise)
  head          the staging commit's MemoryManager
  head_noop     head, with shared_metrics_loop.record_memory_prefetch swapped for a no-op during the block
                (head - head_noop = what the record call costs in place)
  head_hoisted  head source with the function-level `from ... import record_memory_prefetch` moved to
                module level (head - head_hoisted = what the per-call import statement costs)

Plus the round-1 standalone cases (enabled() alone, record_memory_prefetch alone) in the same process.

Usage (fresh interpreter; isolates its own environment, loopback-only connect guard, no network):
  python micro_attribution.py --repo <tree at the staging commit> --base-mm <main memory_manager.py> \
      --sandbox-root <scratch dir> --out <json>
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True)
ap.add_argument("--base-mm", required=True)
ap.add_argument("--sandbox-root", required=True)
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--blocks", type=int, default=16)
ap.add_argument("--calls", type=int, default=400)
ap.add_argument("--standalone-calls", type=int, default=2000)
args = ap.parse_args()

REPO = str(Path(args.repo).resolve())
BASE_MM = str(Path(args.base_mm).resolve())
OUT = args.out.resolve()
sys.dont_write_bytecode = True
sandbox = tempfile.mkdtemp(prefix="e17d-", dir=args.sandbox_root)
os.environ.clear()
os.environ.update(HOME=sandbox, HERMES_HOME=sandbox + "/hermes", PATH="/usr/bin:/bin", PYTHONDONTWRITEBYTECODE="1",
                  HERMES_DISABLE_MODEL_METADATA_FETCH="1", TZ="UTC", LANG="C.UTF-8")
Path(os.environ["HERMES_HOME"]).mkdir()
HOMES = {}
for mode, flag in (("collection_off", "false"), ("collection_on", "true")):
    home = Path(sandbox) / mode
    home.mkdir()
    (home / "config.yaml").write_text(f"telemetry:\n  shared_metrics:\n    enabled: {flag}\n    send: false\n",
                                      encoding="utf-8")
    HOMES[mode] = home
os.chdir(sandbox)
sys.path.insert(0, REPO)

import socket  # noqa: E402

_connect = socket.socket.connect
blocked: list[str] = []


def loopback_only(self, address):
    if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
        blocked.append(str(address))
        raise RuntimeError("Probe blocks non-loopback network")
    return _connect(self, address)


socket.socket.connect = loopback_only

import logging  # noqa: E402

logging.basicConfig(level=logging.ERROR)

from agent import memory_manager as head_mm  # noqa: E402
from agent.memory_provider import MemoryProvider  # noqa: E402
from hermes_cli.observability import relay_shared_metrics  # noqa: E402
from hermes_cli.observability import shared_metrics_loop as loop  # noqa: E402
from hermes_constants import reset_hermes_home_override, set_hermes_home_override  # noqa: E402


def load_from_source(name: str, source: str, filename: str):
    spec = importlib.util.spec_from_loader(name, loader=None, origin=filename)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = filename
    exec(compile(source, filename, "exec"), module.__dict__)
    return module


base_mm = load_from_source("agent._memory_manager_base", Path(BASE_MM).read_text(encoding="utf-8"), BASE_MM)
IMPORT_LINE = "        from hermes_cli.observability.shared_metrics_loop import record_memory_prefetch\n"
head_src = Path(head_mm.__file__).read_text(encoding="utf-8")
assert head_src.count(IMPORT_LINE) == 1, "function-level import not found exactly once"
hoisted_src = head_src.replace(IMPORT_LINE, "").replace(
    "\nimport time\n", "\nimport time\n\nfrom hermes_cli.observability.shared_metrics_loop import record_memory_prefetch\n", 1)
assert hoisted_src.count("from hermes_cli.observability.shared_metrics_loop import record_memory_prefetch") == 1
hoisted_mm = load_from_source("agent._memory_manager_hoisted", hoisted_src, head_mm.__file__ + "#hoisted")

CLASSES = {"base": base_mm.MemoryManager, "base_aa": base_mm.MemoryManager, "head": head_mm.MemoryManager,
           "head_noop": head_mm.MemoryManager, "head_hoisted": hoisted_mm.MemoryManager}
ARMS = list(CLASSES)
REAL_RECORD = loop.record_memory_prefetch


def _noop_record(provider, outcome, started, *, recalled=None):
    return None


class InstantProvider(MemoryProvider):
    @property
    def name(self):
        return "fixture-instant-memory"

    def is_available(self):
        return True

    def initialize(self, session_id, **kwargs):
        pass

    def get_tool_schemas(self):
        return []

    def prefetch(self, query, *, session_id=""):
        return "- fixture recalled fact"


def micro(arm: str, home: Path, calls: int) -> float:
    token = set_hermes_home_override(home)
    if arm == "head_noop":
        loop.record_memory_prefetch = _noop_record
    try:
        manager = CLASSES[arm](external_prefetch_timeout=1.0)
        provider = InstantProvider()
        manager.add_provider(provider)
        manager._prefetch_provider(provider, "warm")
        t0 = time.perf_counter_ns()
        for _ in range(calls):
            manager._prefetch_provider(provider, "what do I prefer?")
        return (time.perf_counter_ns() - t0) / calls / 1000
    finally:
        loop.record_memory_prefetch = REAL_RECORD
        reset_hermes_home_override(token)


def per_call_us(fn, calls: int) -> float:
    t0 = time.perf_counter_ns()
    for _ in range(calls):
        fn()
    return (time.perf_counter_ns() - t0) / calls / 1000


def pct(values, q):
    values = sorted(values)
    k = (len(values) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def summarize(values):
    return {"median": round(statistics.median(values), 2), "p05": round(pct(values, 0.05), 2),
            "p95": round(pct(values, 0.95), 2)}


STANDALONE = {
    "enabled_gate_only": relay_shared_metrics.enabled,
    "record_memory_prefetch": lambda: REAL_RECORD("honcho", "success", time.monotonic(), recalled="- fixture recalled fact"),
    "record_execution_backend_existing": lambda: loop.record_execution_backend("terminal", "local", '{"exit_code": 0}'),
}
CONTRASTS = {
    "head_minus_base": ("head", "base"),
    "head_noop_minus_base": ("head_noop", "base"),
    "head_hoisted_minus_base": ("head_hoisted", "base"),
    "head_minus_head_noop": ("head", "head_noop"),
    "head_minus_head_hoisted": ("head", "head_hoisted"),
    "aa_base_aa_minus_base": ("base_aa", "base"),
}
out: dict = {"schema": "e17d.micro_attribution.v1", "round": 3, "python": sys.version.split()[0], "blocks": args.blocks,
             "calls_per_block": args.calls, "load1_start": os.getloadavg()[0], "modes": {}}
for mode, home in HOMES.items():
    blocks = {arm: [] for arm in ARMS}
    for b in range(args.blocks):
        order = ARMS[b % len(ARMS):] + ARMS[:b % len(ARMS)]
        if b % 2:
            order = list(reversed(order))
        for arm in order:
            blocks[arm].append(micro(arm, home, args.calls))
    contrasts = {name: summarize([x - y for x, y in zip(blocks[a], blocks[c])]) for name, (a, c) in CONTRASTS.items()}
    token = set_hermes_home_override(home)
    try:
        for fn in STANDALONE.values():
            fn()
        standalone = {k: [] for k in STANDALONE}
        names = list(STANDALONE)
        for b in range(args.blocks):
            for name in (names if b % 2 == 0 else list(reversed(names))):
                standalone[name].append(per_call_us(STANDALONE[name], args.standalone_calls))
    finally:
        reset_hermes_home_override(token)
    out["modes"][mode] = {
        "us_per_call_median": {arm: round(statistics.median(v), 2) for arm, v in blocks.items()},
        "contrasts_us": contrasts,
        "standalone_us_median": {k: round(statistics.median(v), 2) for k, v in standalone.items()},
    }
relay_shared_metrics._reset_for_tests()
out["egress_blocked_attempts"] = blocked
out["load1_end"] = os.getloadavg()[0]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
