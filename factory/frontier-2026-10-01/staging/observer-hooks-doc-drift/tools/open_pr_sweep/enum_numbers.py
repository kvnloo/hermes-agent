#!/usr/bin/env python3
"""Read-only: enumerate every open PR number (no file lists) -> open_numbers.txt."""
import json, os, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
Q = """query($c:String){repository(owner:"NousResearch",name:"hermes-agent"){
pullRequests(states:OPEN,first:100,after:$c){totalCount pageInfo{hasNextPage endCursor} nodes{number}}}}"""
nums, cursor, total = set(), None, None
started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
while True:
    args = ["gh", "api", "graphql", "-f", "query=" + Q] + (["-f", "c=" + cursor] if cursor else [])
    for attempt in range(8):
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode == 0 and "errors" not in json.loads(r.stdout):
            break
        time.sleep(3 * (attempt + 1))
    else:
        raise SystemExit("enum failed")
    pr = json.loads(r.stdout)["data"]["repository"]["pullRequests"]
    total = pr["totalCount"]
    nums.update(n["number"] for n in pr["nodes"])
    if not pr["pageInfo"]["hasNextPage"]:
        break
    cursor = pr["pageInfo"]["endCursor"]
ended = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
with open(os.path.join(HERE, "open_numbers.txt"), "w") as f:
    f.write("\n".join(str(n) for n in sorted(nums)) + "\n")
json.dump({"started": started, "ended": ended, "totalCount_last_page": total, "unique_numbers": len(nums)},
          open(os.path.join(HERE, "open_numbers.meta.json"), "w"))
print(started, ended, total, len(nums))
