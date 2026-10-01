"""Static merge checks for staging/anthropic-context-editing: the branch against main, and each
listed upstream PR (fetched read-only into refs/xf/pr/<n>) against main and against the branch.
Roles: "dependency" = a preserved-thinking PR this waits on (P12); "related" = touches the same
request field or beta (#71302: OAuth clear_thinking + the context-management beta); "neighbour" =
edits the same compression config/docs block (file overlap only). Writes receipts/MERGE-<run>.json.
Temporary merge commits are unreferenced objects.

Usage: python merge_check.py --git-dir <bare repo> --main <sha> --branch <sha> --run r20261001-04
"""
import argparse
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path

A = Path(__file__).resolve().parents[1]
PRS = {103476: ("teknium1", "dependency"), 129620: ("JoaoMarcos44", "dependency"), 129492: ("SHL0MS", "dependency"),
       129882: ("Sahilvishnaliya", "dependency"), 71302: ("TrueNix", "related"), 128432: ("Julientalbot", "neighbour"),
       129364: ("thanosapollo", "neighbour")}

ap = argparse.ArgumentParser()
ap.add_argument("--git-dir", required=True)
ap.add_argument("--main", required=True)
ap.add_argument("--branch", required=True)
ap.add_argument("--run", required=True)
ARGS = ap.parse_args()


def git(*args, check=True):
    p = subprocess.run(["git", "-C", ARGS.git_dir, "-c", "user.name=xf", "-c", "user.email=xf@invalid", *args],
                       capture_output=True, text=True)
    if check and p.returncode not in (0, 1):
        raise RuntimeError(p.stderr)
    return p


MERGES: list[str] = []  # one entry per merge-tree actually run; this is the cell count
T0, C0 = time.monotonic(), resource.getrusage(resource.RUSAGE_CHILDREN)


def merge(a, b):
    MERGES.append(f"{a[:10]} x {b[:10]}")
    p = git("merge-tree", "--write-tree", "--name-only", a, b)
    lines = p.stdout.splitlines()
    conflicts = [ln for ln in lines[1:] if ln and not ln.startswith(("Auto-merging", "CONFLICT"))]
    return {"clean": p.returncode == 0, "tree": lines[0] if lines else None, "conflicted_files": conflicts}


def files(a, b):
    base = git("merge-base", a, b).stdout.strip()
    return set(git("diff", "--name-only", base, b).stdout.split())


branch_files = files(ARGS.main, ARGS.branch)
out = {"branch_x_main": merge(ARGS.main, ARGS.branch), "prs": {}}
for n, (author, role) in PRS.items():
    head = git("rev-parse", f"refs/xf/pr/{n}").stdout.strip()
    pr_files = files(ARGS.main, head)
    row = {"author": author, "role": role, "head": head, "files": sorted(pr_files), "overlap_with_branch": sorted(pr_files & branch_files),
           "main_x_pr": merge(ARGS.main, head)}
    if row["main_x_pr"]["clean"]:
        tmp = git("commit-tree", row["main_x_pr"]["tree"], "-p", ARGS.main, "-p", head, "-m", "tmp").stdout.strip()
        row["main_plus_pr_x_branch"] = merge(tmp, ARGS.branch)
    else:
        row["main_plus_pr_x_branch"] = {"skipped": "main x PR conflicts, so there is no main + PR tree to merge with the branch"}
    row["pr_x_branch_direct"] = merge(head, ARGS.branch)
    out["prs"][str(n)] = row

C1 = time.monotonic(), resource.getrusage(resource.RUSAGE_CHILDREN)
WALL = round(C1[0] - T0, 1)
CPU = round((C1[1].ru_utime - C0.ru_utime) + (C1[1].ru_stime - C0.ru_stime), 1)

receipt = {
    "schema": "xf.receipt.v1", "id": f"MERGE/{ARGS.run}", "tier": "T0", "label_default": "OBSERVED",
    "spec": {"path": None, "prereg_commit": None, "note": "static merge-tree check; no oracle beyond clean/conflict"},
    "runner_revision": {"driver": {"path": "harness/merge_check.py", "sha256": hashlib.sha256((A / "harness/merge_check.py").read_bytes()).hexdigest()},
                        "git": subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip()},
    "issue": "kvnloo/hermes-agent#322",
    "origin_refs": [f"NousResearch/hermes-agent#{n}" for n in PRS],
    "staging": "anthropic-context-editing",
    "base_revision": ARGS.main, "head_revision": ARGS.branch,
    "changed_files": sorted(branch_files),
    "policy_revision": {"factory": "FACTORY.md sha256 7726ba18b43a9367f91d7f70c3aaefb96a9863761ddf71225c61c26a30d688d4 (frontier-2026-10-01)"},
    "command": f"python3 harness/merge_check.py --git-dir <h.git> --main {ARGS.main} --branch {ARGS.branch} --run {ARGS.run}",
    "results": out,
    "denominators": {"cells": len(MERGES), "cells_note": "merge-tree runs: branch x main, then per PR main x PR, main + PR x branch (only when main x PR is clean) and PR x branch; PR roles: dependency (P12 ordering), related (same field/beta), neighbour (same config/docs block)", "errored_scored_zero": 0, "infra_excluded": 0, "completeness": 1.0},
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "static"},
    "resource_usage": {"wall_s": WALL, "cpu_core_s": CPU, "gpu_s": 0, "energy_j": None, "tokens": 0, "api_cost_usd": 0.0},
    "provenance": "self",
    "frozen": {"bundle_sha": None, "cells": len(MERGES), "supersedes": "MERGE/r20261001-03 (superseded/r20261001-03/receipts/; it covered only the 4 dependency PRs)", "status": "NOT_FROZEN (P8 pending)"},
    "privacy": "public-aggregate",
    "verdict": "CLEAN" if out["branch_x_main"]["clean"] else "CONFLICT",
}
(A / "receipts" / f"MERGE-{ARGS.run}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"cells": len(MERGES), "branch_x_main": out["branch_x_main"],
                  **{n: {k: (v if k != "files" else len(v)) for k, v in r.items() if k not in ("author", "role")} for n, r in out["prs"].items()}}, indent=1))
