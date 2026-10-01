"""C1 (T0): the runner refuses anything that is not a claimed hermes-agent work_order with a matching spec hash.

    python c1_envelope_only.py <runner worktree> <repo> <scratch dir> <out.json>

Copies specs/F11-P1-fork50.{toml,wo.json} into scratch, mutates one thing per case and runs the CLI.
Pass = every case refused and no run directory created. (Round 1: written down as a script; pass 2 ran
the same four cases inline.)
"""
import hashlib, json, os, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

wt, repo, scratch, out_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
SPECS = Path(__file__).resolve().parents[1] / "specs"
PY = os.environ.get("XF_PYTHON") or sys.executable  # <venv-python>: the interpreter the cells use (read-only)


def case(name, mutate_spec=None, mutate_wo=None, drop_work_order=False):
    d = scratch / name.replace(" ", "-")
    d.mkdir(parents=True)
    spec, wo = d / "F11-P1-fork50.toml", d / "F11-P1-fork50.wo.json"
    shutil.copyfile(SPECS / "F11-P1-fork50.toml", spec)
    order = json.loads((SPECS / "F11-P1-fork50.wo.json").read_text())
    if mutate_spec:
        spec.write_text(mutate_spec(spec.read_text()))
    if mutate_wo:
        mutate_wo(order)
    wo.write_text(json.dumps(order))
    runs = d / "runs"
    argv = [PY, "-m", "evals._factory.gate_runner", "run", "--repo", repo, "--scratch", str(runs), "--python", PY,
            "--out", str(d / "out.json")] + ([] if drop_work_order else ["--work-order", str(wo)])
    p = subprocess.run(argv, cwd=wt, capture_output=True, text=True, timeout=300,
                       env={"PATH": "/usr/bin:/bin", "HOME": os.environ["HOME"], "HERMES_HOME": os.environ["HERMES_HOME"]})
    err = (p.stderr.strip().splitlines() or [""])[-1]
    if drop_work_order:
        err = "argparse error: " + err.split("error: ", 1)[-1]
    return {"case": name, "rc": p.returncode, "observed": err, "refused": p.returncode != 0 and not (d / "out.json").exists(),
            "run_directories_created": len(list(runs.iterdir())) if runs.exists() else 0}


rows = [
    case("spec changed by one value after the envelope was minted", mutate_spec=lambda s: s.replace("reps = 3", "reps = 2")),
    case("envelope kind = receipt", mutate_wo=lambda o: o.__setitem__("kind", "receipt")),
    case("envelope without civ.city_id", mutate_wo=lambda o: o.pop("civ")),
    case("no --work-order argument", drop_work_order=True),
]
runner_sha = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
receipt = {
    "schema": "xf.experiment.v1", "id": "C1-envelope-only/r" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), "tier": "T0",
    "cost_usd": 0, "label": "OBSERVED",
    "question": "Does the runner refuse anything that is not a claimed hermes-agent work_order whose spec hash matches, before creating a run?",
    "inputs": {"runner_commit": runner_sha,
               "gate_runner_sha256": hashlib.sha256((wt / "evals/_factory/gate_runner.py").read_bytes()).hexdigest(),
               "fixture": "specs/F11-P1-fork50.toml + .wo.json, copied and mutated in scratch"},
    "command": "python c1_envelope_only.py <worktree@runner_commit> h.git <scratch> receipts/C1-envelope-only.json",
    "results": rows,
    "run_directories_created": sum(r["run_directories_created"] for r in rows),
    "verdict": ("PASS" if all(r["refused"] for r in rows) and not any(r["run_directories_created"] for r in rows) else "FAIL")
               + f" ({sum(r['refused'] for r in rows)}/{len(rows)} refused before any run directory or worktree existed)",
    "scheduler_surface": "none by construction: one work order per invocation; no loop, timer, queue read or GitHub call in "
                         "evals/_factory/gate_runner.py (source read, not a test)",
    "not_tested": ["that the claim itself (SPEC section 2 lease) exists on GitHub: the runner trusts the envelope's status field"],
}
out_path.write_text(json.dumps(receipt, indent=1) + "\n")
print(receipt["verdict"])
for r in rows:
    print(" ", r["case"], "->", r["observed"])
