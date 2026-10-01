"""E19 post-processor: cache-read ratio around a mid-conversation model switch, from logcalls.parse_logs.

For every session whose ``model=`` changes between consecutive usage-bearing calls, report the hit ratio
(cache_read / prompt tokens) over the K calls before and the K calls after the switch, plus the coverage
the parser achieved, printed FIRST (the lane's rule: quote nothing without coverage). Calls with
cache_state=no_field and usage=unavailable lines are excluded from the ratio and counted.

    python e19_switch.py <logcalls.py> <state.db> <agent.log glob> [K]

Reads only the files given (copies, never a live home).
"""
import glob
import importlib.util
import json
import sys
import tempfile

LOGCALLS, DB, LOGS = sys.argv[1:4]
K = int(sys.argv[4]) if len(sys.argv) > 4 else 5
spec = importlib.util.spec_from_file_location("logcalls_variant", LOGCALLS)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from evals.postmortem.forensics.common import Run  # noqa: E402  (repo root on PYTHONPATH)

run = Run.open(DB, out=tempfile.mkdtemp(prefix="e19-"))
calls = mod.parse_logs(sorted(glob.glob(LOGS)), set(run.in_run))
metered = [c for c in calls if c.get("inp") is not None]
total = run.summary()["api_calls"]
by_sid = {}
for c in metered:
    by_sid.setdefault(c["sid"], []).append(c)


def ratio(cs):
    cs = [c for c in cs if c.get("cache_state") != "no_field"]
    tin = sum(c["inp"] for c in cs)
    return (round(sum(c["hit"] for c in cs) / tin, 4) if tin else None), len(cs)


switches = []
for sid, cs in by_sid.items():
    cs.sort(key=lambda c: c["n"])
    for i in range(1, len(cs)):
        if cs[i]["model"] != cs[i - 1]["model"]:
            before, nb = ratio(cs[max(0, i - K):i])
            after, na = ratio(cs[i:i + K])
            switches.append({"sid_index": len(switches), "from": cs[i - 1]["model"], "to": cs[i]["model"],
                             "call_n": cs[i]["n"], "before": before, "after": after, "n_before": nb, "n_after": na})
out = {"coverage": {"calls_found": len(metered), "run_api_calls": total,
                    "fraction": round(len(metered) / total, 4) if total else None,
                    "usage_unavailable": len(calls) - len(metered)},
       "k": K, "switches": switches}
print(json.dumps(out, indent=1))
