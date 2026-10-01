"""Write the xf.receipt.v1-shaped receipts for staging/postmortem-logcalls-zero-hit from the raw outputs.

Published copy: the local paths and the host name are replaced by <placeholders> (<xf-root>, <worktree>,
<scratch>, <venv>, <host>); re-point them before running. The as-run copy is kept privately
(sha256 3dfc66041b5d93dbab6315173bba59948928c5d35501b394dd7e6871d5ce6910).
"""
import hashlib
import json
import re
from pathlib import Path

R = Path("<xf-root>/staging/postmortem-logcalls-zero-hit")
RAW = R / "receipts" / "raw"
MAIN = "234badf4012af380d23c91eae55d045a69c69ffb"
HEAD = "dd4dd10611e8c23c7579a4ddb95655abebbaca27"
PR121135 = "dd4a0ca4cf3345702eb7be95e11873308d3015b5"
PR119713 = "7471d9915d7d1ce3e94f9d18c9d775461d269815"
WT = "<worktree>"
S = "<scratch>"
TS = "2026-10-01"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ev(*rel):
    return [{"path": f"receipts/raw/{r}", "sha256": sha(RAW / r)} for r in rel]


def harness(*names):
    return {n: sha(R / "harness" / n) for n in names}


def summary(txt):
    m = re.search(r"Summary: (\d+) files, (\d+) tests passed, (\d+) failed", (RAW / txt).read_text(encoding="utf-8"))
    return {"files": int(m.group(1)), "passed": int(m.group(2)), "failed": int(m.group(3))}


def e_lines(txt):
    return sorted({ln.strip() for ln in (RAW / txt).read_text(encoding="utf-8").splitlines() if ln.startswith("E  ")})


COMMON = {
    "schema": "xf.receipt.v1",
    "issue": "kvnloo/hermes-agent (no campaign thread yet; OD-9)",
    "origin_refs": ["NousResearch/hermes-agent#121135", "NousResearch/hermes-agent#84460",
                    "NousResearch/hermes-agent#119713", "NousResearch/hermes-agent#103563"],
    "staging": "postmortem-logcalls-zero-hit",
    "base_revision": MAIN,
    "head_revision": HEAD,
    "changed_files": ["evals/postmortem/forensics/logcalls.py", "evals/postmortem/live_ab/cache_prefix_live.py",
                      "evals/postmortem/live_ab/cache_prefix_wire.py", "evals/postmortem/tests/test_postmortem_harness.py"],
    "env": {"host": "<host>", "test_python": "3.11.14 (HERMES_PYTHON, not activated)", "host_python": "3.14.7",
            "sandbox": "no bwrap (xf executor not built); HOME/HERMES_HOME = fresh scratch dirs; loopback-only socket guard and exec audit hook in the T1 round trip",
            "tz": "America/Chicago (CDT -0500)"},
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
    "harness_abi": {"harness": "hermes evals/postmortem", "editor_abi": "n/a"},
    "provenance": "self",
    "ai_assistance": "Claude Code (Opus 5.5) wrote the patch, tests and harness scripts; disclosed per repository policy",
    "privacy": "synthetic inputs only; no real state.db or agent.log was read",
    "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0, "energy_j": None},
    "frozen": None, "z0evals_study": None,
}

receipts = {}

# 1. PROOF
neg = {}
for m, hunk in (("N1_require_cache", "logcalls _LINE: cache= group made mandatory again"),
                ("N2_no_unavailable", "logcalls _LINE: in=?/out=?/total=? alternatives removed"),
                ("N3_no_field_counts", "_cache_reported always True (no_field read as a miss)"),
                ("N4_cache_state_unread", "cache_state= not captured by parse_logs"),
                ("N5_ratio_over_all", "hit ratio summed over all metered calls instead of scored"),
                ("N6_plateau_unfiltered", "plateau pairs include no_field calls")):
    neg[m] = {"hunk": hunk, "result": summary(f"neg_{m}.txt"), "red_again": summary(f"neg_{m}.txt")["failed"] > 0,
              "assertions": e_lines(f"neg_{m}.txt")[:3]}
sib = json.loads((RAW / "sibling.json").read_text(encoding="utf-8"))
probe_neg = {p: {"base_rows": sib["arms"]["main"]["per_probe"][p]["base"]["rows"],
                 "patched_rows": sib["arms"]["main"]["per_probe"][p]["patched"]["rows"],
                 "metered_lines": sib["arms"]["main"]["metered_lines"]} for p in sib["probes"]}
receipts["PROOF"] = {**COMMON,
    "id": "PROOF/r20261001-01", "tier": "T1", "cost": "$0",
    "experiment": "RED / GREEN x3 / per-hunk NEGATIVE / ADJACENT for the staging commit",
    "inputs": {"main": MAIN, "commit": HEAD, "mutator": harness("mutate.py"), "runner": harness("prove.sh")},
    "command": (f"bash {R}/harness/prove.sh   # wraps, per run: env -u __HERMES_ACTIVATED HOME={S}/testhome-st-postmortem-logcalls-zero-hit "
                f"HERMES_HOME=$HOME/.hermes HERMES_PYTHON=<venv>/bin/python bash scripts/run_tests.sh -j 2 <files> -q"),
    "gates": {
        "red": {"arm": "main parser + committed tests", "result": "PASS", "observed": summary("red.txt"), "assertions": e_lines("red.txt"),
                "marker": "calls_found 2 != 3 (miss dropped) and 2 != 4 (cold_write and no_field dropped)"},
        "green": {"reps": [summary(f"green{i}.txt") for i in (1, 2, 3)], "reps_agree": "3/3",
                  "files": ["evals/postmortem/tests/test_postmortem_harness.py", "tests/agent/test_turn_usage_log_line.py"]},
        "sabotage": {"per_hunk": neg, "probe_hunks_offline": probe_neg,
                     "unpinned_hunks": ["logcalls docstring", "logcalls early-exit message (`if not scored`)", "logcalls coverage print line",
                                        "live probes: `int(c or 0)` / `p or 0` print arithmetic (pinned offline only, see F06RT)"]},
        "adjacent": {"files": ["tests/agent/test_turn_usage_log_line.py (imports logcalls.parse_logs; teknium's parser test)",
                               "evals/postmortem/tests/test_postmortem_harness.py (3 pre-existing tests)"],
                     "base": "6 passed / 0 failed", "arm": "all pre-existing pass", "identical": True, "pre_existing_failures": []},
        "lint": {"ruff_repo_config": (RAW / "ruff.txt").read_text(encoding="utf-8").strip(), "py_compile_probes": "ok", "windows_footguns": (RAW / "footguns.txt").read_text(encoding="utf-8").strip().splitlines()},
        "flaky": False,
    },
    "measurements": [
        {"name": "red_tests_failed", "arm": "main", "value": summary("red.txt")["failed"], "n": 1, "label": "OBSERVED", "statistic": "count"},
        {"name": "green_tests_passed", "arm": "head", "value": summary("green1.txt")["passed"], "n": 3, "label": "OBSERVED", "statistic": "count per rep"},
        {"name": "sabotage_hunks_red_again", "arm": "head", "value": sum(v["red_again"] for v in neg.values()), "n": len(neg), "label": "OBSERVED", "statistic": "count"},
    ],
    "not_tested": ["evals/ is outside pytest testpaths, so CI does not run these tests", "live probes not executed (real provider, paid)"],
    "evidence": ev("heads.txt", "footguns.txt", "red.txt", "green1.txt", "green2.txt", "green3.txt", *[f"neg_{m}.txt" for m in neg], "ruff.txt", "sibling.json"),
    "verdict": "KEEP",
}

# 2. F06RT round trip
rts = {a: json.loads((RAW / f"rt_{a}.json").read_text(encoding="utf-8")) for a in ("main", "a1_pr121135", "a2_pr119713")}
receipts["F06RT"] = {**COMMON,
    "id": "F06RT/r20261001-01", "tier": "T1", "cost": "$0",
    "experiment": "Producer -> parser round trip: the real agent.turn_usage.record_response_usage emits hit / miss / cold_write / no_field / usage-less lines through the real agent.log formatter; each logcalls variant parses them. Then the two live probes' regex literals (pulled by ast, never imported) replay the same lines.",
    "arms": {"main": {"tree": "main", "head": MAIN},
             "a1_pr121135": {"merge_tree": "256dab57f9301d5826a776b5994da966084f0cda", "carrier_head": PR121135, "merge": "clean",
                             "overlay": ["agent/turn_usage.py", "agent/usage_pricing.py"]},
             "a2_pr119713": {"merge_tree": "4506c3748f6d4efedaf0f9421e7aea1fc69f5e64", "carrier_head": PR119713, "merge": "clean",
                             "overlay": ["agent/turn_response_check.py", "agent/turn_usage.py"]}},
    "inputs": {"parser_main": {"path": "receipts/raw/logcalls.main@234badf401.py", "sha256": sha(RAW / "logcalls.main@234badf401.py")},
               "parser_patched": f"{HEAD}:evals/postmortem/forensics/logcalls.py", "scripts": harness("roundtrip.py", "sibling_regex.py", "arms.sh")},
    "command": [f"<venv>/bin/python {R}/harness/roundtrip.py {WT} <arm> main=<logcalls.main.py> patched={WT}/evals/postmortem/forensics/logcalls.py",
                f"bash {R}/harness/arms.sh   # overlays each carrier merge tree's files, runs the round trip, restores HEAD",
                f"python3 {R}/harness/sibling_regex.py <dir with main's live_ab probes> {WT} rt_main.json rt_a1_pr121135.json rt_a2_pr119713.json"],
    "measurements": (
        [{"name": "lines_matched", "arm": a, "parser": p, "value": v["matched"], "of": v["of"], "label": "OBSERVED", "statistic": "count"}
         for a, d in rts.items() for p, v in d["parsers"].items()]
        + [{"name": "probe_rows", "arm": a, "probe": p, "side": s, "value": sib["arms"][a]["per_probe"][p][s]["rows"],
            "of_metered": sib["arms"][a]["metered_lines"], "arm_hit_pct": sib["arms"][a]["per_probe"][p][s]["arm_hit_pct"], "label": "OBSERVED"}
           for a in sib["arms"] for p in sib["probes"] for s in ("base", "patched")]),
    "observed_lines": {a: d["lines"] for a, d in rts.items()},
    "result": "On all three arms the real producer emits 5 API-call lines; main's parser matches 1/5 (only the cache hit), the patched parser 5/5, with usage=unavailable carried as inp=None, cache_state read on the #121135 arm, and upstream= still parsed before trailing cache_state=/ttfb=. Live-probe regexes: base 1/4 metered rows (ARM hit 40.0%), patched 4/4 (ARM hit 10.0% = 40 cached of 400 input).",
    "safety": {a: d["safety"] for a, d in rts.items()},
    "not_tested": ["combined #121135+#119713 producer (the two carriers conflict in agent/turn_usage.py; the combined shape is covered only by the harness fixture)",
                   "providers other than chat_completions/openai-shaped usage in the round trip", "live probes end-to-end"],
    "evidence": ev("rt_main.json", "rt_a1_pr121135.json", "rt_a2_pr119713.json", "sibling.json", "arms.txt"),
    "verdict": "KEEP",
}

# 3. F06SYN
f06 = json.loads((RAW / "f06_summary.json").read_text(encoding="utf-8"))
receipts["F06SYN"] = {**COMMON,
    "id": "F06SYN/r20261001-01", "tier": "T0", "cost": "$0",
    "experiment": "F06 on SYNTHETIC corpora (the real F06 needs OD-7): logcalls coverage and hit ratio, main parser vs patched, on a seeded E19-shaped corpus (model switch, TTL-expiry misses, ~2% usage-less) and an all-hit corpus.",
    "inputs": {"seed": 20261001, "script": harness("f06_synth.py"), "parser_main_sha256": sha(RAW / "logcalls.main@234badf401.py"),
               "parser_patched": f"{HEAD}:evals/postmortem/forensics/logcalls.py",
               "corpora_sha256": {c: f06[c]["inputs_sha256"] for c in f06}},
    "command": f"env -i PATH=/usr/bin:/bin HOME=<scratch> HERMES_HOME=<scratch>/.hermes TZ=America/Chicago python3 {R}/harness/f06_synth.py {WT} <logcalls.main.py> {WT}/evals/postmortem/forensics/logcalls.py <out>",
    "measurements": [
        {"name": "parser_matches_ground_truth", "corpus": "e19_shaped", "arm": "patched",
         "value": f06["e19_shaped"]["cache_hit_ratio_overall"]["patched"] == f06["e19_shaped"]["truth"]["true_hit_ratio"], "label": "OBSERVED"},
        {"name": "coverage_fraction", "corpus": "e19_shaped", "main": f06["e19_shaped"]["coverage_fraction"]["main"],
         "patched": f06["e19_shaped"]["coverage_fraction"]["patched"], "label": "MODELED", "note": "magnitude depends on the synthetic miss rate"},
        {"name": "cache_hit_ratio_overall", "corpus": "e19_shaped", "main": f06["e19_shaped"]["cache_hit_ratio_overall"]["main"],
         "patched": f06["e19_shaped"]["cache_hit_ratio_overall"]["patched"], "truth": f06["e19_shaped"]["truth"]["true_hit_ratio"],
         "delta_pp": f06["e19_shaped"]["hit_ratio_delta_pp"], "label": "MODELED"},
        {"name": "calls_dropped_by_main", "corpus": "e19_shaped", "value": f06["e19_shaped"]["calls_found"]["patched"] - f06["e19_shaped"]["calls_found"]["main"],
         "equals_zero_hit_truth": (f06["e19_shaped"]["calls_found"]["patched"] - f06["e19_shaped"]["calls_found"]["main"]) == f06["e19_shaped"]["truth"]["zero_hit"], "label": "OBSERVED"},
        {"name": "all_hit_observed_block_identical", "corpus": "all_hit", "value": f06["all_hit"]["observed_block_identical"], "label": "OBSERVED"},
        {"name": "all_hit_modeled_block_identical", "corpus": "all_hit", "value": f06["all_hit"]["modeled_block_identical"], "label": "OBSERVED"},
        {"name": "all_hit_coverage_identical_except_new_keys", "corpus": "all_hit", "value": f06["all_hit"]["coverage_identical_except_new_keys"], "label": "OBSERVED"},
        {"name": "real_log_coverage_and_bias", "value": None, "label": "NOT_MEASURED", "note": "needs OD-7 (owner copies state.db + agent.log*)"},
    ],
    "summary": f06,
    "not_tested": ["real logs (OD-7)", "providers whose lines carry cache_state=no_field at scale (#121135 unmerged)"],
    "evidence": ev("f06_summary.json", "f06/f06_synth_full.json", "f06/e19_shaped/agent.log", "f06/e19_shaped/state.db",
                   "f06/all_hit/agent.log", "f06/all_hit/state.db", "f06/e19_shaped/out_main/logcalls.json", "f06/e19_shaped/out_patched/logcalls.json",
                   "f06/all_hit/out_main/logcalls.json", "f06/all_hit/out_patched/logcalls.json"),
    "verdict": "KEEP",
}

# 4. E19SYN
e19m = json.loads((RAW / "e19_synth_main.json").read_text(encoding="utf-8"))
e19p = json.loads((RAW / "e19_synth_patched.json").read_text(encoding="utf-8"))
receipts["E19SYN"] = {**COMMON,
    "id": "E19SYN/r20261001-01", "tier": "T0", "cost": "$0",
    "experiment": "E19 baseline vs rerun after the fix, on the SYNTHETIC e19_shaped corpus only: hit ratio over the 5 usage-bearing calls before and after the root session's model switch.",
    "inputs": {"script": harness("e19_switch.py"), "corpus_sha256": f06["e19_shaped"]["inputs_sha256"],
               "parser_main_sha256": sha(RAW / "logcalls.main@234badf401.py"), "parser_patched": f"{HEAD}:evals/postmortem/forensics/logcalls.py"},
    "command": f"env -i PATH=/usr/bin:/bin PYTHONPATH={WT} HOME=<scratch> HERMES_HOME=<scratch>/.hermes python3 {R}/harness/e19_switch.py <logcalls variant> <corpus>/state.db '<corpus>/agent.log' 5",
    "measurements": [
        {"name": "coverage_fraction", "main": e19m["coverage"]["fraction"], "patched": e19p["coverage"]["fraction"], "label": "MODELED"},
        {"name": "switch_first_call_seen", "main": e19m["switches"][0]["call_n"], "patched": e19p["switches"][0]["call_n"], "true_switch_call": 61,
         "label": "OBSERVED", "note": "main's parser never sees call 61 (the full miss right after the switch)"},
        {"name": "hit_ratio_after_switch_k5", "main": e19m["switches"][0]["after"], "patched": e19p["switches"][0]["after"], "label": "MODELED"},
        {"name": "hit_ratio_before_switch_k5", "main": e19m["switches"][0]["before"], "patched": e19p["switches"][0]["before"], "label": "MODELED"},
        {"name": "real_e19_baseline", "value": None, "label": "NOT_MEASURED", "note": "needs OD-7; queued"},
    ],
    "result": "Baseline parser shows no cache loss at the switch (after 98.8% vs before 98.4%) because it drops the miss; the fixed parser shows it (after 79.5%). Synthetic magnitude only.",
    "not_tested": ["real model switches (OD-7)"],
    "evidence": ev("e19_synth_main.json", "e19_synth_patched.json"),
    "verdict": "KEEP",
}

# 5. CARRIER
mt = (RAW / "merge_tree.txt").read_text(encoding="utf-8")
receipts["CARRIER"] = {**COMMON,
    "id": "CARRIER/r20261001-01", "tier": "T1", "cost": "$0",
    "experiment": "Carrier compatibility: merge-tree matrix (main, #121135, #119713, staging commit) and the carriers' own tests plus the harness on each carrier arm with the patched parser.",
    "arms": receipts["F06RT"]["arms"],
    "inputs": {"carriers": {"#121135": {"author": "Wenfengcheng (commits by funky-xamarin)", "head": PR121135, "state": "OPEN"},
                            "#119713": {"author": "teknium1", "head": PR119713, "state": "OPEN"}},
               "scripts": harness("mt.sh", "arms.sh")},
    "command": [f"bash {R}/harness/mt.sh", f"bash {R}/harness/arms.sh"],
    "merge_tree": mt.strip().splitlines(),
    "measurements": [
        {"name": "merge_clean", "pair": "#121135 x staging", "value": "CLEAN tree=2e7d28d7d314538bf74cd0c42ad3fb2113c88f3a" in mt, "label": "OBSERVED"},
        {"name": "merge_clean", "pair": "#119713 x staging", "value": "CLEAN tree=97793e195c23312e44526170bfe0901163790b38" in mt, "label": "OBSERVED"},
        {"name": "merge_clean", "pair": "main x staging", "value": "main x mine: CLEAN" in mt, "label": "OBSERVED"},
        {"name": "merge_clean", "pair": "#121135 x #119713", "value": False, "label": "OBSERVED", "note": "both edit the log format strings in agent/turn_usage.py; not ours to resolve"},
        {"name": "tests_on_arm", "arm": "a1_pr121135", **summary("tests_a1_pr121135.txt"),
         "files": ["evals/postmortem/tests/test_postmortem_harness.py", "tests/agent/test_turn_usage_log_line.py", "tests/agent/test_cache_log_states.py"], "label": "OBSERVED"},
        {"name": "tests_on_arm", "arm": "a2_pr119713", **summary("tests_a2_pr119713.txt"),
         "files": ["evals/postmortem/tests/test_postmortem_harness.py", "tests/agent/test_turn_usage_log_line.py"], "label": "OBSERVED"},
    ],
    "not_tested": ["a three-way arm (#121135 + #119713 + staging): the carriers conflict with each other"],
    "evidence": ev("merge_tree.txt", "arms.txt", "tests_a1_pr121135.txt", "tests_a2_pr119713.txt"),
    "verdict": "KEEP",
}

out = R / "receipts"
index = {}
for key, rec in receipts.items():
    p = out / f"{rec['id'].replace('/', '_')}.json"
    p.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    index[rec["id"]] = {"path": str(p.relative_to(R)), "sha256": sha(p)}
(out / "INDEX.json").write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
print(json.dumps(index, indent=1))
