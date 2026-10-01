#!/usr/bin/env python3
"""Read-only: list open PRs created in [start, end) with their changed paths, via the GraphQL
pullRequests connection (ASC by createdAt) starting from a synthesised cursor at `start`.

    python3 overlap_scan_segment.py 2026-05-09T10:00:00Z 2026-05-26T11:52:30Z seg0.jsonl

Re-running with the same out file resumes from its last createdAt. Run at most 2-3 segments at once on
a shared token; more trips GitHub's secondary rate limit (the script then sleeps 90 s and retries).
"""
import base64, json, subprocess, sys, time

start, end, out = sys.argv[1], sys.argv[2], sys.argv[3]
Q = '''query($c:String,$n:Int!){ rateLimit{remaining} repository(owner:"NousResearch",name:"hermes-agent"){
 pullRequests(states:OPEN, first:$n, after:$c, orderBy:{field:CREATED_AT,direction:ASC}){
  pageInfo{hasNextPage endCursor}
  nodes{ number createdAt updatedAt headRefOid baseRefName isDraft author{login}
         labels(first:30){nodes{name}}
         files(first:100){ totalCount pageInfo{hasNextPage endCursor} nodes{path} } } } } }'''


def cursor_at(iso):
    s = iso.encode()
    assert len(s) == 20
    return base64.b64encode(b"cursor:v2:" + bytes([0x92, 0xA0 | len(s)]) + s + bytes([0xCE, 0, 0, 0, 0])).decode()


resume = start
try:  # re-running on the same out file resumes from its last createdAt (duplicates are de-duplicated later)
    with open(out) as fh:
        for line in fh:
            resume = max(resume, json.loads(line)["createdAt"])
except FileNotFoundError:
    pass
cursor, size = cursor_at(resume), 100
with open(out, "a") as fh:
    while True:
        attempt = 0
        while attempt < 10:
            args = ["gh", "api", "graphql", "-f", "query=" + Q, "-F", f"n={size}", "-f", "c=" + cursor]
            p = subprocess.run(args, capture_output=True, text=True, timeout=120)
            if p.returncode == 0:
                try:
                    d = json.loads(p.stdout)
                    if d.get("data") and d["data"].get("repository"):
                        break
                except Exception:
                    pass
            if "secondary rate limit" in p.stderr:  # shared token: wait it out, keep the page size
                print("secondary rate limit; sleeping 90 s", flush=True)
                time.sleep(90)
                continue
            attempt += 1
            print(f"retry size={size} err={p.stderr[:120]!r}", flush=True)
            size = max(5, size // 2)
            time.sleep(3 * attempt)
        else:
            print("FAILED", file=sys.stderr)
            sys.exit(1)
        pr = d["data"]["repository"]["pullRequests"]
        stop = False
        for n in pr["nodes"]:
            if n["createdAt"] >= end:
                stop = True
                break
            fh.write(json.dumps(n) + "\n")
        fh.flush()
        last = pr["nodes"][-1]["createdAt"] if pr["nodes"] else None
        print(f"seg {start} n={len(pr['nodes'])} last={last}", flush=True)
        if stop or not pr["pageInfo"]["hasNextPage"]:
            print("SEGMENT DONE", flush=True)
            break
        cursor = pr["pageInfo"]["endCursor"]
        size = min(100, size * 2)
