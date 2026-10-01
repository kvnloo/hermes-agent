"""Static merge checks for staging/anthropic-context-editing: the branch against main, and each
preserved-thinking dependency PR (fetched read-only into refs/xf/pr/<n>) against main and against
the branch. Writes receipts/MERGE-<run>.json. Temporary merge commits are unreferenced objects.

Usage: python merge_check.py --git-dir <bare repo> --main <sha> --branch <sha> --run r20261001-02
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

A = Path(__file__).resolve().parents[1]
PRS = {103476: "teknium1", 129620: "JoaoMarcos44", 129492: "SHL0MS", 129882: "Sahilvishnaliya"}

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


def merge(a, b):
    p = git("merge-tree", "--write-tree", "--name-only", a, b)
    lines = p.stdout.splitlines()
    conflicts = [ln for ln in lines[1:] if ln and not ln.startswith(("Auto-merging", "CONFLICT"))]
    return {"clean": p.returncode == 0, "tree": lines[0] if lines else None, "conflicted_files": conflicts}


def files(a, b):
    base = git("merge-base", a, b).stdout.strip()
    return set(git("diff", "--name-only", base, b).stdout.split())


branch_files = files(ARGS.main, ARGS.branch)
out = {"branch_x_main": merge(ARGS.main, ARGS.branch), "prs": {}}
for n, author in PRS.items():
    head = git("rev-parse", f"refs/xf/pr/{n}").stdout.strip()
    pr_files = files(ARGS.main, head)
    row = {"author": author, "head": head, "files": sorted(pr_files), "overlap_with_branch": sorted(pr_files & branch_files),
           "main_x_pr": merge(ARGS.main, head)}
    if row["main_x_pr"]["clean"]:
        tmp = git("commit-tree", row["main_x_pr"]["tree"], "-p", ARGS.main, "-p", head, "-m", "tmp").stdout.strip()
        row["main_plus_pr_x_branch"] = merge(tmp, ARGS.branch)
    row["pr_x_branch_direct"] = merge(head, ARGS.branch)
    out["prs"][str(n)] = row

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
    "denominators": {"cells": 1 + 3 * len(PRS), "errored_scored_zero": 0, "infra_excluded": 0, "completeness": 1.0},
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "static"},
    "resource_usage": {"wall_s": None, "cpu_core_s": None, "gpu_s": 0, "energy_j": None, "tokens": 0, "api_cost_usd": 0.0},
    "provenance": "self",
    "frozen": {"bundle_sha": None, "cells": 1 + 3 * len(PRS), "supersedes": None, "status": "NOT_FROZEN (P8 pending)"},
    "privacy": "public-aggregate",
    "verdict": "CLEAN" if out["branch_x_main"]["clean"] else "CONFLICT",
}
(A / "receipts" / f"MERGE-{ARGS.run}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"branch_x_main": out["branch_x_main"],
                  **{n: {k: (v if k != "files" else len(v)) for k, v in r.items() if k != "author"} for n, r in out["prs"].items()}}, indent=1))
