#!/usr/bin/env python3
"""Build xf.receipt.v1-shaped receipts (round 2, r20261001-02) for staging/compaction-anchor-retention.

Reads raw/ next to this harness directory. Receipts carry repo-relative paths and placeholders only:
  $STAGING  this staging directory          $WT   the worktree (detached at BASE or HEAD)
  $S        scratch root (test homes)       $VENV the read-only Hermes venv
  $SANDBOX  harness/sandbox.sh              $PY   $VENV/bin/python
"""
import collections
import hashlib
import json
import statistics as st
from pathlib import Path

R = Path(__file__).resolve().parents[1]
RAW, OUT = R / "raw", R / "receipts"
OUT.mkdir(exist_ok=True)
BASE = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
HEAD = "b11e27d5f9c60a420cbbe94fa967fc1454df92a6"
PREV_HEAD = "6e0fa629a0f6227b03417d1d6ff7f7d81208346a"
PR117462 = "2c19948e15d68492d048250bae7707ca77063db5"
TREE_117462 = "8d48e1bbf2de02ca54cdf4aa6bdc9bb029183db1"
PR122522 = "f596584b017694bf123d746a87740f58a2db15c1"
RID = "r20261001-02"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


cov = json.loads((RAW / "coverage.json").read_text(encoding="utf-8"))
A = cov["arms"]
MAIN_ARMS = ("base", "branch", "c117462", "c117462_foldin")
common = {
    "schema": "xf.receipt.v1",
    "staging": "compaction-anchor-retention",
    "issue": None,
    "origin_refs": ["NousResearch/hermes-agent#116246", "NousResearch/hermes-agent#87326", "NousResearch/hermes-agent#117462",
                    "NousResearch/hermes-agent#122274", "NousResearch/hermes-agent#122522", "NousResearch/hermes-agent#78457"],
    "base_revision": BASE,
    "head_revision": HEAD,
    "supersedes": f"{PREV_HEAD[:10]} receipts r20261001-01 (superseded-r01/)",
    "policy_revision": {"factory": "FACTORY.md (frontier-2026-10-01)", "protocol": "promotion-readiness-2026-10-01/PROTOCOL.md"},
    "env": {"python": "3.11 (HERMES_PYTHON venv, read-only bind)",
            "sandbox": ("harness/sandbox.sh: bwrap ro-root, --unshare-net (connect -> ENETUNREACH), systemd-resolved socket "
                        "masked (DNS -> EAI_AGAIN), pidns, clearenv, live Hermes install masked except the venv, fresh "
                        "HOME/HERMES_HOME per run; harness/egress_sitecustomize.py logs every non-loopback DNS lookup and "
                        "connect attempt (the script run had these paths inlined; the copy here takes them from env)"),
            "tests": "HOME=$S/testhome-sf-compaction-anchor-retention HERMES_HOME=$HOME/.hermes HERMES_PYTHON=$PY bash scripts/run_tests.sh -j 2 <files> -q"},
    "provenance": "self",
    "ai_assistance": "Claude Code (Opus 5.5) wrote the rows, tests, harness and gold labels; disclosed per repository policy",
    "privacy": "public-aggregate (inputs are committed upstream text or seeded synthetic data; no state.db, no lineages); no absolute local paths",
    "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0, "tokens": 0},
}
arms_block = {
    "base": {"tree": f"{BASE}:agent/context_compressor.py", "sha256": A["base"]["arm_file_sha256"]},
    "branch": {"head": HEAD, "sha256": A["branch"]["arm_file_sha256"]},
    "c117462": {"pr": 117462, "head": PR117462, "merge_tree_with_base": TREE_117462, "merge": "clean",
                "sha256": A["c117462"]["arm_file_sha256"]},
    "c117462_foldin": {"onto": "c117462", "patch": "foldin-on-117462.patch (rows + tests/agent/test_context_compressor_anchor_index.py)",
                       "patch_sha256": sha(R / "foldin-on-117462.patch"),
                       "merge": "hand-ported (rows placed in #117462's cheap-first order)", "sha256": A["c117462_foldin"]["arm_file_sha256"]},
    "branch_r01": {"head": PREV_HEAD, "sha256": A["branch_r01"]["arm_file_sha256"],
                   "role": "previous staging head (untightened error row); comparison only"},
}
harness = {n: sha(R / "harness" / n) for n in ("anchor_coverage.py", "build_receipts.py", "sandbox.sh",
                                               "egress_sitecustomize.py", "negative_controls.py")}
cov_cmd = ("VENV=$VENV HERMES_INSTALL=<live install> EGRESS_DIR=<dir with sitecustomize.py> $SANDBOX $WT <fresh home> <egress log> "
           "$PY $STAGING/harness/anchor_coverage.py --checkout $WT --arm base=raw/arms/base.py --arm branch=raw/arms/branch.py "
           "--arm c117462=raw/arms/c117462.py --arm c117462_foldin=raw/arms/c117462_foldin.py --arm branch_r01=raw/arms/branch_r01.py "
           "--seeds 10 --out <home>/coverage.json   # $WT detached at HEAD; copied to raw/coverage.json")
cov_inputs = {"scorecard": "evals/compaction/results/SCORECARD-2026-08-15.md", "scorecard_sha256": cov["scorecard_sha256"],
              "harness_sha256": harness, "arms": arms_block, "coverage_json_sha256": sha(RAW / "coverage.json"),
              "checkout_for_imports": (f"$WT at {HEAD}; `git diff --name-only {BASE[:10]} {HEAD[:10]}` lists only "
                                       "agent/context_compressor.py and the new test file, so every other module, website/docs, "
                                       f"AGENTS.md and hermes_cli/config_defaults.py are exactly {BASE[:10]}"),
              "egress": "0 attempts logged for the harness run"}


def write(name, body):
    body = {**common, **body}
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def summary(path):
    txt = (RAW / path).read_text(encoding="utf-8")
    return next(l for l in txt.splitlines() if "Summary:" in l).strip("= ").strip()


def egress(path):
    lines = [l.strip() for l in (RAW / path).read_text(encoding="utf-8").splitlines() if l.strip()]  # "<kind> <target>" (pid stripped)
    return dict(collections.Counter(lines))


# ---------------------------------------------------------------- RG01: red/green proof
neg = json.loads((RAW / "negative_controls.json").read_text(encoding="utf-8"))
rs = {f"{arm}_{i}": {"result": (RAW / f"region_scoping_{arm}_{i}.txt").read_text(encoding="utf-8").strip().splitlines()[-2],
                     "egress": egress(f"egress/rs_{arm}_{i}.egress")} for arm in ("base", "head") for i in (1, 2)}
rgb = json.loads((RAW / "replay_gates_base.json").read_text(encoding="utf-8"))
rgh = json.loads((RAW / "replay_gates_head.json").read_text(encoding="utf-8"))
rg_diff = sorted(k for k in set(rgb) | set(rgh) if rgb.get(k) != rgh.get(k))
rg = {
    "id": f"RG01/{RID}",
    "kind": "redgreen",
    "question": ("Does main's anchor index capture delegation/kanban task ids, dotted config keys and CLI error lines, do the three "
                 "new rows fix that without catching Python annotations or log format strings, and do neighbours stay unchanged?"),
    "inputs": {"test": "tests/agent/test_context_compressor_anchor_index.py", "test_sha256": "5f2f16b360ee25677eff7450ae37d66946f9d45841c892db8559afbe216d3da5",
               "production_seam": "agent/context_compressor.py::_build_anchor_index / _ANCHOR_PATTERNS",
               "production_sha256": {"base": A["base"]["arm_file_sha256"], "head": A["branch"]["arm_file_sha256"]},
               "branch_patch_sha256": sha(R / "compaction-anchor-retention.patch")},
    "commands": {
        "tests": common["env"]["tests"],
        "red": "git checkout --detach BASE; git show HEAD_SHA:tests/agent/test_context_compressor_anchor_index.py > <same path>; run it; rm it",
        "red_prev_rows": f"at HEAD: git show {PREV_HEAD[:10]}:agent/context_compressor.py > agent/context_compressor.py; run the test file; git checkout -- agent/context_compressor.py",
        "negative_controls": "cd $WT; TESTHOME=... HERMES_PYTHON=$PY $PY $STAGING/harness/negative_controls.py <out>  (one mutation at a time; each mutated table must compile; file restored after)",
        "guards": "$SANDBOX $WT <fresh home> <log> $PY evals/compaction/test_region_scoping.py ; $SANDBOX $WT <fresh home> <log> $PY evals/token_accounting/replay_gates.py --out <home>/out.json",
    },
    "gates": {
        "red": {"arm": f"base {BASE}", "result": "PASS", "observed": summary("red_main.full"),
                "assertion": "AssertionError: 'sa-2-7318d0ba' missing from anchor index / AssertionError: assert 'compression.tail_mode' in ''",
                "label": "OBSERVED"},
        "red_prev_rows": {"arm": f"previous staging head {PREV_HEAD[:10]} rows", "observed": summary("red_prev_rows.full"),
                          "assertion": ("'error: Your local changes ... overwritten by merge' missing (no word boundary after an escaped \\n) / "
                                        "'Exception)' leaked into error messages ('error: Optional[Exception] = None(x2), error: %s\", exc)(x2), ...')"),
                          "label": "OBSERVED", "note": "the precision and JSON-output assertions are new in this round"},
        "green": [{"arm": f"branch {HEAD}", "result": "PASS", "reps_agree": "3/3",
                   "observed": [summary(f"green_{i}.full") for i in (1, 2, 3)], "label": "OBSERVED"}],
        "sabotage": {"per_hunk": [{"mutation": x["mutation"], "red_again": bool(x["failed"]), "observed": x["summary"],
                                   "failed": x["failed"]} for x in neg],
                     "unpinned_hunks": [], "label": "OBSERVED"},
        "adjacent": {"files": ["tests/agent/test_context_compressor.py", "tests/agent/test_lean_single_aux_call.py",
                               "tests/agent/test_compression_rotation_state.py", "tests/agent/test_context_compressor_summary_continuity.py",
                               "tests/agent/test_compaction_redaction_boundaries.py", "tests/agent/test_native_compaction_summary_retention.py"],
                     "base": summary("adjacent_base.full"), "arm": summary("adjacent_head.full") + " (the 6 files + the new test file)",
                     "identical": True, "pre_existing_failures": [], "label": "OBSERVED"},
        "guards": {"evals/compaction/test_region_scoping.py": {"base": [rs["base_1"]["result"], rs["base_2"]["result"]],
                                                                "head": [rs["head_1"]["result"], rs["head_2"]["result"]]},
                   "evals/token_accounting/replay_gates.py": {"base": f"{sum(v == 'PASS' for v in rgb['verdict'].values())}/{len(rgb['verdict'])} PASS",
                                                              "head": f"{sum(v == 'PASS' for v in rgh['verdict'].values())}/{len(rgh['verdict'])} PASS",
                                                              "result_dict_keys_differing": rg_diff},
                   "files_unchanged": True,
                   "egress_attempts": {
                       "region_scoping_per_run": {k: v["egress"] for k, v in rs.items()},
                       "replay_gates": {"base": egress("egress/rg_base.egress"), "head": egress("egress/rg_head.egress")},
                       "readout": ("region_scoping: 2 DNS lookups of openrouter.ai per run (the model-metadata fetch, logged as 'Failed to fetch "
                                   "model metadata from OpenRouter' twice), on base and head alike, each run in a fresh home; both fail inside "
                                   "the sandbox, so 0 connect attempts follow. replay_gates: 0 attempts on both."),
                   },
                   "label": "OBSERVED"},
        "flaky": False,
        "route_scope": "local-compressor (lean tail mode only; _augment_summary_lean is a no-op in legacy mode; native summaries are opaque)",
        "cache_read_ratio": {"status": "N_A", "why": "rows change summary text only at a compaction event, which already breaks the prompt cache; cadence unchanged"},
    },
    "denominators": {"cells": 1 + 1 + 3 + len(neg) + 2 + 4 + 2, "errored_scored_zero": 0, "infra_excluded": 0, "completeness": 1.0},
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
    "not_tested": ["recall exam (E04/E05): needs an aux LLM", "real lineages (state.db copies): forbidden here / OD-7", "native compaction routes"],
    "verdict": "KEEP",
    "raw": {"red": "raw/red_main.full", "red_prev_rows": "raw/red_prev_rows.full", "green": [f"raw/green_{i}.full" for i in (1, 2, 3)],
            "negative_controls": "raw/negative_controls.json", "adjacent": ["raw/adjacent_base.full", "raw/adjacent_head.full"],
            "guards": [f"raw/region_scoping_{a}_{i}.txt" for a in ("base", "head") for i in (1, 2)]
            + ["raw/replay_gates_base.json", "raw/replay_gates_head.json", "raw/egress/"]},
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
               "'natural' re-tests 4 golds inside the line their emitter prints (gh 'GraphQL: ', tsc 'error TS2741: ', GNU as 'Fatal error: ', "
               "'PR #82980'); that column is MODELED."),
    "measurements": [
        {"name": "identifier_golds_reachable_raw", "arm": a, "value": tot[a]["reachable_raw"], "n": tot[a]["in_scope"], "label": "OBSERVED"} for a in MAIN_ARMS
    ] + [
        {"name": "identifier_golds_reachable_in_emitter_line", "arm": a, "value": tot[a]["reachable_natural"], "n": tot[a]["in_scope"], "label": "MODELED"} for a in MAIN_ARMS
    ],
    "per_class": tables,
    "newly_reachable_on_branch": newly,
    "in_sample_warning": {
        "circular": ("the rows were written after reading these same golds, so 24 -> 31 is an in-sample count, not a held-out estimate. "
                     "The 'GraphQL' and 'Blocked' alternatives of the error row exist because of these golds."),
        "error_line_gain": {"golds": len(err_new), "distinct_strings": len(distinct_err), "strings": dict(distinct_err),
                            "note": ("'Blocked: ...' is Hermes's own tool-refusal prefix (the terminal git guard here), not a CLI error line; "
                                     "the lowercase fatal:/error: and 'error TS####:' alternatives match 0 raw golds")},
        "held_out_check": ("SCORECARD-2026-09-19-jev.md asks for coverage on its prreview/sysprompt/sigsegv banks; those banks and their golds "
                           "are not committed (jev-cycles-2026-09-19/*.json carry no golds), so that check was not run"),
    },
    "missing_class_evidence": {
        "error_message": {"golds": tables["base"]["error_message"]["golds"], "reachable_on_main": tables["base"]["error_message"]["reachable_raw"],
                          "lineages": tables["base"]["error_message"]["lineages_unreached"], "gate_3_lineages": len(tables["base"]["error_message"]["lineages_unreached"]) >= 3},
        "task_id": {"golds": 1, "lineages": ["gui"], "plus": "maintainer statement (SCORECARD-2026-09-19-jev.md: 'delegation ids'), source-only"},
        "config_key": {"golds": 1, "lineages": ["prmerge"], "plus": "maintainer statement ('config keys'), source-only"},
        "env_var": {"golds": 0, "decision": "no row added (no evidence)"},
        "symbol": {"golds": tables["base"]["symbol"]["golds"], "lineages": tables["base"]["symbol"]["lineages_unreached"],
                   "decision": "largest residual unreachable class; not addressed (a bare snake/camel identifier row would be dominated by frequent code tokens)"},
    },
    "emitter_line_change_vs_r01": ("branch 35 -> 34 MODELED: the GNU as line 'Fatal error: error writing to ...: No space left on device' no longer "
                                   "matches, because 'error:' there does not start a line"),
    "limitations": ["reachability is an upper bound: it does not show the gold text was in the compacted region, nor that it survives caps/budget",
                    "labels are agent-assigned (not human-curated); value claims need the human-curated exam",
                    "in-sample: see in_sample_warning"],
    "verdict": "KEEP (missing classes confirmed on the committed banks: error lines on 3 lineages; task id and config key on 1 each; in-sample)",
    "learning": {"hypothesis": "classes named in SCORECARD-2026-09-19 are absent from _ANCHOR_PATTERNS",
                 "result": "confirmed for error lines, subagent ids, dotted config keys; env vars unevidenced; symbols are the larger residual"},
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
        new = ("error_message", "config_key", "task_id")
        out[dens] = {"all": [sum(x["hit"] for x in rows), sum(x["total"] for x in rows)],
                     "new_classes": [sum(byc[c][0] for c in new), sum(byc[c][1] for c in new)],
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
               "real _build_anchor_index output"),
    "label": "MODELED",
    "results": E,
    "readout": [
        (f"sparse: branch and fold-in keep {E['branch']['sparse']['new_classes'][0]}/{E['branch']['sparse']['new_classes'][1]} new-class needles "
         f"(main {E['base']['sparse']['new_classes'][0]}/110). The misses are 'Hermes backend exited (0)', which no row targets, and the GNU as "
         f"'Fatal error: error writing ...' line, which the line-start rule now skips (previous rows: {E['branch_r01']['sparse']['new_classes'][0]}/110)"),
        (f"medium: branch keeps {E['branch']['medium']['new_classes'][0]}/110 (rows are appended last, so they only get leftover budget; error "
         f"messages {E['branch']['medium']['per_class']['error_message'][0]}/90), fold-in {E['c117462_foldin']['medium']['new_classes'][0]}/110"),
        (f"dense: every arm loses almost all once-mentioned needles of every class (main {E['base']['dense']['all'][0]}/570, #117462 "
         f"{E['c117462']['dense']['all'][0]}/570); frequency-first ranking plus the 7,000-char budget, not the row set, is the binding limit"),
    ],
    "limitations": ["filler distributions are invented; real regions mention important identifiers more than once", "no LLM summary text is included (index only)"],
    "verdict": "PARTIAL (mechanism works where budget remains; full effect on main needs #117462's per-section truncation; dense regions are bounded by ranking)",
})

f02 = {}
for a in MAIN_ARMS:
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
    f02[a]["timing_443k_char_region_s"] = A[a]["timing_big_region"]["build_s"]


def key(x):
    return (x["density"], x["seed"], x["bank"])


b = {key(x): x["sections"] for x in A["base"]["F02s"]}
h = {key(x): x["sections"] for x in A["branch"]["F02s"]}
prefix_ok = sum(1 for k in b if h[k][:len(b[k])] == b[k])
write("F02s-budget-audit", {
    "id": f"F02s/{RID}",
    "kind": "static",
    "question": "How large does the anchor index get with the new rows, against _LEAN_ANCHOR_BUDGET_CHARS=7000 and the 32k-token retained-summary budget, and do main's existing sections stay byte-identical?",
    "substitutes_for": "F02 on frozen local lineages (needs OD-7)",
    "inputs": cov_inputs, "command": cov_cmd,
    "measurements": [
        {"name": "branch_index_chars_max", "arm": "branch", "value": f02["branch"]["index_chars_max"], "n": f02["branch"]["regions"], "label": "OBSERVED",
         "note": "this PR's arm only: 180 synthetic regions (10 seeds x 6 banks x 3 densities)"},
        {"name": "branch_sections_chars_max", "arm": "branch", "value": f02["branch"]["sections_chars_max"], "n": f02["branch"]["regions"], "label": "OBSERVED"},
        {"name": "branch_index_tokens_max", "arm": "branch", "value": f02["branch"]["index_chars_max"] // 4, "label": "MODELED",
         "note": "chars/4, the harness convention; vs RETAINED_SUMMARY_TOKEN_BUDGET=32000 (agent/native_compaction.py:146)"},
        {"name": "base_sections_prefix_of_branch_sections", "value": prefix_ok, "n": len(b), "label": "OBSERVED",
         "note": "strict additivity on main: existing lines byte-identical"},
    ] + [{"name": "index_chars_max", "arm": a, "value": f02[a]["index_chars_max"], "n": f02[a]["regions"], "label": "OBSERVED"} for a in MAIN_ARMS],
    "per_arm": f02,
    "structural_note": ("over-budget counts are 0 on every arm BY CONSTRUCTION, not as a finding: main's loop only appends a section while "
                        "used + len(line) <= 7000 and #117462 truncates a section to the room left. The measurement of interest is the "
                        "size: heading, separators and footer add under 200 chars on top of the sections"),
    "not_measured": ["whole-summary tokens on real lineages (LLM output): NOT_MEASURED; the index adds at most about 1.8k tokens (MODELED)"],
    "verdict": "KEEP",
})

# ---------------------------------------------------------------- N01: noise audit
NEW_ROWS = ("task ids", "dotted keys", "error messages")
br, r01 = A["branch"]["N01"], A["branch_r01"]["N01"]
code, code01 = br["code"], r01["code"]
write("N01-noise-audit", {
    "id": f"N01/{RID}",
    "kind": "static",
    "question": "What do the three new rows capture on large public Hermes text, both docs and Python source (a stand-in for read_file output)?",
    "inputs": {**cov_inputs,
               "docs_corpus": {"what": f"AGENTS.md + website/docs/**/*.md at {BASE}", "files": br["corpus_files"], "chars": br["corpus_chars"],
                               "sha256": br["corpus_sha256"]},
               "code_corpus": {"what": f"agent/*.py at {BASE}", "files": code["corpus_files"], "chars": code["corpus_chars"], "sha256": code["corpus_sha256"]},
               "default_config_keys": br["default_config_keys"]},
    "command": cov_cmd,
    "results": {"docs": {lab: br[lab] for lab in NEW_ROWS if lab in br}, "code": {lab: code[lab] for lab in NEW_ROWS if lab in code}},
    "previous_rows_r01": {"docs_error_messages_matches": r01["error messages"]["matches"],
                          "code_error_messages": {"matches": code01["error messages"]["matches"], "distinct": code01["error messages"]["distinct"],
                                                  "sample": code01["error messages"]["values"][:12]}},
    "scan_seconds": {a: A[a]["N01"]["scan_s"] for a in MAIN_ARMS},
    "readout": [
        f"task ids: {br['task ids']['matches']} matches / {br['task ids']['distinct']} distinct in the docs (both doc examples), 0 in agent/*.py",
        (f"dotted keys, docs: {br['dotted keys']['distinct']} distinct values, {br['dotted keys']['distinct_in_DEFAULT_CONFIG']} "
         f"({100 * br['dotted keys']['distinct_in_DEFAULT_CONFIG'] / br['dotted keys']['distinct']:.1f}%) are DEFAULT_CONFIG keys, hence the label 'dotted keys'"),
        (f"dotted keys, code (LIMITATION): {code['dotted keys']['distinct']} distinct values in agent/*.py; of the 40 most frequent, "
         f"{code['dotted keys']['top40_self_attr']} are self.* attributes and {code['dotted keys']['top40_in_DEFAULT_CONFIG']} are DEFAULT_CONFIG keys "
         "(the rest are attribute accesses such as agent.session_id and module paths). In a region full of Python source the 40-value cap "
         "fills with these, and a config key mentioned once in assistant text can be crowded out. Not changed in this slice."),
        (f"error messages: docs {br['error messages']['matches']} matches (previous rows {r01['error messages']['matches']}); agent/*.py "
         f"{code['error messages']['matches']} matches, both real message strings (previous rows {code01['error messages']['matches']} matches, "
         "nearly all annotations such as 'error: Exception) -> Dict[str, Any]' or log formats such as 'error: %s\", exc)')"),
    ],
    "label": "OBSERVED",
    "limitations": ["docs and source files are not transcripts; precision on real regions is NOT_MEASURED", "scan timings are single runs on a shared host"],
    "verdict": "KEEP (error row tightened this round; dotted-keys code limitation disclosed)",
})

# ---------------------------------------------------------------- AB117462: carrier compatibility
write("AB117462-carrier-compat", {
    "id": f"AB117462/{RID}",
    "kind": "carrier-ab",
    "question": "Is this slice duplicated by the open #117462 (Seldash, anchor harvest surface + truncation), and does it compose with it?",
    "inputs": {"arms": {k: v for k, v in arms_block.items() if k != "branch_r01"},
               "tests": {"ours": "tests/agent/test_context_compressor_anchor_index.py",
                         "theirs": f"tests/agent/test_context_compressor_anchor_harvest.py @ {PR117462}"}},
    "command": "in $WT at HEAD: copy each arm file over agent/context_compressor.py (plus #117462's test file), run both test files with run_tests.sh; restore",
    "matrix": {
        "c117462": {"ours": summary("ab_c117462_ours.full"), "theirs": summary("ab_c117462_theirs.full")},
        "c117462_foldin": {"ours": summary("ab_c117462_foldin_ours.full"), "theirs": summary("ab_c117462_foldin_theirs.full"),
                           "adjacent_8_files": summary("adjacent_foldin.full")},
        "branch": {"ours": summary("ab_branch_ours.full"), "theirs": summary("ab_branch_theirs.full"),
                   "theirs_failing": ["test_anchor_index_cheap_ids_survive_a_tight_budget", "test_anchor_index_harvests_tool_call_arguments_and_artifact_paths",
                                      "test_anchor_index_names_a_class_whose_values_cannot_fit"]},
    },
    "merge": {"branch_vs_main": "clean", "117462_vs_main": f"clean (tree {TREE_117462[:10]})",
              "branch_vs_117462_head": "conflict in agent/context_compressor.py (both edit the _ANCHOR_PATTERNS table)",
              "foldin_patch_applies_to_117462_head": ("yes, exactly (git apply, no offset; the patch is a git diff of #117462's tree "
                                                      "plus the rows and our test file)"),
              "foldin_patch_applies_to_main_plus_117462": ("yes (offset +105 lines); the result is byte-identical to the tested "
                                                           "c117462_foldin arm"),
              "branch_vs_122522_head": f"clean ({PR122522[:10]})"},
    "pr_state_read_only": {"117462": "OPEN, head 2c19948e15, 0 formal reviews; 1 issue comment from a User account (kyssta-exe) signed 'Reviewed using Hermes-Agent', verdict 'Looks good to merge'; author follow-up 2026-09-22",
                           "122522": "OPEN, head f596584b01"},
    "label": "OBSERVED",
    "readout": "not a duplicate: #117462 does not capture these classes (our tests RED on it) and this slice does not do its work (3 of its 5 tests RED here); the two compose (fold-in GREEN on both suites)",
    "verdict": "KEEP (complementary; this slice is offered to #117462 as a fold-in)",
})
print("receipts:", sorted(p.name for p in OUT.iterdir()))
