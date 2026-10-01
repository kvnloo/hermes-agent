"""Compose the $0 receipts for staging/edit-fuzzy-wrong-region from the raw run outputs."""
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

P = Path(os.environ["S"]) / "st-edit-fuzzy"  # was an absolute scratch path
OUT = Path(os.environ["STAGING_DIR"])  # was an absolute path
RC = OUT / "receipts"
RAW = RC / "raw"
RAW.mkdir(parents=True, exist_ok=True)

MAIN_TESTED = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0"
MAIN_FINAL = "234badf4012af380d23c91eae55d045a69c69ffb"
FACTORY_BASE = "e496ccc7d7e0ca885041e69223683d7739123ff9"
COMMIT_TESTED = "01bf8d379edc480765c53c087735e09be7798140"
COMMIT_FINAL = "ea25f06132c81ef18f44f160b7a278770ac59586"
COMMIT_INTERMEDIATE = "8375dc3ccae5e7d32f2d9be43792e85936d560e1"
BLOBS = {"tools/fuzzy_match.py": "a6a439d70e7d31a2ff781db3ab9baa6686ea4ee9",
         "tools/file_operations.py": "cc028e89f130b2629cbcb6448203b1a5d770c45a",
         "tools/patch_parser.py": "8e6ce92ed7b68d3ca32c57b346a4a1087af0c8bf",
         "tests/tools/test_fuzzy_match_wrong_region.py": "3335a5bf23ea75c684dc02521fef640617ea50bf"}
PY = "<venv-python> (interpreter only; HOME/HERMES_HOME isolated)"
ENV = {"host": "<local-workstation> (name withheld)", "python_interpreter": PY,
       "HOME": "$S/testhome-st-edit-fuzzy-wrong-region", "HERMES_HOME": "$HOME/.hermes",
       "network": "loopback-only by construction (no provider, no model, direct tool calls)",
       "sandbox": "process isolation via run_tests.sh clean env; bwrap NOT used (xf executor not built)"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def keep(src, rel):
    dst = RAW / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return {"path": f"receipts/raw/{rel}", "sha256": sha256(dst)}


FILE_RE = re.compile(r"\] [✓✗] (\S+) \((\d+)✓(?: (\d+)s)?(?: (\d+)✗)?")


def parse_log(path):
    text = Path(path).read_text(encoding="utf-8")
    head = text.splitlines()[0]
    meta = dict(kv.split("=", 1) for kv in head[2:].split() if "=" in kv)
    files = {}
    for m in FILE_RE.finditer(text):
        files[m.group(1)] = {"passed": int(m.group(2)), "skipped": int(m.group(3) or 0),
                             "failed": int(m.group(4) or 0)}
    failed = sorted({re.sub(r" - .*", "", l[len("FAILED "):]) for l in text.splitlines() if l.startswith("FAILED ")})
    rc = re.search(r"^# rc=(\d+)", text, re.M)
    return {"meta": meta, "files": files, "failed_ids": failed, "rc": int(rc.group(1)) if rc else None}


runs = {}
for log in sorted((P / "runs").rglob("*.log")):
    arm = log.parent.name
    rel = f"runs/{arm}/{log.name}"
    runs[rel] = {**parse_log(log), "log": keep(log, rel)}

CONTRACT = "tests/tools/test_fuzzy_match_wrong_region.py"


def contract_counts(arm, label="proof"):
    reps = [runs[k] for k in sorted(runs) if k.startswith(f"runs/{arm}/{label}.rep")]
    out = [(r["files"][CONTRACT]["passed"], r["files"][CONTRACT]["failed"]) for r in reps]
    return {"reps": len(out), "per_rep_pass_fail": out, "reps_agree": len(set(out)) == 1,
            "failed_ids_rep1_all_files_in_run": reps[0]["failed_ids"] if reps else None}


# ---------------- F01 carrier A/B ----------------
arms_def = {
    "base": {"tree": f"main {MAIN_TESTED[:10]} + contract commit {COMMIT_TESTED[:10]}", "merge": "n/a",
             "fuzzy_match_sha256": sha256(P / "arms/base/fuzzy_match.py")},
    "c54575": {"pr": 54575, "author": "MaxFreedomPollard", "head": "e28d7c772dccbc5a773c758b5ae647cac7e98d19",
               "merge": "conflict (tests only); tools/fuzzy_match.py hunk merges clean; test conflicts resolved mechanically "
                        "(keep main's deletion of TestStrategyNameSurfaced / TestTerminalOutputCleanliness, keep the carrier's additions) "
                        "by receipts/raw/scripts/resolve_drop_base.py, which refuses any other conflict shape. The published c54575-rebased-on-main.diff is purely additive (0 removed lines); the overlay these runs used differed from it only in blank lines (diff -w -B empty: an earlier resolver pass collapsed 4+ newline runs), so results carry over",
               "merge_tree_on_main": "3ff55756f369bf59ba9ac10bd1084ebadddde3bc",
               "fuzzy_match_sha256": sha256(P / "overlay/c54575/tools/fuzzy_match.py")},
    "c125376": {"pr": 125376, "author": "Finn763", "head": "5f3f5896a4b03f102be75e3f2bdd8aae8ca65fd1",
                "merge": "CONFLICTING (tui_gateway/methods_bot_relay.py from the bundled bot_relay commit 1c890ae8d0); not run. "
                         "Its merged tools/fuzzy_match.py is byte-identical to c125376-leaf's (sha256 below), so the leaf arm stands in for the edit fix.",
                "merge_tree_on_main": "8c7468038303612dcee4c9cb9eaed32f8837fc66",
                "fuzzy_match_sha256": sha256(P / "arms/c125376/fuzzy_match.py")},
    "c125376-leaf": {"cherry_pick": ["5f3f5896a4"], "merge": "clean", "tree_on_main": "b311275c1dd0ba6902d477d8be72318632a1963c",
                     "fuzzy_match_sha256": sha256(P / "overlay/c125376-leaf/tools/fuzzy_match.py")},
    "both": {"composition": "c54575 + c125376-leaf", "merge": "clean (fuzzy_match.py hunks disjoint)",
             "fuzzy_match_sha256": sha256(P / "overlay/both/tools/fuzzy_match.py")},
    "leaf+fold": {"composition": "c125376-leaf + fold-in", "fuzzy_match_sha256": sha256(P / "overlay/leaf+fold/tools/fuzzy_match.py")},
    "both+fold": {"composition": "c54575 + c125376-leaf + fold-in (1 line)", "fuzzy_match_sha256": sha256(P / "overlay/both+fold/tools/fuzzy_match.py")},
    "c126502": {"pr": 126502, "author": "Finn763", "head": "6d4fbff950", "merge": "clean",
                "merge_tree_on_main": "708fe568a2a816be361dea96b431e3f28c7fa44a",
                "note": "found by the dedupe search during this run (not in the selection): block_anchor single-candidate threshold 0.50 -> 0.70; closes #93698",
                "fuzzy_match_sha256": sha256(P / "overlay/c126502/tools/fuzzy_match.py")},
    "c126502+leaf+fold": {"composition": "c126502 + c125376-leaf + fold-in", "fuzzy_match_sha256": sha256(P / "overlay/c126502+leaf+fold/tools/fuzzy_match.py")},
    "c93717": {"pr": 93717, "author": "fangliquanflq", "head": "3c4c81f706",
               "merge": "CONFLICTING in tools/fuzzy_match.py (written against the pre-refactor module); not run, not hand-ported. "
                        "Core change is the same flat 0.70 block_anchor floor as #126502, plus a hunk that keeps escape-drift diagnostics for weak anchors."},
}
fold = keep(P / "foldin.diff", "patches/foldin-125376-stripped-guard.diff")

ab = {}
for arm in ["base", "c54575", "c125376-leaf", "both", "leaf+fold", "both+fold", "c126502", "c126502+leaf+fold"]:
    ab[arm] = contract_counts(arm)
    first = runs.get(f"runs/{arm}/proof.rep1.log")
    ab[arm]["carrier_tests_cross_applied"] = {f: first["files"].get(f) for f in
                                              ["tests/tools/test_fuzzy_match.py", "tests/tools/test_file_tools_live.py"]
                                              if f in first["files"]} or "not run on this arm (contract file only)"

adjacent = {arm: runs[f"runs/{arm}/adjacent.rep1.log"]["files"] for arm in ["base", "c54575", "c125376-leaf", "both+fold", "c126502"]}
adj_tot = {arm: {k: sum(v[k] for v in files.values()) for k in ("passed", "skipped", "failed")} for arm, files in adjacent.items()}

sab = {}
for m in ["floor", "single_line", "foldin"]:
    r = runs[f"runs/both+fold/sabotage-{m}.rep1.log"]
    sab[m] = {"reverted": {"floor": "#54575 content-divergence guard in fuzzy_find_and_replace",
                           "single_line": "#125376 single-line refusal in _strategy_context_aware",
                           "foldin": "fold-in only (stripped-pattern test back to n == 1)"}[m],
              "contract": r["files"][CONTRACT], "red_again": r["files"][CONTRACT]["failed"] > 0,
              "carrier_tests": {f: r["files"][f] for f in ["tests/tools/test_fuzzy_match.py", "tests/tools/test_file_tools_live.py"]},
              "failed_ids": r["failed_ids"], "log": r["log"]}

final = {"intermediate_head": {"base": runs["runs/base/final.rep1.log"], "both+fold": runs["runs/both+fold/final.rep1.log"],
                               "sabotage_foldin": runs["runs/both+fold/final-sab-foldin.rep1.log"]},
         "final_head": {**{f"base_rep{i}": runs[f"runs/base/final2.rep{i}.log"] for i in (1, 2, 3)},
                        **{f"both+fold_rep{i}": runs[f"runs/both+fold/final2.rep{i}.log"] for i in (1, 2, 3)},
                        **{f"sabotage_{m}": runs[f"runs/both+fold/final2-sab-{m}.rep1.log"] for m in ("floor", "single_line", "foldin")}}}

cross = json.loads((P / "probe_cross.json").read_text())
probe = json.loads((P / "probe_out.json").read_text())

for s in ["probe_arms.py", "probe_cross.py", "meter_probe.py", "run_arm.sh", "run_e01.sh", "sabotage.py",
          "resolve_drop_base.py", "make_receipts.py", "probe_trap_variant.py"]:
    keep(P / s, f"scripts/{s}")
keep(P / "probe_cross.json", "probes/probe_cross.json")
keep(P / "probe_out.json", "probes/probe_arms.json")

f01 = {
    "schema": "xf.receipt.v1 (hand-run; xf executor not built)",
    "id": "F01/r20261001-01",
    "staging": "edit-fuzzy-wrong-region",
    "kind": "carrier-ab",
    "tier": "T1 ($0): real ShellFileOperations + LocalEnvironment (bash in tmp dir), no model, no provider, no network",
    "origin_refs": ["NousResearch/hermes-agent#54572", "NousResearch/hermes-agent#111116", "NousResearch/hermes-agent#93698"],
    "base_revision": {"tested": MAIN_TESTED, "final": MAIN_FINAL, "factory_base": FACTORY_BASE,
                      "edit_path_blobs_identical_across_all_three": BLOBS},
    "head_revision": {"tested": COMMIT_TESTED, "final": COMMIT_FINAL, "intermediate": COMMIT_INTERMEDIATE, "note": "tested = first build on 572e4f4fad; intermediate = cherry-pick onto 234badf401 (0 edit-path drift); final = same tree with two test comments reworded (#111116 battery -> #111127 battery), re-proven 3/3 RED, 3/3 GREEN, 3/3 per-hunk sabotage on the final head"},
    "command": "receipts/raw/scripts/run_arm.sh <arm> <rep> proof tests/tools/test_fuzzy_match_wrong_region.py tests/tools/test_fuzzy_match.py tests/tools/test_file_tools_live.py  "
               "(wraps: HOME=$S/testhome-st-edit-fuzzy-wrong-region HERMES_HOME=$HOME/.hermes HERMES_PYTHON=<venv python> bash scripts/run_tests.sh -j 2 <files> -q -m 'not live and not integration')",
    "arms": arms_def,
    "inject": {"contract_test": f"tests/tools/test_fuzzy_match_wrong_region.py @ {COMMIT_FINAL[:10]} (blob {BLOBS['tests/tools/test_fuzzy_match_wrong_region.py'][:10]}; tested-head blob 42fff91290 differs only in two comments)",
               "carrier_tests_cross_applied": "union of #54575 + #125376 test additions (test_fuzzy_match.py, test_file_tools_live.py) applied to every arm except the c126502 arms",
               "fold_in": fold},
    "gates": {
        "red": {"arm": "base", "result": "PASS", "label": "OBSERVED",
                "observed": "8 failed / 10 (all 8 wrong-region cells), 2 near-miss cells pass; 3/3 reps agree on the tested head and 3/3 on the final head ea25f06132",
                "marker": "wrong region replaced via block_anchor|context_aware: count=1, error=None",
                "failed_ids": [i for i in ab["base"]["failed_ids_rep1_all_files_in_run"] if "wrong_region" in i]},
        "green": {"arm": "both+fold", "result": "PASS", "label": "OBSERVED", "reps_agree": "3/3 on the tested head, 1/1 intermediate, 3/3 on the final head",
                  "observed": "10/10 contract; carrier tests 61/61 + 16/16"},
        "no_single_carrier_green": {"c54575": "4/10 (block_anchor fixed; 3 single-line cases x 2 modes still replaced)",
                                    "c125376-leaf": "6/10 (single-line fixed; block_anchor x2 and trailing newline x2 still replaced)",
                                    "both": "8/10 (trailing-newline bypass x2 still replaced)",
                                    "leaf+fold": "8/10 (block_anchor x2 still replaced)",
                                    "c126502": "4/10 (block_anchor fixed)",
                                    "c126502+leaf+fold": "10/10 (3/3)"},
        "sabotage": sab,
        "adjacent": {"files": sorted(adjacent["base"]), "per_arm_totals": adj_tot,
                     "identical_to_base": {arm: adjacent[arm] == adjacent["base"] for arm in adjacent},
                     "c126502_failures": runs["runs/c126502/adjacent.rep1.log"]["failed_ids"],
                     "note": "c126502 needs its own edits to two existing escape-drift tests; with main's tests unchanged it fails them (weak-anchor escape-drift diagnostic downgraded to plain no-match)"},
        "flaky": False,
        "guards": "F14 standing set NOT run (factory-replay-gate harness not built here)",
        "informativeness": "N_A", "credit": None, "cache_read_ratio": {"status": "N_A"},
    },
    "ab_table": ab,
    "cross_application_block_anchor_carriers": {"label": "OBSERVED (direct calls)", "result": cross,
                                                "summary": "#54575 refuses both #93717's and #126502's Markdown repros and keeps both escape-drift diagnostics; #126502 refuses the repros but downgrades both diagnostics to plain no-match"},
    "residual_probe": {"label": "OBSERVED (direct calls)", "result": probe,
                       "summary": "with both+fold: CRLF and leading-newline variants also refused; a 2-line wrong-token anchor ('def normalize(value):' + 'return value.trim()') still applies via context_aware on every arm (out of scope; #125376 states it deliberately)"},
    "final_head_check": {stage: {k: {"head": v["meta"].get("head"), "files": v["files"], "failed_ids": v["failed_ids"], "log": v["log"]} for k, v in group.items()} for stage, group in final.items()},
    "env": ENV,
    "evidence_class": {"local": True, "ci": "none (statusCheckRollup empty on #54575/#125376/#126502)", "simulation": False, "runtime": False, "kind": "mechanism"},
    "not_tested": ["model behaviour after a refusal (E02, deferred)", "Windows/CRLF files on disk (only CRLF in old_string probed)",
                   "#93717 (CONFLICTING, not hand-ported)", "#125376 full head (CONFLICTING)", "F14 standing guard set",
                   "bwrap sandbox / blind verifier"],
    "verdict": "KEEP",
    "carrier_choice": {"winner": "#54575 (block_anchor) + #125376 fix commit 5f3f5896a4 (single-line) + 1-line fold-in on #125376",
                       "why": "No single open PR closes all four cases. #54575 keeps adjacent tests identical and preserves escape-drift diagnostics, "
                              "and also refuses the #93717/#126502 repros; #126502 fails two existing escape-drift tests unless they are edited; #93717 conflicts. "
                              "#125376's guard misses old_string with a trailing newline; testing the stripped pattern closes it (sabotage of that line alone re-REDs only the contract test)."},
    "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0, "label": "OBSERVED (runner per-file wall times, summed over every log incl. adjacent/sabotage)",
                       "test_file_wall_s_sum": round(sum(
                           float(x) for log in (P / "runs").rglob("*.log")
                           for x in re.findall(r"\] [✓✗] \S+ \([^)]*?, ([\d.]+)s\)", log.read_text(encoding="utf-8"))), 1),
                       "runs": len(runs)},
    "ai_assistance": "Claude Code (Opus 5.5) wrote the contract test, probes and receipts",
    "privacy": "public-aggregate (synthetic fixtures only)",
}
(RC / "F01-r20261001-01.json").write_text(json.dumps(f01, indent=1) + "\n", encoding="utf-8")

# ---------------- E01 battery ----------------
e01_arms = {}
for arm in ["base", "c54575", "c125376-leaf", "both", "both+fold"]:
    data = json.loads((P / f"e01/{arm}.json").read_text())
    rec = keep(P / f"e01/{arm}.json", f"e01/{arm}.json")
    keep(P / f"e01/{arm}.report.txt", f"e01/{arm}.report.txt")
    keep(P / f"e01/{arm}.tripwire.txt", f"e01/{arm}.tripwire.txt")
    e01_arms[arm] = {a: {"score": f"{sum(r['passed'] for r in recs)}/{len(recs)}",
                         "missing_anchor": next(r for r in recs if r["task_id"] == "missing_anchor")["outcome"] +
                                           " (" + next(r for r in recs if r["task_id"] == "missing_anchor")["reason"][:40] + ")"}
                     for a, recs in data["arms"].items()}
    e01_arms[arm]["scorecard"] = rec
    e01_arms[arm]["fuzzy_match_sha256"] = arms_def[arm]["fuzzy_match_sha256"]
e01 = {
    "schema": "xf.receipt.v1 (hand-run)",
    "id": "E01/r20261001-01",
    "staging": "edit-fuzzy-wrong-region",
    "tier": "T0 ($0): deterministic battery, direct fuzzy_find_and_replace calls, no model",
    "question": "Does the #111127 battery at its current head reproduce the 6/6 vs 5/6 scorecard on current main, and does it move on the carrier arms?",
    "inputs": {"battery": "NousResearch/hermes-agent#111127 head 5444b1a2a83d8c9a239a98d01f91156dd1d73f96 (evals/edittool, git archive, unmodified)",
               "main": MAIN_TESTED, "fuzzy_match_blob": BLOBS["tools/fuzzy_match.py"],
               "note": "fuzzy_match.py blob is identical on e496ccc7d7 (factory base), 572e4f4fad (tested) and 234badf401 (final)"},
    "command": "receipts/raw/scripts/run_e01.sh base c54575 c125376-leaf both both+fold  "
               "(per arm: python evals/edittool/runner.py --label <arm> --output <json>; python evals/edittool/report.py <json>; python evals/edittool/test_edittool.py)",
    "results": e01_arms,
    "label": "OBSERVED",
    "findings": [
        "Main reproduces KeyArgo's 2026-09-16 scorecard (taken on head 602e596389b) at head 5444b1a2a8: str_replace 6/6, hermes_patch 5/6, missing_anchor applied via context_aware.",
        "The score does not move on any fixed arm: with #125376's guard, missing_anchor becomes no_change, because the trap's new_string 'return value' is a substring of 'return value.strip()' and the already-applied check reports a success-shaped no-op. The file is untouched, but expected 'rejected' is still DRIFT.",
        "So the battery as written cannot tell main from a fixed tree by score. A new_string that is not already in the file (the contract test uses 'return value.casefold()') makes the trap sensitive.",
        "The test_edittool.py tripwire passes on every arm (it asserts the last task is NOT passed).",
    ],
    "trap_variant_check": {"label": "OBSERVED (direct calls emulating arms._hermes_replace line for line; battery files not modified)",
                           "command": "python receipts/raw/scripts/probe_trap_variant.py <arms dir> base,c54575,c125376-leaf,both,both+fold",
                           "result": json.loads((P / "probe_trap_variant.json").read_text()),
                           "raw": keep(P / "probe_trap_variant.json", "probes/probe_trap_variant.json"),
                           "summary": "with new_string 'return value.casefold()' the trap is applied on main and rejected on every arm carrying #125376's guard, so the score would move 5/6 -> 6/6"},
    "attribution": "Battery author: KoNit-K (#111127). The 6/6 vs 5/6 scorecard was posted by KeyArgo (third-party run).",
    "env": ENV,
    "verdict": "KEEP (reproduced; battery insensitivity recorded)",
    "not_tested": ["toolperf_abeval model arm (E02)"],
}
(RC / "E01-r20261001-01.json").write_text(json.dumps(e01, indent=1) + "\n", encoding="utf-8")

# ---------------- M01 meter labels ----------------
m01 = {"schema": "xf.receipt.v1 (hand-run)", "id": "M01/r20261001-01", "staging": "edit-fuzzy-wrong-region",
       "tier": "T1 ($0): patch_replace inside the shared-metrics edit probe, mapped with file_edit_fields; no metrics store written",
       "question": "Are the hermes.file_edit.count outcome and strategy label sets unchanged, and what does the meter record per case?",
       "command": "per arm: overlay tools/fuzzy_match.py; python receipts/raw/scripts/meter_probe.py <worktree>",
       "results": {}, "label": "OBSERVED"}
for arm in ["base", "c54575", "c125376-leaf", "both", "both+fold"]:
    d = json.loads((P / f"m01/{arm}.json").read_text())
    rec = keep(P / f"m01/{arm}.json", f"m01/{arm}.json")
    m01["results"][arm] = {"cases": {c: f"{v['outcome']}/{v['match_strategy']}" for c, v in d["cases"].items()},
                           "labels_in_contract": all(v["labels_in_contract"] for v in d["cases"].values()), "raw": rec}
base_d = json.loads((P / "m01/base.json").read_text())
m01["label_sets_identical_across_arms"] = all(
    json.loads((P / f"m01/{a}.json").read_text())[k] == base_d[k]
    for a in ["c54575", "c125376-leaf", "both", "both+fold"] for k in ("strategy_labels", "outcome_labels", "strategies_chain"))
m01["findings"] = ["Label sets (match_strategy, outcome) and the strategy chain are identical on every arm.",
                   "On main the meter counts every wrong-region edit as applied/block_anchor or applied/context_aware, the same bucket as a legitimate rescue. On both+fold they move to no_match/none; near-miss labels are unchanged."]
m01["env"] = ENV
m01["verdict"] = "KEEP"
(RC / "M01-r20261001-01.json").write_text(json.dumps(m01, indent=1) + "\n", encoding="utf-8")

# manifest of receipt hashes
man = {p.name: sha256(p) for p in sorted(RC.glob("*-r*.json"))}
(RC / "SHA256SUMS.json").write_text(json.dumps(man, indent=1) + "\n", encoding="utf-8")
print(json.dumps(man, indent=1))
print("adjacent totals", adj_tot)
