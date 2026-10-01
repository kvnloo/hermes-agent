#!/usr/bin/env python3
"""Build xf.receipt.v1-shaped receipts for staging/compaction-anchor-retention from raw outputs."""
import collections
import hashlib
import json
import statistics as st
from pathlib import Path

R = Path("$STAGING")
RAW, OUT = R / "raw", R / "receipts"
OUT.mkdir(exist_ok=True)
S = "$S"
W = "$WT"
BASE = "234badf4012af380d23c91eae55d045a69c69ffb"
BASE0 = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0"
HEAD = "6e0fa629a0f6227b03417d1d6ff7f7d81208346a"
PR117462 = "2c19948e15d68492d048250bae7707ca77063db5"
TREE_117462 = "8dfb180bae5909ccd06f79f7268885f3309c9af6"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


cov = json.loads((RAW / "coverage.json").read_text())
A = cov["arms"]
arm_files = {k: str(RAW / "arms" / f"{k}.py") for k in A}
common = {
    "schema": "xf.receipt.v1",
    "staging": "compaction-anchor-retention",
    "issue": None,
    "origin_refs": ["NousResearch#87326", "NousResearch#117462", "NousResearch#122274", "NousResearch#122522", "NousResearch#78457"],
    "base_revision": BASE,
    "head_revision": HEAD,
    "policy_revision": {"factory": "FACTORY.md (frontier-2026-10-01)", "protocol": "promotion-readiness-2026-10-01/PROTOCOL.md"},
    "env": {"host": "<local-host>", "python": "3.11.14 (HERMES_PYTHON venv, read-only bind)",
            "sandbox": "bwrap ro-root, --unshare-net (connect 1.1.1.1:443 -> ENETUNREACH), pidns, clearenv, "
                       "$HERMES_INSTALL masked except venv, isolated HOME/HERMES_HOME"},
    "provenance": "self",
    "ai_assistance": "Claude Code (Opus 5.5) wrote the rows, tests, harness and gold labels; disclosed per repository policy",
    "privacy": "public-aggregate (all inputs are committed upstream text or seeded synthetic data; no state.db, no lineages)",
    "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0, "tokens": 0},
}
arms_block = {
    "base": {"tree": f"{BASE}:agent/context_compressor.py", "sha256": A["base"]["arm_file_sha256"]},
    "branch": {"head": HEAD, "sha256": A["branch"]["arm_file_sha256"]},
    "c117462": {"pr": 117462, "head": PR117462, "merge_tree": TREE_117462, "merge": "clean", "sha256": A["c117462"]["arm_file_sha256"]},
    "c117462_foldin": {"onto": "c117462", "patch": "foldin-on-117462.patch", "patch_sha256": sha(R / "foldin-on-117462.patch"),
                        "merge": "handported (rows placed in #117462's cheap-first order)", "sha256": A["c117462_foldin"]["arm_file_sha256"]},
}
harness = {"anchor_coverage.py": sha(R / "harness" / "anchor_coverage.py"), "build_receipts.py": sha(R / "harness" / "build_receipts.py")}
cov_cmd = (f"{S}/car_sandbox.sh {W} $VENV/bin/python {R}/harness/anchor_coverage.py "
           f"--checkout {W} --arm base={RAW}/arms/base.py --arm branch={RAW}/arms/branch.py "
           f"--arm c117462={RAW}/arms/c117462.py --arm c117462_foldin={RAW}/arms/c117462_foldin.py --seeds 10 "
           f"--out {RAW}/sbhome/coverage.json  # then moved to raw/coverage.json")
cov_inputs = {"scorecard": "evals/compaction/results/SCORECARD-2026-08-15.md", "scorecard_sha256": cov["scorecard_sha256"],
              "harness_sha256": harness, "arms": arms_block, "coverage_json_sha256": sha(RAW / "coverage.json"),
              "checkout_tree_for_imports": BASE0 + " (agent/* other than context_compressor.py identical to " + BASE + ")"}


def write(name, body):
    body = {**common, **body}
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n")
    return p


# ---------------------------------------------------------------- RG01: red/green proof
rg = {
    "id": "RG01/r20261001-01",
    "kind": "redgreen",
    "question": "Does main's anchor index capture delegation/kanban task ids, dotted config keys and CLI error lines, and do the three new rows fix that without disturbing neighbours?",
    "inputs": {"test": "tests/agent/test_context_compressor_anchor_index.py", "production_seam": "agent/context_compressor.py::_build_anchor_index / _ANCHOR_PATTERNS",
               "branch_patch_sha256": sha(R / "compaction-anchor-retention.patch")},
    "commands": {
        "tests": "HOME=$S/testhome-st-compaction-anchor-retention HERMES_HOME=$HOME/.hermes HERMES_PYTHON=$VENV/bin/python bash scripts/run_tests.sh -j 2 <files> -q",
        "red": "git show HEAD~1:agent/context_compressor.py > agent/context_compressor.py; run tests/agent/test_context_compressor_anchor_index.py; git checkout -- agent/context_compressor.py",
        "negative_controls": "delete one new row at a time (and a precision sabotage of the dotted-keys regex), rerun the test file, restore",
        "guards": "car_sandbox.sh <wt> $PY evals/compaction/test_region_scoping.py ; car_sandbox.sh <wt> $PY evals/token_accounting/replay_gates.py --out <json>",
    },
    "gates": {
        "red": {"arm": f"base {BASE} (and {BASE0})", "result": "PASS", "observed": "2 failed / 2",
                "assertion": "AssertionError: 'sa-2-7318d0ba' missing from anchor index / assert 'compression.tail_mode' in ''", "label": "OBSERVED"},
        "green": [{"arm": f"branch {HEAD}", "result": "PASS", "reps_agree": "3/3", "observed": "2 passed / 2", "label": "OBSERVED"}],
        "sabotage": {"per_hunk": [
            {"mutation": "drop row 'task ids'", "red_again": True, "observed": "2 failed"},
            {"mutation": "drop row 'dotted keys'", "red_again": True, "observed": "2 failed"},
            {"mutation": "drop row 'error messages'", "red_again": True, "observed": "2 failed"},
            {"mutation": "dotted-keys last segment no longer needs '_'", "red_again": True, "observed": "1 failed (config.yaml / context_compressor.py / api.openai.com leak)"},
        ], "unpinned_hunks": [], "label": "OBSERVED"},
        "adjacent": {"files": ["tests/agent/test_context_compressor.py", "tests/agent/test_lean_single_aux_call.py",
                               "tests/agent/test_compression_rotation_state.py", "tests/agent/test_context_compressor_summary_continuity.py",
                               "tests/agent/test_compaction_redaction_boundaries.py", "tests/agent/test_native_compaction_summary_retention.py"],
                     "base": "365 passed / 0 failed (6 files)", "arm": "365 passed + 2 new = 367 passed / 0 failed (7 files)",
                     "identical": True, "pre_existing_failures": [], "label": "OBSERVED"},
        "guards": {"evals/compaction/test_region_scoping.py": "ALL PASS on base and head (legacy + lean)",
                   "evals/token_accounting/replay_gates.py": "11/11 PASS on base and head; full result dict equal apart from compressor_sha256",
                   "files_unchanged": True, "egress_attempts_blocked": "1 per region_scoping run (model-metadata fetch to openrouter.ai, ENETUNREACH in sandbox; same on base)",
                   "label": "OBSERVED"},
        "flaky": False,
        "route_scope": "local-compressor (lean tail mode only; _augment_summary_lean is a no-op in legacy mode; native summaries are opaque)",
        "cache_read_ratio": {"status": "N_A", "why": "rows change summary text only at a compaction event, which already breaks the prompt cache; cadence unchanged"},
    },
    "denominators": {"cells": 3 + 1 + 4 + 4, "errored_scored_zero": 0, "infra_excluded": 0, "completeness": 1.0},
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
    "not_tested": ["recall exam (E04/E05): needs an aux LLM", "real lineages (state.db copies) — forbidden here / OD-7", "native compaction routes"],
    "verdict": "KEEP",
    "raw": {"red": "raw/final_red.txt", "green": ["raw/final_green_1.txt", "raw/final_green_2.txt", "raw/final_green_3.txt"],
            "negative_controls": "raw/negative_controls.txt", "adjacent": ["raw/adjacent_base.txt", "raw/final_adjacent_head.txt"],
            "guards": ["raw/region_scoping_base.txt", "raw/final_region_scoping_head.txt", "raw/replay_gates_base.json", "raw/final_replay_gates_head.json"]},
}
write("RG01-redgreen", rg)

# ---------------------------------------------------------------- E03p: gold reachability
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


tables = {a: e03p_table(a) for a in A}
newly = []
for rb, rh in zip(A["base"]["E03p"], A["branch"]["E03p"]):
    if rb.get("raw_total") and rb["raw_hit"] < rb["raw_total"] and rh["raw_hit"] == rh["raw_total"]:
        newly.append({"bank": rb["bank"], "n": rb["n"], "class": rb["class"], "rows": rh["raw_rows"]})
tot = {a: {"in_scope": sum(t["golds"] for t in tables[a].values()),
           "reachable_raw": sum(t["reachable_raw"] for t in tables[a].values()),
           "reachable_natural": sum(t["reachable_natural"] for t in tables[a].values())} for a in A}
write("E03p-gold-reachability", {
    "id": "E03p/r20261001-01",
    "kind": "static",
    "question": "Which identifier classes in the committed recall-exam gold answers can main's anchor rows capture at all, and which classes are missing?",
    "substitutes_for": "E03 (gold-identifier survival over reconstruct_lineage outputs from a LOCAL state.db copy) — not runnable here: reading state.db is forbidden in this run and needs OD-7",
    "inputs": cov_inputs,
    "command": cov_cmd,
    "method": ("90 gold answers (6 banks x 15, lineages sweep/gui/prmerge/acp) parsed from the committed scorecard; each hand-labelled "
               "by class (frozen LABELS table in the harness); 49 are identifier classes. A gold is reachable when every needle in it is "
               "contained in some value an anchor row extracts from the gold string itself (needles >100 chars compare on the first 100). "
               "'natural' re-tests 4 golds inside the line their emitter prints (gh 'GraphQL: ', tsc 'error TS2741: ', GNU as 'Fatal error: ', "
               "'PR #82980') — that column is MODELED."),
    "measurements": [
        {"name": "identifier_golds_reachable_raw", "arm": a, "value": tot[a]["reachable_raw"], "n": tot[a]["in_scope"], "label": "OBSERVED"} for a in A
    ] + [
        {"name": "identifier_golds_reachable_in_emitter_line", "arm": a, "value": tot[a]["reachable_natural"], "n": tot[a]["in_scope"], "label": "MODELED"} for a in A
    ],
    "per_class": tables,
    "newly_reachable_on_branch": newly,
    "missing_class_evidence": {
        "error_message": {"golds": tables["base"]["error_message"]["golds"], "reachable_on_main": tables["base"]["error_message"]["reachable_raw"],
                           "lineages": tables["base"]["error_message"]["lineages_unreached"], "gate_3_lineages": len(tables["base"]["error_message"]["lineages_unreached"]) >= 3},
        "task_id": {"golds": 1, "lineages": ["gui"], "plus": "maintainer statement (SCORECARD-2026-09-19-jev.md: 'delegation ids') — source-only"},
        "config_key": {"golds": 1, "lineages": ["prmerge"], "plus": "maintainer statement ('config keys') — source-only"},
        "env_var": {"golds": 0, "decision": "no row added (no evidence)"},
        "symbol": {"golds": tables["base"]["symbol"]["golds"], "lineages": tables["base"]["symbol"]["lineages_unreached"],
                   "decision": "largest residual unreachable class; not addressed (a bare snake/camel identifier row would be dominated by frequent code tokens)"},
    },
    "limitations": ["reachability is an upper bound: it does not show the gold text was in the compacted region, nor that it survives caps/budget",
                    "labels are agent-assigned (not human-curated); value claims need the human-curated exam",
                    "the 09-19 banks (prreview/sysprompt/sigsegv) are not committed, so the classes the maintainer named there are not counted"],
    "verdict": "KEEP (missing classes confirmed: error messages on 3 lineages; task id and config key on 1 each)",
    "learning": {"hypothesis": "classes named in SCORECARD-2026-09-19 are absent from _ANCHOR_PATTERNS", "result": "confirmed for error lines, subagent ids, dotted config keys; env vars unevidenced; symbols are the larger residual"},
})

# ---------------------------------------------------------------- E03s / F02s
def e03s(arm):
    out = {}
    for dens in ("sparse", "medium", "dense"):
        rows = [x for x in A[arm]["E03s"] if x["density"] == dens]
        byc = collections.defaultdict(lambda: [0, 0])
        for x in rows:
            byc[x["class"]][0] += x["hit"]
            byc[x["class"]][1] += x["total"]
        new = [c for c in ("error_message", "config_key", "task_id")]
        out[dens] = {"all": [sum(x["hit"] for x in rows), sum(x["total"] for x in rows)],
                     "new_classes": [sum(byc[c][0] for c in new), sum(byc[c][1] for c in new)],
                     "per_class": {c: v for c, v in sorted(byc.items())}}
    return out


write("E03s-synthetic-survival", {
    "id": "E03s/r20261001-01",
    "kind": "sizing",
    "question": "If each identifier gold is mentioned once in assistant text inside a region of a given density, does it survive into the anchor index?",
    "inputs": cov_inputs, "command": cov_cmd,
    "method": "seeded synthetic regions (DENSITIES in harness; 10 seeds x 6 banks x 3 densities = 180 regions per arm); each bank's identifier golds planted once on their own line in an assistant message (emitter line where defined); survival = needle substring of the real _build_anchor_index output",
    "label": "MODELED",
    "results": {a: e03s(a) for a in A},
    "readout": [
        "sparse: branch and fold-in keep 100/110 new-class needles (main 0/110); the miss is 'Hermes backend exited (0)', which no row targets",
        "medium: main-only branch keeps 17/110 (rows are appended last, so they only get leftover budget; error messages 0/90), fold-in 20/110 (task ids and dotted keys 20/20, error messages still 0/90)",
        "dense: every arm loses almost all once-mentioned needles of every class (main 13/570, #117462 25/570); frequency-first ranking plus the 7,000-char budget, not the row set, is the binding limit",
    ],
    "limitations": ["filler distributions are invented; real regions mention important identifiers more than once", "no LLM summary text is included (index only)"],
    "verdict": "PARTIAL (mechanism works where budget remains; full effect on main needs #117462's per-section truncation; dense regions are bounded by ranking)",
})

f02 = {}
for a in A:
    f02[a] = {}
    for dens in ("sparse", "medium", "dense"):
        rows = [x for x in A[a]["F02s"] if x["density"] == dens]
        sc = [x["sections_chars"] for x in rows]
        ic = [x["index_chars"] for x in rows]
        labs = collections.Counter(l for x in rows for l in x["labels"])
        f02[a][dens] = {"n": len(rows), "sections_chars_max": max(sc), "sections_chars_p50": int(st.median(sc)),
                        "index_chars_max": max(ic), "index_tokens_max_chars_div_4": max(ic) // 4,
                        "over_budget": sum(1 for v in sc if v > A[a]["budget"]), "sections_emitted": dict(labs)}
    f02[a]["timing_443k_char_region_s"] = A[a]["timing_big_region"]["build_s"]


def key(x):
    return (x["density"], x["seed"], x["bank"])


b = {key(x): x["sections"] for x in A["base"]["F02s"]}
h = {key(x): x["sections"] for x in A["branch"]["F02s"]}
prefix_ok = sum(1 for k in b if h[k][:len(b[k])] == b[k])
write("F02s-budget-audit", {
    "id": "F02s/r20261001-01",
    "kind": "static",
    "question": "Do the new rows keep the anchor index within _LEAN_ANCHOR_BUDGET_CHARS=7000 and far under the 32k-token native retained-summary budget, and do they leave main's existing sections untouched?",
    "substitutes_for": "F02 on frozen local lineages (needs OD-7)",
    "inputs": cov_inputs, "command": cov_cmd,
    "measurements": [
        {"name": "regions_over_budget", "value": sum(f02[a][d]["over_budget"] for a in A for d in ("sparse", "medium", "dense")), "n": 720, "label": "OBSERVED", "note": "4 arms x 180 synthetic regions"},
        {"name": "index_chars_max_any_arm", "value": max(f02[a][d]["index_chars_max"] for a in A for d in ("sparse", "medium", "dense")), "label": "OBSERVED"},
        {"name": "index_tokens_max_any_arm", "value": max(f02[a][d]["index_tokens_max_chars_div_4"] for a in A for d in ("sparse", "medium", "dense")), "label": "MODELED", "note": "chars/4, the harness convention; vs RETAINED_SUMMARY_TOKEN_BUDGET=32000 (native_compaction.py:146)"},
        {"name": "base_sections_prefix_of_branch_sections", "value": prefix_ok, "n": len(b), "label": "OBSERVED", "note": "strict additivity on main: existing lines byte-identical"},
    ],
    "per_arm": f02,
    "structural_note": "the loop only appends a section while used + len(line) <= budget (main) or truncates it to the room left (#117462), so sections never exceed 7000 chars whatever rows exist; heading, separators and footer add < 200 chars",
    "not_measured": ["whole-summary tokens on real lineages (LLM output) — NOT_MEASURED; the index adds at most ~1.8k tokens (MODELED)"],
    "verdict": "KEEP",
})

# ---------------------------------------------------------------- N01: noise audit
n01 = {a: {lab: A[a]["N01"].get(lab) for lab in ("task ids", "dotted keys", "error messages") if A[a]["N01"].get(lab)} for a in ("branch",)}
write("N01-noise-audit", {
    "id": "N01/r20261001-01",
    "kind": "static",
    "question": "What do the three new rows capture on a large public Hermes text corpus?",
    "inputs": {**cov_inputs, "corpus": "AGENTS.md + website/docs/**/*.md at " + BASE0, "corpus_files": A["branch"]["N01"]["corpus_files"],
               "corpus_chars": A["branch"]["N01"]["corpus_chars"], "corpus_sha256": A["branch"]["N01"]["corpus_sha256"],
               "default_config_keys": A["branch"]["N01"]["default_config_keys"]},
    "command": cov_cmd,
    "results": n01["branch"],
    "scan_seconds": {a: A[a]["N01"]["scan_s"] for a in A},
    "readout": [
        "task ids: 4 matches / 2 distinct in 7.8M chars (both doc examples): effectively noise-free",
        "dotted keys: 1032 distinct values, 306 (29.7%) are DEFAULT_CONFIG keys; the 15 most frequent are all real dotted identifiers (plugin API calls like ctx.register_hook, config keys like gateway.multiplex_profiles) — hence the label 'dotted keys', not 'config keys'",
        "error messages: 24 matches; in docs these are mostly prose/table fragments that start with 'error:' — transcripts carry real CLI output instead",
    ],
    "label": "OBSERVED",
    "limitations": ["docs are not transcripts; precision on real regions is NOT_MEASURED", "scan timings are single runs on a shared host"],
    "verdict": "KEEP",
})

# ---------------------------------------------------------------- AB117462: carrier compatibility
write("AB117462-carrier-compat", {
    "id": "AB117462/r20261001-01",
    "kind": "carrier-ab",
    "question": "Is this slice duplicated by the open #117462 (Seldash, anchor harvest surface + truncation), and does it compose with it?",
    "inputs": {"arms": arms_block, "tests": {"ours": "tests/agent/test_context_compressor_anchor_index.py",
                                             "theirs": f"tests/agent/test_context_compressor_anchor_harvest.py @ {PR117462}"}},
    "command": "copy each arm file over agent/context_compressor.py in the worktree (plus #117462's test file), run both test files with run_tests.sh, restore",
    "matrix": {
        "c117462": {"ours": "0 passed / 2 failed", "theirs": "5 passed"},
        "c117462_foldin": {"ours": "2 passed", "theirs": "5 passed", "adjacent_8_files": "372 passed / 0 failed"},
        "branch": {"ours": "2 passed", "theirs": "2 passed / 3 failed"},
    },
    "merge": {"branch_vs_main": "clean", "branch_vs_117462_head": "conflict (both edit the _ANCHOR_PATTERNS table)",
              "foldin_patch_applies_to_117462_head": "yes (git apply, offset -105 lines)", "branch_vs_122522_head": "clean"},
    "label": "OBSERVED",
    "readout": "not a duplicate: #117462 does not capture these classes (our tests RED on it) and this slice does not do its work (3 of its 5 tests RED here); the two compose (fold-in GREEN on both suites)",
    "verdict": "KEEP (complementary; coordinate)",
})
print("receipts:", sorted(p.name for p in OUT.iterdir()))
