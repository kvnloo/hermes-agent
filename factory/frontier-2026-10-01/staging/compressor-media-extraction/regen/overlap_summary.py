#!/usr/bin/env python3
"""Summarise an overlap_census.py result (read-only)."""
import json, sys, collections
d = json.load(open(sys.argv[1]))
R = d["records"]
STACK = {80636, 80645, 80644, 81074, 81181}
fac = [r for r in R if r.get("touches_facade")]
print("open PRs scanned:", d["scanned"], "| file lists re-read via REST:", d["truncated_checked"])
print("PRs touching agent/context_compressor.py:", len(fac), "| drafts:", sum(1 for r in fac if r.get("isDraft")),
      "| updated since 2026-09-01:", sum(1 for r in fac if r["updatedAt"] >= "2026-09-01"))
print("PRs adding agent/context_compressor_media.py:", sorted(r["number"] for r in R if r.get("adds_media_module")))
print("not analysable:", [(r["number"], r["error"][:90]) for r in R if r.get("error")])
print("pre-image method:", dict(collections.Counter((r.get("preimage") or "none").split(" ")[0] for r in fac)))
edits = [r for r in fac if r.get("edits_moved")]
carried = [r for r in fac if r.get("carries_main_text_only") and not r.get("edits_moved")]
print("\nA. edit a moved statement (head text differs from both the PR's pre-image and main):", len(edits),
      "| outside the #80636 stack:", len([r for r in edits if r["number"] not in STACK]))
for r in sorted(edits, key=lambda r: r["number"]):
    print("  #%d %s upd=%s draft=%s %s%s" % (r["number"], r["author"], r["updatedAt"][:10], r.get("isDraft"),
          ",".join(r["edits_moved"]), "  [other-file scan skipped]" if r.get("other_files_scan") else ""))
print("\n   (only carry main's exact text of a moved statement, nothing to port:", len(carried), sorted(r["number"] for r in carried), ")")
nf = [r for r in fac if r.get("new_facade_refs")]
print("\nB. add a facade reference to a moved name the branch's facade does not import:", len(nf))
for r in nf:
    print("  #%d %s %s (also in A: %s)" % (r["number"], r["author"], r["new_facade_refs"], bool(r.get("edits_moved"))))
op = [r for r in R if r.get("other_files_new_old_path_refs")]
print("\nC. add an old-path reference to a moved name in another file (not on main):", len(op))
for r in op:
    for o in r["other_files_new_old_path_refs"]:
        print("  #%d %s %s breaks=%s gate-only=%s" % (r["number"], r["author"], o["file"], o["breaks_after_merge"], o["resolves_via_facade_import_gate_only"]))
oc = [r for r in R if r.get("other_files_carry_main_lines")]
print("\n   (carry main's old-path line that the branch rewrites:", len(oc), [(r["number"], [o["file"] for o in r["other_files_carry_main_lines"]]) for r in oc], ")")
sk = [r for r in R if r.get("other_files_scan")]
print("\nother-file scan skipped (mega-diffs):", len(sk), [r["number"] for r in sk])
union = {r["number"] for r in edits} | {r["number"] for r in nf} | {r["number"] for r in op}
print("\nA or B or C:", len(union), "| outside the #80636 stack:", len(union - STACK), sorted(union - STACK))
bt = collections.Counter(f for r in R for f in r.get("touches_branch_files", []))
print("PRs touching each file the branch touches:", dict(bt))
