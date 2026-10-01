#!/usr/bin/env python3
"""Aggregate raw/<run>/ (written by tools/chs_guards.sh) into receipts/E12-<run>.json.

Verdict maps compared per arm against the "base" arm: replay_gates (whole result JSON minus volatile
fields), ab_checkpoint_preflight (per-scenario compress-call counts), test_region_scoping and the
adjacent pytest summary. Observer counters come from tools/chs_guard_wrap.py.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ST = Path(__file__).resolve().parents[1]
run = sys.argv[1]
raw = ST / "raw" / run
VOLATILE = {"checkout", "head", "elapsed_s", "wall_s", "duration_s", "tmp", "home", "session_id", "requests"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in VOLATILE and not k.endswith("_ms")}
    if isinstance(o, list):
        return [strip(v) for v in o]
    if isinstance(o, str) and re.search(r"/tmp/|/var/tmp/|\d{8}_\d{6}_[0-9a-f]{6}", o):
        return "<volatile>"
    return o


def load(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception as exc:  # noqa: BLE001
        return {"_unreadable": repr(exc)}


def pytest_summary(log: Path):
    if not log.exists():
        return None
    txt = log.read_text(errors="replace")
    m = re.search(r"=== Summary: (\d+) files?, (\d+) tests? passed, (\d+) failed", txt)
    if m:
        return {"files": int(m.group(1)), "passed": int(m.group(2)), "failed": int(m.group(3)),
                "failing": sorted(set(re.findall(r"^FAILED (\S+)", txt, flags=re.M)))}
    m = re.search(r"(\d+) passed(?:, (\d+) failed)?", txt)
    return {"passed": int(m.group(1)), "failed": int(m.group(2) or 0)} if m else {"unparsed": txt[-400:]}


def region(log: Path):
    txt = log.read_text(errors="replace") if log.exists() else ""
    return {"verdict": "ALL PASS" if "scoping tripwire: ALL PASS" in txt else "FAIL", "tail": txt.strip().splitlines()[-3:]}


arms = {}
for line in (raw / "arms.txt").read_text().splitlines():
    arm, commit, tree = line.split()
    rg = load(raw / f"{arm}-replay_gates.json")
    pf = load(raw / f"{arm}-ab_checkpoint_preflight.json")
    arms[arm] = {
        "commit": commit, "tree": tree,
        "replay_gates": {"file": f"raw/{run}/{arm}-replay_gates.json", "sha256": sha(raw / f"{arm}-replay_gates.json")
                         if (raw / f"{arm}-replay_gates.json").exists() else None,
                         "verdicts": strip(rg), "observer_counts": load(raw / f"{arm}-replay_gates.counts.json")},
        "ab_checkpoint_preflight": {"file": f"raw/{run}/{arm}-ab_checkpoint_preflight.json",
                                    "verdicts": strip(pf),
                                    "observer_counts": load(raw / f"{arm}-ab_checkpoint_preflight.counts.json")},
        "test_region_scoping": region(raw / f"{arm}-test_region_scoping.log"),
        "adjacent": pytest_summary(raw / f"{arm}-adjacent.log"),
    }

base = arms.get("base")
for arm, a in arms.items():
    if base is None or arm == "base":
        continue
    a["equal_to_base"] = {
        "replay_gates": a["replay_gates"]["verdicts"] == base["replay_gates"]["verdicts"],
        "ab_checkpoint_preflight": a["ab_checkpoint_preflight"]["verdicts"] == base["ab_checkpoint_preflight"]["verdicts"],
        "test_region_scoping": a["test_region_scoping"]["verdict"] == base["test_region_scoping"]["verdict"],
    }
    for key in ("replay_gates", "ab_checkpoint_preflight"):
        if not a["equal_to_base"][key]:
            diffs = []

            def walk(x, y, path=""):
                if isinstance(x, dict) and isinstance(y, dict):
                    for k in sorted(set(x) | set(y)):
                        walk(x.get(k), y.get(k), f"{path}.{k}")
                elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
                    for i, (u, v) in enumerate(zip(x, y)):
                        walk(u, v, f"{path}[{i}]")
                elif x != y:
                    diffs.append({"path": path, "base": y, "arm": x})
            walk(a[key]["verdicts"], base[key]["verdicts"])
            a.setdefault("diff_vs_base", {})[key] = diffs[:20]

receipt = {"schema": "xf.receipt.v1", "id": f"E12/{run}", "label": "OBSERVED", "staging": "compaction-hook-salvage",
           "harness": {"replay_gates": "evals/token_accounting/replay_gates.py",
                       "ab_checkpoint_preflight": "evals/native_compaction/ab_checkpoint_preflight.py",
                       "test_region_scoping": "evals/compaction/test_region_scoping.py",
                       "wrapper": "tools/chs_guard_wrap.py", "wrapper_sha256": sha(ST / "tools" / "chs_guard_wrap.py"),
                       "script": "tools/chs_guards.sh", "script_sha256": sha(ST / "tools" / "chs_guards.sh")},
           "arms": arms}
out = ST / "receipts" / f"E12-{run}.json"
out.write_text(json.dumps(receipt, indent=1, default=str))
print(out, sha(out))
for arm, a in arms.items():
    print(arm, a.get("equal_to_base"), "rg_counts", {k: a["replay_gates"]["observer_counts"].get(k) for k in ("rc", "hook_fires", "commits_total", "commits_succeeded")},
          "pf_counts", {k: a["ab_checkpoint_preflight"]["observer_counts"].get(k) for k in ("rc", "hook_fires", "commits_total")},
          "region", a["test_region_scoping"], "adj", a["adjacent"])
