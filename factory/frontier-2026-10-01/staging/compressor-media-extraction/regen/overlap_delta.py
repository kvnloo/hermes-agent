#!/usr/bin/env python3
"""Read-only: refresh an earlier overlap census against a new open-PR listing, re-analysing only
the PRs that may have changed.

    python3 overlap_delta.py plan  <earlier-census-raw.json> <earlier-listing-start-iso> <out-dir> seg*.jsonl
    OVERLAP_MAIN=<sha> python3 overlap_census.py <regen-dir> <out-dir>/census-delta.json <out-dir>/reanalyse.jsonl
    python3 overlap_delta.py merge <earlier-census-raw.json> <out-dir>

A census record depends on the PR's head commit, its own patch and main's facade text. When main's
facade blob is unchanged since the earlier census (the caller checks this), an earlier record still
stands if the PR has the recorded head, or (for records that kept no head) has not been updated at all
since the earlier listing began. Every other PR that touches the facade, or whose truncated file list
cannot be ruled out, goes to reanalyse.jsonl. Only GitHub reads happen in overlap_census.py; this
script reads local files only.
"""
import json, sys
from pathlib import Path

FACADE = "agent/context_compressor.py"
MEDIA = "agent/context_compressor_media.py"
STACK = {80636, 80645, 80644, 81074, 81181}


def load_listing(files):
    metas = {}
    for fn in files:
        for line in open(fn):
            m = json.loads(line)
            metas[m["number"]] = m
    return metas


def earlier(raw_path):
    d = json.load(open(raw_path))
    touch = set(d["touching_facade"])
    # the earlier receipt counted #42793 as touching (GraphQL lists the facade; REST returned no files)
    touch |= set(int(k) for k in d.get("not_analysed", {}) or {}) | {42793}
    flagged = {r["number"]: r for r in d["flagged"]}
    return d, touch, flagged


def plan(raw_path, start, out_dir, seg_files):
    d, touch, flagged = earlier(raw_path)
    metas = load_listing(seg_files)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    reuse, reanalyse, new_touch = [], [], []
    for n, m in sorted(metas.items()):
        files = m.get("files")
        paths = [x["path"] for x in files["nodes"]] if files else None
        complete = files is not None and not files["pageInfo"]["hasNextPage"]
        in_paths = bool(paths) and (FACADE in paths or MEDIA in paths)
        rec = flagged.get(n)
        unchanged = (rec["head"] == m["headRefOid"]) if rec and rec.get("head") else (m["updatedAt"] < start)
        if in_paths:
            touches = True
        elif complete:
            touches = False
        else:
            touches = (n in touch) if unchanged else None
        if touches is False:
            continue
        if touches and n in touch and unchanged:
            reuse.append(n)
            continue
        reanalyse.append(m)
        if n not in touch:
            new_touch.append(n)
    with open(out / "reanalyse.jsonl", "w") as fh:
        for m in reanalyse:
            fh.write(json.dumps(m) + "\n")
    open_now = set(metas)
    plan_d = {
        "earlier_main": d["main"], "earlier_listed_at": d["listed_at"], "earlier_open_prs_listed": d["open_prs_listed"],
        "earlier_touching": len(touch), "listing_start_used_for_reuse": start,
        "open_prs_listed_now": len(metas),
        "reused_unchanged": sorted(reuse),
        "reanalyse": sorted(m["number"] for m in reanalyse),
        "reanalyse_not_in_earlier_set": sorted(new_touch),
        "earlier_touching_no_longer_open": sorted(touch - open_now),
    }
    json.dump(plan_d, open(out / "plan.json", "w"), indent=1)
    print(f"listed now {len(metas)}; earlier touching {len(touch)}; reused {len(reuse)}; re-analyse {len(reanalyse)} "
          f"({len(new_touch)} not in earlier set); earlier touching no longer open {len(touch - open_now)}")


def merge(raw_path, out_dir):
    d, touch, flagged = earlier(raw_path)
    out = Path(out_dir)
    p = json.load(open(out / "plan.json"))
    delta = json.load(open(out / "census-delta.json"))
    recs = {}
    for n in p["reused_unchanged"]:
        recs[n] = dict(flagged[n], source="earlier census (unchanged head)") if n in flagged else \
            {"number": n, "touches_facade": True, "source": "earlier census (unchanged, not flagged)"}
        recs[n]["touches_facade"] = True
    for r in delta["records"]:
        r["source"] = "re-analysed"
        recs[r["number"]] = r
    fac = {n: r for n, r in recs.items() if r.get("touches_facade") or r.get("error")}
    A = sorted(n for n, r in fac.items() if r.get("edits_moved"))
    B = {n: r["new_facade_refs"] for n, r in fac.items() if r.get("new_facade_refs")}
    C = {n: r["other_files_new_old_path_refs"] for n, r in fac.items() if r.get("other_files_new_old_path_refs")}
    C_fail = sorted(n for n, v in C.items() if any(o["breaks_after_merge"] for o in v))
    kinds = {n: fac[n].get("kind") for n in fac}
    union = set(A) | set(B) | set(C)
    focused = sorted(n for n in union - STACK if kinds.get(n) == "focused" or
                     (kinds.get(n) is None and (fac[n].get("n_files") or 0) < 600))
    summary = {
        "open_prs_listed_now": p["open_prs_listed_now"],
        "touching_facade_now": len(fac),
        "touching_facade_numbers": sorted(fac),
        "errors": {n: r["error"] for n, r in fac.items() if r.get("error")},
        "reused_from_earlier": len(p["reused_unchanged"]),
        "re_analysed": len(delta["records"]),
        "re_analysed_touching": sorted(r["number"] for r in delta["records"] if r.get("touches_facade")),
        "earlier_touching_no_longer_open": p["earlier_touching_no_longer_open"],
        "A_edit_a_moved_statement": A,
        "A_outside_stack": sorted(set(A) - STACK),
        "B_new_facade_use_of_non_imported_moved_name": {str(k): v for k, v in sorted(B.items())},
        "C_new_old_path_reference_in_other_files": sorted(C),
        "C_would_fail_to_import": C_fail,
        "A_or_B_or_C": sorted(union),
        "A_or_B_or_C_outside_stack": sorted(union - STACK),
        "kind_of_each_flagged": {str(n): kinds.get(n) or f"unclassified ({fac[n].get('n_files')} files)" for n in sorted(union)},
        "focused_outside_stack": focused,
    }
    json.dump(summary, open(out / "summary.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "touching_facade_numbers"}, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "plan":
        plan(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
    elif sys.argv[1] == "merge":
        merge(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
