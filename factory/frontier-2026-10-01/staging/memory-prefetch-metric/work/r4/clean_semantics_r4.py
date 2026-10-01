"""For each flagged PR that merges cleanly with the staging head, compare MemoryManager._prefetch_provider in the
merged tree with the head's, and count record_memory_prefetch calls and return statements in it.
Usage: python clean_semantics_r4.py <h.git> <flagged_merge json> <out json>
"""
import json, re, subprocess, sys
hg, src, out = sys.argv[1:]
HEAD = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"
def fn(tree):
    s = subprocess.run(["git", "-C", hg, "show", f"{tree}:agent/memory_manager.py"], capture_output=True, text=True).stdout
    m = re.search(r"\n    def _prefetch_provider\(.*?(?=\n    def )", s, re.S)
    return m.group(0) if m else ""
base_fn = fn(HEAD)
res = {"head_fn": {"records": base_fn.count("record_memory_prefetch("), "returns": len(re.findall(r"\breturn\b", base_fn)), "raises": len(re.findall(r"\braise\b", base_fn))}, "prs": {}}
for n, v in json.load(open(src))["prs"].items():
    if v["class"] != "clean_both":
        continue
    sha = subprocess.run(["gh", "api", f"repos/NousResearch/hermes-agent/pulls/{n}", "--jq", ".head.sha"], capture_output=True, text=True).stdout.strip()
    tree = subprocess.run(["git", "-C", hg, "merge-tree", "--write-tree", HEAD, sha], capture_output=True, text=True).stdout.split()[0]
    f = fn(tree)
    res["prs"][n] = {"author": v["author"], "title": v["title"], "fn_changed": f != base_fn,
                     "records": f.count("record_memory_prefetch("), "returns": len(re.findall(r"\breturn\b", f)),
                     "raises": len(re.findall(r"\braise\b", f))}
    print(n, v["author"], res["prs"][n])
json.dump(res, open(out, "w"), indent=1, ensure_ascii=False)
print("head", res["head_fn"])
