#!/usr/bin/env python3
"""FACTORY S8 push-trigger scan of .github/workflows/* on an exact tree (factory-only; read-only).

usage: chs_workflow_scan_r5.py <h.git> <commit> <branch>

Prints one JSON object: how many workflow files have no push trigger, a push trigger whose branch filters do not
match <branch>, a tags-only push trigger, or a push trigger that matches <branch> (must be 0 before a push).
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
import sys

import yaml


def git(h, *args):
    return subprocess.run(["git", "-C", h, *args], capture_output=True, text=True, check=True).stdout


def branch_match(patterns, branch):
    return any(fnmatch.fnmatchcase(branch, p.replace("**", "*")) for p in patterns)


def main() -> int:
    h, commit, branch = sys.argv[1:4]
    names = [n for n in git(h, "ls-tree", "--name-only", f"{commit}:.github/workflows").split() if n.endswith((".yml", ".yaml"))]
    out = {"commit": commit, "branch": branch, "files": len(names), "no_push": [], "push_not_matching": [],
           "tags_only": [], "matching": []}
    for n in names:
        doc = yaml.safe_load(git(h, "show", f"{commit}:.github/workflows/{n}")) or {}
        on = doc.get("on", doc.get(True))  # YAML 1.1 reads a bare `on:` key as True
        if isinstance(on, str):
            on = {on: None}
        elif isinstance(on, list):
            on = {k: None for k in on}
        if not isinstance(on, dict) or "push" not in on:
            out["no_push"].append(n)
            continue
        push = on.get("push") or {}
        branches, ignore, tags = push.get("branches"), push.get("branches-ignore"), push.get("tags")
        if branches is None and ignore is None and tags is not None:
            out["tags_only"].append(n)
        elif branches is not None:
            (out["matching"] if branch_match(branches, branch) else out["push_not_matching"]).append(n)
        elif ignore is not None:
            (out["push_not_matching"] if branch_match(ignore, branch) else out["matching"]).append(n)
        else:
            out["matching"].append(n)
    out["counts"] = {k: len(out[k]) for k in ("no_push", "push_not_matching", "tags_only", "matching")}
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
