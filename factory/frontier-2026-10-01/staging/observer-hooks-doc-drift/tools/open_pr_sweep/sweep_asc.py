#!/usr/bin/env python3
"""Read-only sweep: every open NousResearch/hermes-agent PR's file list, looking for one path.

Writes one JSON line per PR to prs.jsonl (number, headRefOid, changedFiles, paths
truncated at 100) and the cursor to cursor.txt so it can resume. PRs with more
than 100 changed files are re-read through the REST files endpoint afterwards.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "prs_asc.jsonl")
CUR = os.path.join(HERE, "cursor_asc.txt")
LOG = os.path.join(HERE, "sweep_asc.log")
Q = """query($c:String){repository(owner:"NousResearch",name:"hermes-agent"){
pullRequests(states:OPEN,first:100,after:$c,orderBy:{field:CREATED_AT,direction:ASC}){
totalCount pageInfo{hasNextPage endCursor}
nodes{number headRefOid changedFiles author{login} files(first:100){nodes{path}}}}}
rateLimit{cost remaining resetAt}}"""


def log(msg):
    with open(LOG, "a") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")


def page(cursor):
    args = ["gh", "api", "graphql", "-f", "query=" + Q]
    if cursor:
        args += ["-f", "c=" + cursor]
    for attempt in range(8):
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode == 0:
            d = json.loads(r.stdout)
            if "errors" not in d:
                return d
            log(f"graphql errors: {d['errors']}")
        else:
            log(f"rc={r.returncode} {r.stderr.strip()[:300]}")
        time.sleep(5 * (attempt + 1))
    raise SystemExit("giving up at cursor " + str(cursor))


cursor = open(CUR).read().strip() if os.path.exists(CUR) else None
if cursor == "DONE":
    sys.exit(0)
n_pages = 0
while True:
    d = page(cursor)
    pr = d["data"]["repository"]["pullRequests"]
    with open(OUT, "a") as f:
        for n in pr["nodes"]:
            f.write(json.dumps({
                "number": n["number"], "head": n["headRefOid"], "changedFiles": n["changedFiles"],
                "author": (n["author"] or {}).get("login"),
                "paths": None if n["files"] is None else [x["path"] for x in n["files"]["nodes"]],
            }) + "\n")
    n_pages += 1
    if n_pages % 20 == 0:
        log(f"page {n_pages} total={pr['totalCount']} rate={d['data']['rateLimit']}")
    if not pr["pageInfo"]["hasNextPage"]:
        open(CUR, "w").write("DONE")
        log(f"done after {n_pages} pages this run; totalCount={pr['totalCount']}")
        break
    cursor = pr["pageInfo"]["endCursor"]
    open(CUR, "w").write(cursor)
