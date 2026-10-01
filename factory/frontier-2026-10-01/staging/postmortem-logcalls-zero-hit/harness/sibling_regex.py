"""Offline check of the two live probes' per-call parsers (T0, static + replay of real producer lines).

The probes run a live provider loop at import, so they are never imported here. Instead the exact regex
literal passed to re.findall(...) is pulled out of each file with ast, for the base and patched version,
and applied to the API-call lines the real producer emitted in the round-trip receipt (rt_<arm>.json).
The per-row arithmetic mirrors the probe's loop: cached = int(c or 0) on the patched side.

    python sibling_regex.py <base_dir_with_probe_copies> <patched_repo> <rt_json>...
"""
import ast
import json
import re
import sys
from pathlib import Path

BASE, PATCHED, RTS = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
PROBES = ("cache_prefix_live.py", "cache_prefix_wire.py")


def findall_regex(src: str) -> str:
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "findall"
                and node.args and isinstance(node.args[0], ast.Constant) and "API call" in node.args[0].value):
            return node.args[0].value
    raise SystemExit("findall regex not found")


out = {"probes": {}, "arms": {}}
for probe in PROBES:
    out["probes"][probe] = {"base": findall_regex((BASE / probe).read_text(encoding="utf-8")),
                            "patched": findall_regex((PATCHED / "evals/postmortem/live_ab" / probe).read_text(encoding="utf-8"))}
for rt in RTS:
    d = json.loads(Path(rt).read_text(encoding="utf-8"))
    log = "\n".join(d["lines"]) + "\n"
    metered = sum(1 for ln in d["lines"] if "in=?" not in ln)
    arm = {"lines": len(d["lines"]), "metered_lines": metered, "per_probe": {}}
    for probe, rx in out["probes"].items():
        res = {}
        for side in ("base", "patched"):
            rows = re.findall(rx[side], log)
            tot_in = sum(int(r[1]) for r in rows)
            tot_c = sum(int(r[3] or 0) for r in rows)
            res[side] = {"rows": len(rows), "input": tot_in, "cached": tot_c,
                         "arm_hit_pct": round(100 * tot_c / max(tot_in, 1), 1),
                         "rows_detail": [[r[0], r[1], r[3] or "0"] for r in rows]}
        arm["per_probe"][probe] = res
    out["arms"][d["arm"]] = arm
print(json.dumps(out, indent=1))
