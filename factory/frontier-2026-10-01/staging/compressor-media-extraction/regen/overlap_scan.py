#!/usr/bin/env python3
"""Read-only: list every open NousResearch/hermes-agent PR with its changed paths via GraphQL
(one stream, ASC or DESC by createdAt; page size adapts to HTTP 502s).

    python3 overlap_scan.py ASC 400 open.jsonl [start-cursor]

For speed, overlap_scan_segment.py covers one createdAt window; run several in parallel and pass
all outputs to overlap_census.py (it de-duplicates by PR number)."""
import json, subprocess, sys, time

direction, pages_max, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
Q = '''query($c:String,$n:Int!){ rateLimit{cost remaining resetAt} repository(owner:"NousResearch",name:"hermes-agent"){
 pullRequests(states:OPEN, first:$n, after:$c, orderBy:{field:CREATED_AT,direction:%s}){
  totalCount pageInfo{hasNextPage endCursor}
  nodes{ number createdAt updatedAt headRefOid baseRefName isDraft author{login}
         labels(first:30){nodes{name}}
         files(first:100){ totalCount pageInfo{hasNextPage endCursor} nodes{path} } } } } }''' % direction

cursor = sys.argv[4] if len(sys.argv) > 4 else None
size = 100
with open(out, "a") as fh:
    for page in range(pages_max):
        for attempt in range(8):
            args = ["gh", "api", "graphql", "-f", "query=" + Q, "-F", f"n={size}"]
            if cursor:
                args += ["-f", "c=" + cursor]
            p = subprocess.run(args, capture_output=True, text=True, timeout=120)
            if p.returncode == 0:
                try:
                    d = json.loads(p.stdout)
                    if d.get("data") and d["data"].get("repository"):
                        break
                except Exception:
                    pass
            print(f"retry size={size} err={p.stderr[:200]!r}", flush=True)
            size = max(5, size // 2)
            time.sleep(3 * (attempt + 1))
        else:
            print("FAILED page", page, p.stderr[:500], file=sys.stderr)
            sys.exit(1)
        pr = d["data"]["repository"]["pullRequests"]
        for n in pr["nodes"]:
            fh.write(json.dumps(n) + "\n")
        fh.flush()
        rl = d["data"]["rateLimit"]
        print(f"{direction} page {page} n={len(pr['nodes'])} last={pr['nodes'][-1]['number'] if pr['nodes'] else None} total={pr['totalCount']} rl={rl['remaining']}", flush=True)
        if not pr["pageInfo"]["hasNextPage"]:
            break
        cursor = pr["pageInfo"]["endCursor"]
        print("cursor", cursor, flush=True)
        size = min(100, size * 2)
