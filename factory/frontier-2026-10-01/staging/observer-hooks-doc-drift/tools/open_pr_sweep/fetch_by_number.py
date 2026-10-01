#!/usr/bin/env python3
"""Read-only: fetch file lists for the PR numbers in <numbers file>, 40 per aliased GraphQL query.

usage: fetch_by_number.py <numbers-file> <out.jsonl>
Resumable: numbers already present in <out.jsonl> are skipped.
"""
import json, os, subprocess, sys, time

nums_file, out = sys.argv[1], sys.argv[2]
want = [int(x) for x in open(nums_file).read().split()]
done = set()
if os.path.exists(out):
    for line in open(out):
        if line.strip():
            done.add(json.loads(line)["number"])
todo = [n for n in want if n not in done]
FIELDS = "number headRefOid changedFiles author{login} state files(first:100){nodes{path}}"


def run(batch):
    body = " ".join(f"p{n}: pullRequest(number:{n}){{{FIELDS}}}" for n in batch)
    q = 'query{repository(owner:"NousResearch",name:"hermes-agent"){' + body + "}}"
    for attempt in range(8):
        r = subprocess.run(["gh", "api", "graphql", "-f", "query=" + q], capture_output=True, text=True)
        if r.returncode == 0:
            d = json.loads(r.stdout)
            if d.get("data") and d["data"].get("repository"):
                return d["data"]["repository"], d.get("errors")
        sys.stderr.write(f"retry {attempt} rc={r.returncode} {r.stderr.strip()[:200]}\n")
        time.sleep(4 * (attempt + 1))
    raise SystemExit(f"failed batch starting {batch[0]}")


for i in range(0, len(todo), 40):
    batch = todo[i:i + 40]
    repo, errs = run(batch)
    with open(out, "a") as f:
        for n in batch:
            node = repo.get(f"p{n}")
            if node is None:
                f.write(json.dumps({"number": n, "head": None, "changedFiles": None, "author": None,
                                    "state": None, "paths": None, "error": "null node"}) + "\n")
                continue
            f.write(json.dumps({
                "number": n, "head": node["headRefOid"], "changedFiles": node["changedFiles"],
                "author": (node["author"] or {}).get("login"), "state": node["state"],
                "paths": None if node["files"] is None else [x["path"] for x in node["files"]["nodes"]],
            }) + "\n")
