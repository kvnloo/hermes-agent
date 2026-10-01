#!/usr/bin/env python3
"""Read-only: re-read full file lists over REST for PRs whose GraphQL list was null or cut at 100.

usage: rest_files.py <pr numbers...>   -> appends to prs_rest.jsonl
REST returns at most 3000 files per PR; a PR at that cap is flagged.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "prs_rest.jsonl")
for n in map(int, sys.argv[1:]):
    for attempt in range(6):
        r = subprocess.run(["gh", "api", "--paginate",
                            f"repos/NousResearch/hermes-agent/pulls/{n}/files?per_page=100",
                            "--jq", ".[].filename"], capture_output=True, text=True)
        if r.returncode == 0:
            break
        sys.stderr.write(f"#{n} retry {attempt}: {r.stderr.strip()[:200]}\n")
        time.sleep(4 * (attempt + 1))
    else:
        paths = None
    paths = r.stdout.split() if r.returncode == 0 else None
    with open(OUT, "a") as f:
        f.write(json.dumps({"number": n, "paths": paths, "n": None if paths is None else len(paths),
                            "at_rest_cap": bool(paths and len(paths) >= 3000)}) + "\n")
