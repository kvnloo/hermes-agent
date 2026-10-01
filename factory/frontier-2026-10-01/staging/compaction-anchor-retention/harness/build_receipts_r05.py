#!/usr/bin/env python3
"""Build the round-5 receipts (r20261001-05) for staging/compaction-anchor-retention.

Round 5 moves the fold-in rows for #117462 to the end of that PR's table (after ``errors``), the
same placement as the standalone commit, so no line #117462 emits changes. Only the receipts that
measure the fold-in arm are rebuilt: E03p, E03s, F02s, T01 and AB117462. RG01 and N01 stay at
r20261001-03 (the standalone head and its rows did not change; N01 output is identical on both
fold-in orders, see raw/r05/coverage_foldin.json), N02 stays at r20261001-04.

Inputs (repo-relative, placeholders only, no local paths):
  raw/coverage.json                 round-3 run: base, branch, c117462, round-3 fold-in (key c117462_foldin), branch_r01, branch_r02
  raw/r05/coverage_foldin.json      round-5 run: c117462 (control), c117462_foldin (round-5 order), c117462_foldin_r03 (control)
  raw/r05/foldin_order_check.json   harness/foldin_order_check.py (synthetic + real-text line comparison vs #117462)
  raw/r05/index_cost.json           harness/index_cost.py (build time and per-row time, 7 reps)
  raw/r05/*.full                    test runs of the round-5 fold-in; raw/r05/negative_controls_foldin.json
  raw/ab_c117462_*.full, raw/ab_branch_*.full   round-3 runs of the unchanged arms
"""
import collections
import hashlib
import json
import statistics as st
from pathlib import Path

R = Path(__file__).resolve().parents[1]
RAW, OUT, R5 = R / "raw", R / "receipts", R / "raw" / "r05"
BASE = "040b6df2c40b0f4f88f51e4c2062eafc4d7463c5"
HEAD = "30a746f7920c2b4101f121353778d94f5ce001b5"
MAIN_NOW = "44a1ce9724502b9c692faaef00af3054bf11f1a6"      # main when the round-5 runs started (11:40-05:00)
MAIN_LATEST = "aaa863f7ff2dec1821be1652b5d15ad14ecea70b"   # main at the round-5 recheck (11:55-05:00)
TREE_117462_LATEST = "ee14a0acac817501f082ed8181aa5d471ea67986"
TREE_BRANCH_LATEST = "e2c14b39eefd2c90edfdd75e40baf91d82a017d1"
PR117462 = "2c19948e15d68492d048250bae7707ca77063db5"
TREE_117462 = "f4139cef66cd97f30f7fc450301551d233ebf616"
TREE_117462_NOW = "7beb2da24840f32329d5c5d47837fe52fef9e249"
PR122522 = "f596584b017694bf123d746a87740f58a2db15c1"
RID = "r20261001-05"
OLD_PATCH_SHA = "3713e44bbb4edfdbd493b80c290b013a3d26b3a21e88c734bd733f6fad3e9bf5"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


cov3 = json.loads((RAW / "coverage.json").read_text(encoding="utf-8"))
cov5 = json.loads((R5 / "coverage_foldin.json").read_text(encoding="utf-8"))
assert cov3["scorecard_sha256"] == cov5["scorecard_sha256"]
A = dict(cov3["arms"])
A["c117462_foldin_r03"] = A.pop("c117462_foldin")
A["c117462_foldin"] = cov5["arms"]["c117462_foldin"]


def strip_timing(a):
    a = dict(a)
    a.pop("timing_big_region", None)
    a.pop("T01_dot_chain", None)
    a["F02s"] = [{k: v for k, v in x.items() if k != "build_s"} for x in a["F02s"]]
    a["N01"] = {k: v for k, v in a["N01"].items() if k != "scan_s"}
    return a


reproduced = {
    "c117462_round5_run_equals_round3_run_apart_from_timings": strip_timing(cov5["arms"]["c117462"]) == strip_timing(cov3["arms"]["c117462"]),
    "round3_foldin_round5_run_equals_round3_run_apart_from_timings": strip_timing(cov5["arms"]["c117462_foldin_r03"]) == strip_timing(cov3["arms"]["c117462_foldin"]),
    "N01_identical_round5_vs_round3_foldin_order": strip_timing(cov5["arms"]["c117462_foldin"])["N01"] == strip_timing(cov3["arms"]["c117462_foldin"])["N01"],
}
assert all(reproduced.values()), reproduced
order = json.loads((R5 / "foldin_order_check.json").read_text(encoding="utf-8"))
assert order["coverage_sha256"] == sha(R5 / "coverage_foldin.json")
cost = json.loads((R5 / "index_cost.json").read_text(encoding="utf-8"))["arms"]
neg = json.loads((R5 / "negative_controls_foldin.json").read_text(encoding="utf-8"))

MAIN_ARMS = ("base", "branch", "c117462", "c117462_foldin")
common = {
    "schema": "xf.receipt.v1",
    "staging": "compaction-anchor-retention",
    "issue": None,
    "origin_refs": ["NousResearch/hermes-agent#116246", "NousResearch/hermes-agent#87326", "NousResearch/hermes-agent#117462",
                    "NousResearch/hermes-agent#122274", "NousResearch/hermes-agent#122522", "NousResearch/hermes-agent#78457"],
    "base_revision": BASE,
    "head_revision": HEAD,
    "main_recheck": {"sha": MAIN_LATEST, "note": (f"agent/context_compressor.py, hermes_cli/config_defaults.py and the 6 neighbouring test files are "
                                                  f"byte-identical on {BASE[:10]}, {MAIN_NOW[:10]} and {MAIN_LATEST[:10]}; main+#117462 merges clean on all three "
                                                  f"(trees {TREE_117462[:10]}, {TREE_117462_NOW[:10]}, {TREE_117462_LATEST[:10]}) and gives the same compressor file "
                                                  f"(the c117462 arm); the branch merges clean on {MAIN_LATEST[:10]} (tree {TREE_BRANCH_LATEST[:10]})")},
    "supersedes": "the r20261001-03 receipt of the same name (superseded-r04/receipts/), which measured the round-3 fold-in order",
    "policy_revision": {"factory": "FACTORY.md (frontier-2026-10-01)", "protocol": "promotion-readiness-2026-10-01/PROTOCOL.md"},
    "env": {"python": "3.11 (HERMES_PYTHON venv, read-only bind)",
            "sandbox": ("harness/sandbox.sh: bwrap ro-root, --unshare-net (connect -> ENETUNREACH), systemd-resolved socket "
                        "masked (DNS -> EAI_AGAIN), pidns, clearenv, live Hermes install masked except the venv, fresh "
                        "HOME/HERMES_HOME per run; harness/egress_sitecustomize.py logs every non-loopback DNS lookup and connect attempt"),
            "tests": "HOME=$S/testhome-sf3-compaction-anchor-retention HERMES_HOME=$HOME/.hermes HERMES_PYTHON=$PY bash scripts/run_tests.sh -j 2 <files> -q"},
    "provenance": "self",
    "ai_assistance": "Claude Code (Opus 5.5) wrote the rows, tests, harness, gold labels and this receipt; disclosed per repository policy",
    "privacy": "public-aggregate (inputs are committed upstream text or seeded synthetic data; no state.db, no lineages); no absolute local paths",
    "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0, "tokens": 0},
}
arms_block = {
    "base": {"tree": f"{BASE}:agent/context_compressor.py", "sha256": A["base"]["arm_file_sha256"]},
    "branch": {"head": HEAD, "sha256": A["branch"]["arm_file_sha256"]},
    "c117462": {"pr": 117462, "head": PR117462, "merge_tree_with_base": TREE_117462, "merge_tree_with_main_now": TREE_117462_NOW,
                "merge": "clean", "sha256": A["c117462"]["arm_file_sha256"]},
    "c117462_foldin": {"onto": "c117462", "patch": "foldin-on-117462.patch (rows + tests/agent/test_context_compressor_anchor_index.py)",
                       "patch_sha256": sha(R / "foldin-on-117462.patch"),
                       "placement": ("round 5: the three rows appended after 'errors', the last row of #117462's table; the rows block "
                                     "(rows and comments) is byte-identical to the standalone commit's"),
                       "sha256": A["c117462_foldin"]["arm_file_sha256"],
                       "equals": f"git apply foldin-on-117462.patch on main {MAIN_NOW[:10]} + #117462 (tree {TREE_117462_NOW[:10]}), offset +105"},
    "c117462_foldin_r03": {"onto": "c117462", "patch": f"superseded-r04/foldin-on-117462.patch (sha256 {OLD_PATCH_SHA})",
                           "placement": "round 3: 'task ids' after 'todo ids', 'dotted keys' before 'files', 'error messages' last",
                           "sha256": A["c117462_foldin_r03"]["arm_file_sha256"], "role": "comparison only (the order round 5 replaces)"},
}
harness = {n: sha(R / "harness" / n) for n in ("anchor_coverage.py", "foldin_order_check.py", "index_cost.py", "build_receipts_r05.py",
                                               "sandbox.sh", "egress_sitecustomize.py", "negative_controls.py")}
SANDBOX = "VENV=$VENV HERMES_INSTALL=<live install> EGRESS_DIR=<dir with sitecustomize.py> $SANDBOX $WT <fresh home on a non-/tmp disk> <egress log>"
cov_cmd = {
    "round5_foldin": (f"{SANDBOX} $PY $STAGING/harness/anchor_coverage.py --checkout $WT --arm c117462=raw/arms/c117462.py "
                      "--arm c117462_foldin=raw/arms/c117462_foldin.py --arm c117462_foldin_r03=raw/arms/c117462_foldin_r03.py "
                      "--seeds 10 --out <home>/coverage_r05.json   # $WT detached at HEAD; copied to raw/r05/coverage_foldin.json"),
    "round3_other_arms": ("the same harness with --arm base/branch/c117462/c117462_foldin(round-3 order)/branch_r01/branch_r02, "
                          "copied to raw/coverage.json (r20261001-03); its c117462_foldin key is read here as c117462_foldin_r03"),
}
cov_inputs = {"scorecard": "evals/compaction/results/SCORECARD-2026-08-15.md", "scorecard_sha256": cov5["scorecard_sha256"],
              "harness_sha256": harness, "arms": arms_block,
              "coverage_json_sha256": {"raw/coverage.json": sha(RAW / "coverage.json"), "raw/r05/coverage_foldin.json": sha(R5 / "coverage_foldin.json")},
              "reproduction_checks": reproduced,
              "checkout_for_imports": (f"$WT at {HEAD}; `git diff --name-only {BASE[:10]} {HEAD[:10]}` lists only "
                                       "agent/context_compressor.py and the new test file"),
              "egress": "0 attempts logged for every harness run (raw/r05/egress/ for round 5)"}


def write(name, body):
    body = {**common, **body}
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def summary(path):
    txt = Path(path).read_text(encoding="utf-8")
    return next(l for l in txt.splitlines() if "Summary:" in l).strip("= ").strip()


# ---------------------------------------------------------------- E03p
def e03p_table(arm):
    agg = collections.OrderedDict()
    for row in A[arm]["E03p"]:
        if not row["in_scope"]:
            continue
        g = agg.setdefault(row["class"], {"golds": 0, "reachable_raw": 0, "reachable_natural": 0, "lineages": set(), "lineages_unreached": set()})
        g["golds"] += 1
        g["lineages"].add(row["bank"].split("/")[0])
        full = row["raw_hit"] == row["raw_total"]
        g["reachable_raw"] += full
        if not full:
            g["lineages_unreached"].add(row["bank"].split("/")[0])
        g["reachable_natural"] += row.get("natural_hit", row["raw_hit"]) == row.get("natural_total", row["raw_total"])
    for g in agg.values():
        g["lineages"] = sorted(g["lineages"])
        g["lineages_unreached"] = sorted(g["lineages_unreached"])
    return agg


tables = {a: e03p_table(a) for a in MAIN_ARMS}
newly = []
for rb, rh in zip(A["base"]["E03p"], A["branch"]["E03p"]):
    if rb.get("raw_total") and rb["raw_hit"] < rb["raw_total"] and rh["raw_hit"] == rh["raw_total"]:
        newly.append({"bank": rb["bank"], "n": rb["n"], "class": rb["class"], "rows": rh["raw_rows"], "needle": rb["needles"][0][:70]})
err_new = [x for x in newly if x["class"] == "error_message"]
distinct_err = collections.Counter("Blocked: `git ...` would rewrite Hermes's live source checkout ..." if x["needle"].startswith("Blocked:")
                                   else x["needle"] for x in err_new)
tot = {a: {"in_scope": sum(t["golds"] for t in tables[a].values()),
           "reachable_raw": sum(t["reachable_raw"] for t in tables[a].values()),
           "reachable_natural": sum(t["reachable_natural"] for t in tables[a].values())} for a in MAIN_ARMS}
per_gold = lambda arm: [{k: r[k] for k in ("raw_hit", "natural_hit") if k in r} for r in A[arm]["E03p"]]  # noqa: E731
write("E03p-gold-reachability", {
    "id": f"E03p/{RID}",
    "kind": "static",
    "question": "Which identifier classes in the committed recall-exam gold answers can main's anchor rows capture at all, and which classes are missing?",
    "substitutes_for": "E03 (gold-identifier survival over reconstruct_lineage outputs from a LOCAL state.db copy); not runnable here: reading state.db is forbidden in this run and needs OD-7",
    "inputs": cov_inputs,
    "command": cov_cmd,
    "method": ("90 gold answers (6 banks x 15, lineages sweep/gui/prmerge/acp) parsed from the committed 08-15 scorecard; each hand-labelled "
               "by class (frozen LABELS table in the harness); 49 are identifier classes. A gold is reachable when every needle in it is "
               "contained in some value an anchor row extracts from the gold string itself (needles >100 chars compare on the first 100). "
               "'natural' re-tests 4 golds inside the line their emitter prints; that column is MODELED. Row order does not enter this "
               "measurement (each row is applied to the gold string alone)."),
    "measurements": [
        {"name": "identifier_golds_reachable_raw", "arm": a, "value": tot[a]["reachable_raw"], "n": tot[a]["in_scope"], "label": "OBSERVED"} for a in MAIN_ARMS
    ] + [
        {"name": "identifier_golds_reachable_in_emitter_line", "arm": a, "value": tot[a]["reachable_natural"], "n": tot[a]["in_scope"], "label": "MODELED"} for a in MAIN_ARMS
    ],
    "per_class": tables,
    "newly_reachable_on_branch": newly,
    "change_vs_r03": {"foldin_identical_per_gold_to_round3_order": per_gold("c117462_foldin") == per_gold("c117462_foldin_r03"),
                      "note": "round 5 only moves the fold-in rows within the table; reachability does not depend on order"},
    "in_sample_warning": {
        "circular": ("the rows were written after reading these same golds, so 24 -> 31 is an in-sample count, not a held-out estimate. "
                     "The 'GraphQL' and 'Blocked' alternatives of the error row exist because of these golds."),
        "error_line_gain": {"golds": len(err_new), "distinct_strings": len(distinct_err), "strings": dict(distinct_err)},
        "held_out_check": ("SCORECARD-2026-09-19-jev.md asks for coverage on its prreview/sysprompt/sigsegv banks; those banks and their golds "
                           "are not committed (jev-cycles-2026-09-19/*.json carry no golds), so that check was not run"),
    },
    "missing_class_evidence": {
        "error_message": {"golds": tables["base"]["error_message"]["golds"], "reachable_on_main": tables["base"]["error_message"]["reachable_raw"],
                          "lineages": tables["base"]["error_message"]["lineages_unreached"]},
        "task_id": {"golds": 1, "lineages": ["gui"], "plus": "maintainer statement (SCORECARD-2026-09-19-jev.md: 'delegation ids'), source-only"},
        "config_key": {"golds": 1, "lineages": ["prmerge"], "plus": "maintainer statement ('config keys'), source-only"},
        "env_var": {"golds": 0, "decision": "no row added (no evidence)"},
        "symbol": {"golds": tables["base"]["symbol"]["golds"], "lineages": tables["base"]["symbol"]["lineages_unreached"],
                   "decision": "largest residual unreachable class; not addressed"},
    },
    "limitations": ["reachability is an upper bound: it does not show the gold text was in the compacted region, nor that it survives caps/budget",
                    "labels are agent-assigned (not human-curated)", "in-sample: see in_sample_warning"],
    "verdict": "KEEP (unchanged numbers: main 24/49, branch 31/49, #117462 24/49, fold-in 31/49; in-sample)",
})


# ---------------------------------------------------------------- E03s
def e03s(arm):
    out = {}
    for dens in ("sparse", "medium", "dense"):
        rows = [x for x in A[arm]["E03s"] if x["density"] == dens]
        byc = collections.defaultdict(lambda: [0, 0])
        for x in rows:
            byc[x["class"]][0] += x["hit"]
            byc[x["class"]][1] += x["total"]
        new = ("error_message", "config_key", "task_id")
        allv = [sum(x["hit"] for x in rows), sum(x["total"] for x in rows)]
        newv = [sum(byc[c][0] for c in new), sum(byc[c][1] for c in new)]
        out[dens] = {"all": allv, "new_classes": newv, "existing_classes": [allv[0] - newv[0], allv[1] - newv[1]],
                     "per_class": {c: v for c, v in sorted(byc.items())}}
    return out


E = {a: e03s(a) for a in A}
write("E03s-synthetic-survival", {
    "id": f"E03s/{RID}",
    "kind": "sizing",
    "question": "If each identifier gold is mentioned once in assistant text inside a region of a given density, does it survive into the anchor index?",
    "inputs": cov_inputs, "command": cov_cmd,
    "method": ("seeded synthetic regions (DENSITIES in harness; 10 seeds x 6 banks x 3 densities = 180 regions per arm); each bank's identifier "
               "golds planted once on their own line in an assistant message (emitter line where defined); survival = needle substring of the "
               "real _build_anchor_index output. 'existing_classes' = needles of classes the current rows target (460 per density)."),
    "label": "MODELED",
    "results": E,
    "readout": [
        (f"sparse: branch and fold-in keep {E['branch']['sparse']['new_classes'][0]}/110 and {E['c117462_foldin']['sparse']['new_classes'][0]}/110 "
         f"new-class needles (main and #117462 {E['base']['sparse']['new_classes'][0]}/110)"),
        (f"medium: branch {E['branch']['medium']['new_classes'][0]}/110, fold-in {E['c117462_foldin']['medium']['new_classes'][0]}/110 "
         f"(round-3 order {E['c117462_foldin_r03']['medium']['new_classes'][0]}/110); error messages "
         f"{E['c117462_foldin']['medium']['per_class']['error_message'][0]}/90 on every arm"),
        (f"existing classes, #117462 vs fold-in: sparse {E['c117462']['sparse']['existing_classes'][0]} vs {E['c117462_foldin']['sparse']['existing_classes'][0]}, "
         f"medium {E['c117462']['medium']['existing_classes'][0]} vs {E['c117462_foldin']['medium']['existing_classes'][0]}, "
         f"dense {E['c117462']['dense']['existing_classes'][0]} vs {E['c117462_foldin']['dense']['existing_classes'][0]} (of 460 each): identical. "
         f"The round-3 order lost one in medium ({E['c117462_foldin_r03']['medium']['existing_classes'][0]}/460: "
         "\"ModuleNotFoundError: No module named 'hermes_cli.dashboard_auth'\", seed 1, which the shortened 'errors' line dropped)"),
        (f"dense: every arm keeps almost no once-mentioned needle (main {E['base']['dense']['all'][0]}/570, #117462 and fold-in "
         f"{E['c117462']['dense']['all'][0]}/570; new classes 0/110 on every arm, round-3 order included); frequency-first ranking plus the "
         "7,000-char budget is the binding limit"),
    ],
    "limitations": ["filler distributions are invented; real regions mention important identifiers more than once",
                    "no LLM summary text is included (index only)",
                    ("once-mentioned needles rank last in both fold-in orders, so this measure does not show the cost of appending: a new-class "
                     "value repeated often in a dense region is kept by the round-3 order and cut by the round-5 order (see F02s new_sections)")],
    "verdict": "PARTIAL (mechanism works where budget remains; the round-5 fold-in order keeps every #117462 needle and the same new-class survival as the round-3 order)",
})

# ---------------------------------------------------------------- F02s
f02 = {}
for a in MAIN_ARMS + ("c117462_foldin_r03",):
    f02[a] = {}
    for dens in ("sparse", "medium", "dense"):
        rows = [x for x in A[a]["F02s"] if x["density"] == dens]
        sc = [x["sections_chars"] for x in rows]
        ic = [x["index_chars"] for x in rows]
        labs = collections.Counter(l for x in rows for l in x["labels"])
        f02[a][dens] = {"n": len(rows), "sections_chars_max": max(sc), "sections_chars_p50": int(st.median(sc)),
                        "index_chars_max": max(ic), "index_tokens_max_chars_div_4": max(ic) // 4,
                        "over_budget": sum(1 for v in sc if v > A[a]["budget"]), "sections_emitted": dict(labs)}
    f02[a]["regions"] = sum(f02[a][d]["n"] for d in ("sparse", "medium", "dense"))
    f02[a]["index_chars_max"] = max(f02[a][d]["index_chars_max"] for d in ("sparse", "medium", "dense"))
    f02[a]["sections_chars_max"] = max(f02[a][d]["sections_chars_max"] for d in ("sparse", "medium", "dense"))


def key(x):
    return (x["density"], x["seed"], x["bank"])


b = {key(x): x["sections"] for x in A["base"]["F02s"]}
h = {key(x): x["sections"] for x in A["branch"]["F02s"]}
prefix_main = sum(1 for k in b if h[k][:len(b[k])] == b[k])
syn = order["synthetic"]
real = order["real_text"]
cost_block = {a: {"build_s_median": v["build_s_median"], "new_rows_s_median": v["new_row_s_median"], "new_rows_s_sum": v["new_rows_s_sum"]}
              for a, v in cost.items()}
write("F02s-budget-audit", {
    "id": f"F02s/{RID}",
    "kind": "static",
    "question": ("How large does the anchor index get with the new rows, and do the existing sections stay byte-identical, both on main "
                 "(standalone commit) and on #117462 (fold-in)?"),
    "substitutes_for": "F02 on frozen local lineages (needs OD-7)",
    "inputs": {**cov_inputs, "order_check_sha256": sha(R5 / "foldin_order_check.json"), "index_cost_sha256": sha(R5 / "index_cost.json"),
               "real_text_corpus": {"what": f"agent/*.py at {MAIN_NOW[:10]} (git archive), as read_file tool traffic", **order["corpus"]}},
    "command": {**cov_cmd,
                "order_check": (f"{SANDBOX} $PY $STAGING/harness/foldin_order_check.py --checkout $WT --coverage <round-5 coverage json> "
                                "--corpus <git archive of agent/ at main>/agent --arm c117462=... --arm c117462_foldin=... "
                                "--arm c117462_foldin_r03=... --out <home>/order.json   # copied to raw/r05/foldin_order_check.json"),
                "index_cost": (f"{SANDBOX} $PY $STAGING/harness/index_cost.py --checkout $WT --arm base=... --arm branch=... "
                               "--arm c117462=... --arm c117462_foldin=... --out <home>/cost.json   # copied to raw/r05/index_cost.json")},
    "measurements": [
        {"name": "branch_index_chars_max", "arm": "branch", "value": f02["branch"]["index_chars_max"], "n": f02["branch"]["regions"], "label": "OBSERVED"},
        {"name": "branch_sections_chars_max", "arm": "branch", "value": f02["branch"]["sections_chars_max"], "n": f02["branch"]["regions"], "label": "OBSERVED"},
        {"name": "branch_index_tokens_max", "arm": "branch", "value": f02["branch"]["index_chars_max"] // 4, "label": "MODELED",
         "note": "chars/4; vs RETAINED_SUMMARY_TOKEN_BUDGET=32000 (agent/native_compaction.py:146)"},
        {"name": "main_sections_prefix_of_branch_sections", "value": prefix_main, "n": len(b), "label": "OBSERVED",
         "note": "standalone commit on main: existing lines byte-identical"},
        {"name": "117462_sections_prefix_of_foldin_sections", "arm": "c117462_foldin", "value": syn["c117462_foldin"]["carrier_lines_prefix"],
         "n": syn["c117462_foldin"]["regions"], "label": "OBSERVED", "note": "round-5 fold-in on #117462: every #117462 line byte-identical"},
        {"name": "117462_sections_prefix_of_foldin_sections", "arm": "c117462_foldin_r03", "value": syn["c117462_foldin_r03"]["carrier_lines_prefix"],
         "n": syn["c117462_foldin_r03"]["regions"], "label": "OBSERVED",
         "note": f"round-3 order: a #117462 line changed in {syn['c117462_foldin_r03']['regions_with_a_carrier_line_changed']} of 180 regions"},
        {"name": "real_text_117462_lines_unchanged", "arm": "c117462_foldin",
         "value": sum(1 for v in real["c117462_foldin"].values() if v["prefix"]), "n": len(real["c117462_foldin"]), "label": "OBSERVED",
         "note": "regions of 40, 120 and 251 agent/*.py files as read_file traffic"},
    ] + [{"name": "index_chars_max", "arm": a, "value": f02[a]["index_chars_max"], "n": f02[a]["regions"], "label": "OBSERVED"} for a in MAIN_ARMS],
    "per_arm": f02,
    "foldin_order": {
        "synthetic": syn,
        "real_text": real,
        "readout": [
            ("round 5 (rows after 'errors'): no #117462 line changes in 180 of 180 synthetic regions and in 3 of 3 real-text regions; "
             "the new sections only get the room #117462's own sections leave"),
            (f"round 3 (task ids after todo ids, dotted keys before files): dense 'files' cut from a median "
             f"{syn['c117462_foldin_r03']['per_density']['dense']['carrier_lines_changed']['files']['carrier_len_p50']} chars to the bare label in "
             f"{syn['c117462_foldin_r03']['per_density']['dense']['carrier_lines_changed']['files']['cut_to_bare_label']} of 60 dense regions "
             f"and removed in {syn['c117462_foldin_r03']['per_density']['dense']['carrier_lines_changed']['files']['label_removed']} "
             f"(changed in {syn['c117462_foldin_r03']['per_density']['dense']['carrier_lines_changed']['files']['regions_changed']} of 60); "
             f"medium 'errors' shorter in {syn['c117462_foldin_r03']['per_density']['medium']['carrier_lines_changed']['errors']['regions_changed']} of 60; "
             f"real text: 'errors' {real['c117462_foldin_r03']['40']['changed']['errors'][0]} -> {real['c117462_foldin_r03']['40']['changed']['errors'][1]} chars "
             f"(40 files), {real['c117462_foldin_r03']['120']['changed']['errors'][0]} -> {real['c117462_foldin_r03']['120']['changed']['errors'][1]} (120 files), "
             f"while 'dotted keys' took {real['c117462_foldin_r03']['40']['new_lens']['dotted keys']}-{real['c117462_foldin_r03']['251']['new_lens']['dotted keys']} chars "
             "of attribute access"),
            ("the trade round 5 keeps: in dense synthetic regions 'task ids' is emitted in "
             f"{syn['c117462_foldin']['per_density']['dense']['new_sections']['task ids']['emitted_in']} of 60 "
             f"({syn['c117462_foldin']['per_density']['dense']['new_sections']['task ids']['bare_label']} as a bare label), 'dotted keys' in "
             f"{syn['c117462_foldin']['per_density']['dense']['new_sections']['dotted keys']['emitted_in']} of 60 (bare), 'error messages' in "
             f"{syn['c117462_foldin']['per_density']['dense']['new_sections']['error messages']['emitted_in']} of 60; in medium regions "
             f"'error messages' is emitted in {syn['c117462_foldin']['per_density']['medium']['new_sections']['error messages']['emitted_in']} of 60 "
             f"({syn['c117462_foldin']['per_density']['medium']['new_sections']['error messages']['bare_label']} bare); in the real-text regions only "
             f"'dotted keys' gets room ({real['c117462_foldin']['40']['new_lens'].get('dotted keys')}-{real['c117462_foldin']['120']['new_lens'].get('dotted keys')} chars). "
             "The round-3 order emitted these sections in every dense region, at #117462's expense"),
        ],
    },
    "build_cost_443k_char_region": {
        "per_arm": cost_block,
        "readout": (f"the three rows' patterns take about {cost['c117462_foldin']['new_rows_s_sum']} s together on this region wherever they run. "
                    f"#117462 has no break, so its build goes from {cost['c117462']['build_s_median']} s to {cost['c117462_foldin']['build_s_median']} s "
                    f"(median of 7). On main the loop stops at 'errors', the first section that does not fit on this region, before reaching the rows, so main and branch both take "
                    f"about {cost['base']['build_s_median']} s here; on regions where every section fits, main pays the same per-row cost"),
        "label": "OBSERVED (single host, shared; order of magnitude only)",
    },
    "structural_note": ("over-budget counts are 0 on every arm BY CONSTRUCTION, not as a finding: main's loop only appends a section while "
                        "used + len(line) <= 7000 and #117462 truncates a section to the room left"),
    "not_measured": ["whole-summary tokens on real lineages (LLM output): NOT_MEASURED; the index adds at most about 1.8k tokens (MODELED)",
                     "placement is measured here, not pinned by a unit test"],
    "verdict": "KEEP",
})

# ---------------------------------------------------------------- T01
T_ARMS = ("base", "branch", "branch_r02", "c117462", "c117462_foldin")
t01 = {a: A[a]["T01_dot_chain"] for a in T_ARMS}
write("T01-dot-chain-cost", {
    "id": f"T01/{RID}",
    "kind": "static",
    "question": "Does the dotted-keys row add super-linear regex cost on adversarial tool output (one long unbroken lowercase dot chain)?",
    "inputs": cov_inputs, "command": cov_cmd,
    "method": ("one tool message whose content is 'a.' * n; wall time of the arm's whole _build_anchor_index, of each row alone on n = 20,000, "
               "and of the 'dotted keys' row alone up to n = 100,000. Single runs on a shared host. The fold-in arm is the round-5 run; "
               "the other arms are the round-3 run (unchanged files)."),
    "label": "OBSERVED",
    "results": t01,
    "readout": [
        (f"dotted keys row alone on 'a.'*20000: branch {t01['branch']['dotted_keys_row_s']['a.x20000']} s, round-2 row "
         f"{t01['branch_r02']['dotted_keys_row_s']['a.x20000']} s; branch on 'a.'*100000: {t01['branch']['dotted_keys_row_s']['a.x100000']} s (linear)"),
        (f"whole index on 'a.'*20000: main {t01['base']['index_s']['a.x20000']} s, branch {t01['branch']['index_s']['a.x20000']} s; "
         f"main's cost is its existing 'files' row ({t01['base']['per_row_s_a.x20000']['files']} s alone)"),
        (f"#117462 arm {t01['c117462']['index_s']['a.x20000']} s, fold-in {t01['c117462_foldin']['index_s']['a.x20000']} s, fold-in dotted keys row "
         f"{t01['c117462_foldin']['dotted_keys_row_s']['a.x20000']} s on 'a.'*20000"),
    ],
    "verdict": "KEEP (row order does not change regex cost; the fold-in row is linear)",
})

# ---------------------------------------------------------------- AB117462
write("AB117462-carrier-compat", {
    "id": f"AB117462/{RID}",
    "kind": "carrier-ab",
    "question": "Is this slice duplicated by the open #117462, does the fold-in compose with it, and does the fold-in leave #117462's own lines unchanged?",
    "inputs": {"arms": {k: v for k, v in arms_block.items()},
               "tests": {"ours": "tests/agent/test_context_compressor_anchor_index.py",
                         "theirs": f"tests/agent/test_context_compressor_anchor_harvest.py @ {PR117462}"}},
    "command": {
        "foldin": (f"worktree at {MAIN_NOW[:10]}; git restore --source={TREE_117462_NOW[:10]} (main+#117462); git apply foldin-on-117462.patch "
                   "(offset +105); run ours, theirs and the 8 adjacent files with run_tests.sh"),
        "117462_head": f"worktree at {PR117462[:10]}; git apply foldin-on-117462.patch (no offset); run both test files",
        "negative_controls": f"in the {PR117462[:10]} worktree with the patch applied: TESTHOME=... HERMES_PYTHON=$PY $PY $STAGING/harness/negative_controls.py <out>",
        "other_arms": "round 3 (unchanged arm files): in $WT at HEAD, copy each arm over agent/context_compressor.py plus #117462's test file; run both",
    },
    "matrix": {
        "c117462": {"ours": summary(RAW / "ab_c117462_ours.full"), "theirs": summary(RAW / "ab_c117462_theirs.full"), "run": "round 3"},
        "c117462_foldin": {"ours": summary(R5 / "ab_c117462_foldin_ours.full"), "theirs": summary(R5 / "ab_c117462_foldin_theirs.full"),
                           "adjacent_8_files": summary(R5 / "adjacent_foldin.full"), "run": f"round 5, on main {MAIN_NOW[:10]} + #117462 + patch",
                           "adjacent_8_files_on_latest_main": summary(R5 / "adjacent_foldin_main_aaa863f7ff.full"),
                           "latest_main_run": f"round 5, on main {MAIN_LATEST[:10]} + #117462 (tree {TREE_117462_LATEST[:10]}) + patch (offset +105); compressor file byte-identical to the arm"},
        "117462_head_plus_foldin_patch": {"both_files": summary(R5 / "ab_117462head_foldin_both.full"), "run": "round 5"},
        "branch": {"ours": summary(RAW / "ab_branch_ours.full"), "theirs": summary(RAW / "ab_branch_theirs.full"), "run": "round 3",
                   "theirs_failing": ["test_anchor_index_cheap_ids_survive_a_tight_budget", "test_anchor_index_harvests_tool_call_arguments_and_artifact_paths",
                                      "test_anchor_index_names_a_class_whose_values_cannot_fit"]},
    },
    "foldin_negative_controls": {"result": f"{sum(1 for x in neg if x['failed'])}/{len(neg)} re-RED on {PR117462[:10]} + patch",
                                 "per_mutation": [{"mutation": x["mutation"], "observed": x["summary"], "failed": x["failed"]} for x in neg]},
    "placement": {"rows": "appended after 'errors' (round 5), the same block and position as the standalone commit",
                  "117462_lines_unchanged": {"synthetic": f"{syn['c117462_foldin']['carrier_lines_prefix']}/180",
                                             "real_text": f"{sum(1 for v in real['c117462_foldin'].values() if v['prefix'])}/3"},
                  "round3_order_for_comparison": f"a #117462 line changed in {syn['c117462_foldin_r03']['regions_with_a_carrier_line_changed']} of 180 synthetic regions (see F02s foldin_order)"},
    "merge": {"117462_vs_main": f"clean ({BASE[:10]}: tree {TREE_117462[:10]}; {MAIN_NOW[:10]}: tree {TREE_117462_NOW[:10]}; {MAIN_LATEST[:10]}: tree {TREE_117462_LATEST[:10]})",
              "branch_vs_main": f"clean ({MAIN_LATEST[:10]}: tree {TREE_BRANCH_LATEST[:10]})",
              "branch_vs_117462_head": "conflict in agent/context_compressor.py (both edit the _ANCHOR_PATTERNS table)",
              "foldin_patch_applies_to_117462_head": "yes, exactly (git apply, no offset); both test files pass there",
              "foldin_patch_applies_to_main_plus_117462": (f"yes on {MAIN_NOW[:10]} + #117462 (offset +105); the result is byte-identical to the "
                                                           "c117462_foldin arm file"),
              "branch_vs_122522_head": f"clean ({PR122522[:10]})"},
    "pr_state_read_only": {"117462": "OPEN, head 2c19948e15, 0 formal reviews, 2 issue comments (kyssta-exe's review-style comment and Seldash's reply)",
                           "122522": "OPEN, head f596584b01"},
    "label": "OBSERVED",
    "readout": ("not a duplicate: #117462 does not capture these classes (our tests 0 of 2 pass on it) and this slice does not do its work "
                "(3 of its 5 tests fail on our branch); the round-5 fold-in passes both suites (2 of 2 and 5 of 5) and the 8-file "
                "adjacent suite, and leaves every #117462 line unchanged"),
    "verdict": "KEEP (complementary; offered to #117462 as a fold-in appended after its last row)",
})
print("written:", sorted(p.name for p in OUT.iterdir()))
