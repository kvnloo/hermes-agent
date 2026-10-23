"""Track 1 spike bench: deterministic gate (baseline) vs NanoJev (spike).

Runs under the z0int venv python (it imports z0int for the baseline gate and
agent.nanojev_shadow for the spike)::

    Z0INT_PYTHON=<venv>/bin/python <venv>/bin/python lab/track1/bench_nanojev.py

For each turn in turns.jsonl:
  BASELINE (red): z0int deterministic_gate over a DecisionOpportunity built
      with an empty state packet (the current #55 falsification baseline).
  SPIKE (green): NanoJev answers the ACT/ASK/ESCALATE choice via
      agent/nanojev_shadow.py (shadow mode, child subprocess).

Metrics: N/N decisions produced, gate-vs-label and nanojev-vs-label
agreement, gate-vs-nanojev agreement, per-turn latency. Writes
lab/track1/bench_results.json and prints a table.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# z0int source for the baseline gate (not installed in this interpreter).
_z0int_src = Path(os.environ.get("Z0INT_SRC") or (REPO_ROOT.parent / "z0int" / "src"))
if _z0int_src.is_dir():
    sys.path.insert(0, str(_z0int_src))

from agent import nanojev_shadow as ns  # noqa: E402


def load_turns(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def baseline_gate(text: str) -> str:
    """z0int deterministic gate over an empty-packet opportunity."""
    from z0int.decision_opportunity import build_decision_opportunity, deterministic_gate

    opp = build_decision_opportunity(".", text, harness="hermes", packet={})
    return deterministic_gate(opp)


def main() -> int:
    lab = Path(__file__).resolve().parent
    turns = load_turns(lab / "turns.jsonl")
    os.environ.setdefault("Z0INT_PYTHON", sys.executable)
    os.environ["NANOJEV_SHADOW_DIR"] = str(lab / "shadow_records")
    # The z0int child needs the z0int source tree (not pip-installed here).
    if _z0int_src.is_dir():
        os.environ["PYTHONPATH"] = str(_z0int_src) + os.pathsep + os.environ.get("PYTHONPATH", "")

    print(f"turns: {len(turns)}  z0int_python: {os.environ['Z0INT_PYTHON']}")
    print(f"{'id':<16}{'expected':<24}{'gate':<10}{'nanojev':<10}{'lat_ms':>8}  note")
    print("-" * 100)

    rows = []
    for t in turns:
        tid, platform, msg, expected = t["id"], t["platform"], t["user_message"], t["expected"]
        t0 = time.perf_counter()
        excluded, text = ns.classify_turn(msg, platform)
        if excluded is not None:
            got, nanojev, lat = f"excluded:{excluded}", "-", 0.0
            gate = f"excluded:{excluded}"
        else:
            try:
                gate = baseline_gate(text or "")
            except Exception as exc:  # noqa: BLE001
                gate = f"gate_error:{type(exc).__name__}"
            rec = ns.shadow_turn(
                msg, turn_id=tid, platform=platform, record=True,
            )
            nanojev = rec.get("nanojev_choice") or f"error:{rec.get('nanojev_error', '?')[:40]}"
            lat = rec.get("nanojev_latency_ms") or 0.0
            got = nanojev
        wall = (time.perf_counter() - t0) * 1000.0
        rows.append(
            {
                "id": tid, "expected": expected, "gate": gate, "nanojev": nanojev,
                "nanojev_latency_ms": round(lat, 1), "wall_ms": round(wall, 1),
                "gate_match": gate == expected, "nanojev_match": got == expected,
            }
        )
        print(f"{tid:<16}{expected:<24}{str(gate):<10}{str(nanojev):<10}{lat:>8.0f}  {t.get('note', '')}")

    evaluable = [r for r in rows if not r["expected"].startswith("excluded")]
    n = len(evaluable)
    gate_agree = sum(1 for r in evaluable if r["gate_match"])
    nj_agree = sum(1 for r in evaluable if r["nanojev_match"])
    nj_nj = [r for r in evaluable if isinstance(r["nanojev"], str) and r["nanojev"] in ("ACT", "ASK", "ESCALATE")]
    lats = sorted(r["nanojev_latency_ms"] for r in nj_nj)

    def pct(q):
        return lats[min(len(lats) - 1, int(q * len(lats)))] if lats else None

    summary = {
        "turns": len(turns),
        "evaluable": n,
        "nanojev_decisions_produced": f"{len(nj_nj)}/{n}",
        "gate_vs_label_agreement": f"{gate_agree}/{n}",
        "nanojev_vs_label_agreement": f"{nj_agree}/{n}",
        "gate_vs_nanojev_agreement": f"{sum(1 for r in evaluable if r['gate'] == r['nanojev'])}/{n}",
        "nanojev_latency_ms_p50": pct(0.5),
        "nanojev_latency_ms_p95": pct(0.95),
        "rows": rows,
    }
    (lab / "bench_results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("-" * 100)
    print(f"NanoJev decisions produced : {summary['nanojev_decisions_produced']}")
    print(f"gate vs label agreement    : {summary['gate_vs_label_agreement']}")
    print(f"nanojev vs label agreement : {summary['nanojev_vs_label_agreement']}")
    print(f"gate vs nanojev agreement  : {summary['gate_vs_nanojev_agreement']}")
    print(f"nanojev latency p50/p95 ms : {summary['nanojev_latency_ms_p50']} / {summary['nanojev_latency_ms_p95']}")
    print("wrote lab/track1/bench_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
