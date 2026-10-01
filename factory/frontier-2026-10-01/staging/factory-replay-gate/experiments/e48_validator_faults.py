"""E48 (T0): validate_receipt() against 10 fault fixtures derived from one clean OBSERVED receipt.

    python e48_validator_faults.py <runner worktree> <clean receipt.json> <out.json>

Pass = every fault refused, the clean receipt accepted, verified_success still null on every fixture.
"""
import copy, hashlib, json, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

wt, clean_path, out_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(wt))
from evals._factory import gate_runner as gr  # noqa: E402

clean = json.loads(clean_path.read_text())
now = datetime.strptime(clean["generated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) + timedelta(hours=1)


def fault(name, mutate, **kw):
    r = copy.deepcopy(clean)
    mutate(r)
    return name, r, kw


def set_gate(gate, result, **detail):
    return lambda r: r["gates"].__setitem__(gate, {"result": result, **detail})


FAULTS = [
    fault("missing RED", lambda r: r["gates"].pop("red")),
    fault("GREEN on base (RED not reproduced)", set_gate("red", "FAIL", reps_agree="0/3", reason="no_repro_on_base")),
    fault("flaky reps", lambda r: (r["gates"].__setitem__("green", {"result": "FLAKY", "reps_agree": "2/3"}), r["gates"].__setitem__("flaky", True))),
    fault("infra exit counted", lambda r: r["denominators"].__setitem__("infra", 1)),
    fault("GREEN negative control", set_gate("sabotage", "FAIL", reason="no sabotage re-REDs")),
    fault("adjacent regression", set_gate("adjacent", "FAIL", regressions=["tests/x.py"])),
    fault("private-field leak", lambda r: r["limitations"].append("copied from /home/someone/.hermes/state.db")),
    fault("MODELED headline", lambda r: r["measurements"][0].__setitem__("label", "MODELED")),
    fault("stale base", lambda r: None, max_age_hours=24, now=now + timedelta(hours=48)),
    fault("unpinned PR head", lambda r: r.__setitem__("head_revision", r["head_revision"][:10])),
]
EXTRA = [fault("verified_success self-upgraded", lambda r: r["outcome"].__setitem__("verified_success", True)),
         # Round 1 (verifier finding): the pass-2 leak shape, an absolute run-directory path outside /home inside the Relay pin error.
         fault("absolute local path (non-home)", lambda r: r["env"]["relay"].__setitem__(
             "error", "ImportError: cannot import name 'resolve_plugin_sources' from 'agent.relay_runtime' (/srv/scratch/.xf-runs/x/arms/head/agent/relay_runtime.py)"))]

rows = []
for name, r, kw in FAULTS + EXTRA:
    problems = gr.validate_receipt(r, now=kw.get("now", now), max_age_hours=kw.get("max_age_hours"))
    rows.append({"fixture": name, "refused": bool(problems), "reasons": problems,
                 "verified_success": r["outcome"]["verified_success"], "core": name in [f[0] for f in FAULTS]})
clean_problems = gr.validate_receipt(clean, now=now, max_age_hours=24)
core = [x for x in rows if x["core"]]
runner_sha = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
receipt = {
    "schema": "xf.experiment.v1", "id": "E48/r" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), "tier": "T0", "cost_usd": 0,
    "label": "OBSERVED", "question": "Does validate_receipt refuse each injected fault and accept the clean receipt?",
    "inputs": {"runner_commit": runner_sha, "gate_runner_sha256": hashlib.sha256((wt / "evals/_factory/gate_runner.py").read_bytes()).hexdigest(),
               "clean_receipt": clean["id"], "clean_receipt_sha256": hashlib.sha256(clean_path.read_bytes()).hexdigest()},
    "command": "python e48_validator_faults.py <worktree@runner_commit> receipts/F11-P1-fork50.json receipts/E48-validator-faults.json",
    "results": {"core_faults_refused": f"{sum(x['refused'] for x in core)}/{len(core)}",
                "extra_faults_refused": f"{sum(x['refused'] for x in rows if not x['core'])}/{len(rows) - len(core)}",
                "clean_accepted": not clean_problems, "clean_problems": clean_problems,
                "verified_success_null_on_core_faults": all(x["verified_success"] is None for x in core)},
    "fixtures": rows,
    "verdict": "PASS" if all(x["refused"] for x in rows) and not clean_problems else "FAIL",
    "not_tested": ["joining z0int / verifier / component receipts into one envelope (kvnloo/hermes-agent#322 join half)",
                   "schema-level validation with a JSON Schema engine (validator is stdlib code)"],
}
out_path.write_text(json.dumps(receipt, indent=1) + "\n")
print(receipt["verdict"], receipt["results"])
