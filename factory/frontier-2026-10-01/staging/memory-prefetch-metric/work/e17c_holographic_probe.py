"""E17c: a real bundled provider (holographic, local SQLite) through the real turn-start prefetch path.

Usage: python e17c_holographic_probe.py --repo <tree at the staging commit> --out <json>
Isolated HOME/HERMES_HOME, loopback-only connect guard, synthetic facts only, no model inference.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True)
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--turns", type=int, default=20)
a = ap.parse_args()
sandbox = tempfile.mkdtemp(prefix="e17c-holo-", dir="$S")
os.environ.clear()
os.environ.update(HOME=sandbox, HERMES_HOME=sandbox + "/hermes", PATH="/usr/bin:/bin", TZ="UTC", LANG="C.UTF-8")
home = Path(os.environ["HERMES_HOME"])
home.mkdir()
(home / "config.yaml").write_text(
    "telemetry:\n  shared_metrics:\n    enabled: true\n    send: false\nmemory:\n  provider: holographic\n", encoding="utf-8")
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
from types import SimpleNamespace  # noqa: E402

from agent.memory_manager import MemoryManager  # noqa: E402
from agent.turn_context import _memory_turn_start_and_prefetch  # noqa: E402
from hermes_cli.observability import relay_shared_metrics  # noqa: E402
from hermes_cli.observability.shared_metrics import SharedMetricsStore  # noqa: E402
from plugins.memory import load_memory_provider  # noqa: E402

provider = load_memory_provider("holographic")
assert provider is not None and provider.is_available(), "holographic provider unavailable"
manager = MemoryManager()
manager.add_provider(provider)
manager.initialize_all(session_id="e17c", hermes_home=str(home), platform="cli")
for fact in ("The user prefers tabs over spaces in Python files.",
             "The user's telescope is a 10 inch Dobsonian.",
             "The user deploys with a blue-green rollout on Fridays."):
    provider.handle_tool_call("fact_store", {"action": "add", "content": fact})
queries = ["Do I prefer tabs or spaces in Python?", "What telescope do I own?",
           "What is the capital of Mongolia?", "Which bread flour do I buy?"]
agent = SimpleNamespace(_memory_manager=manager, session_id="e17c", _user_turn_count=0, _emit_status=lambda *_: None)
turns = []
for i in range(a.turns):
    agent._user_turn_count = i + 1
    q = queries[i % len(queries)]
    t0 = time.perf_counter()
    ctx = _memory_turn_start_and_prefetch(agent, q)
    turns.append({"query_index": i % len(queries), "context_nonempty": bool(ctx.strip()),
                  "wait_ms": round((time.perf_counter() - t0) * 1000, 3)})
relay_shared_metrics._reset_for_tests()
root = home / "telemetry" / "shared_metrics"
store = SharedMetricsStore(root / "metrics.sqlite3", root / "outbox")
rows = [{"dims": r["dimensions"], "value": r["value"]} for r in store.counter_snapshot()
        if r["metric_name"] == "hermes.memory.prefetch.count"]
nonempty = sum(t["context_nonempty"] for t in turns)
out = {
    "provider": "holographic (bundled, local SQLite)", "turns": a.turns, "rows": rows,
    "turns_with_context": nonempty, "turns_without_context": a.turns - nonempty,
    "row_outcome_counts": {o: sum(r["value"] for r in rows if r["dims"]["outcome"] == o) for o in ("success", "empty")},
    "rows_match_turns": sum(r["value"] for r in rows) == a.turns
    and sum(r["value"] for r in rows if r["dims"]["outcome"] == "success") == nonempty,
    "wait_ms_p50": sorted(t["wait_ms"] for t in turns)[len(turns) // 2],
    "wait_ms_max": max(t["wait_ms"] for t in turns),
    "egress_blocked_attempts": blocked,
}
a.out.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
