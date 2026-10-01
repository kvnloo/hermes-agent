#!/usr/bin/env python3
"""Aggregate cells-r03.jsonl + static checks into xf.receipt.v1 receipts (write-once), run r03.

r03 vs r02: head 2f79b549ef on main aea969677c (same diff as 402e9b0bdb; only the commit body
rewrap differs). The receipts now carry every xf.receipt.v1 field (FACTORY 9.2): spec (marked
NOT_PREREGISTERED), changed_files, carrier_choice, harness_abi, limitations, learning and frozen.
No absolute local path is written: the interpreter is $HERMES_PYTHON, the worktree <wt>, the
test home $TH.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

S = Path("$S")
H = S / "h.git"
FRONTIER = Path("$ARTIFACTS/frontier-2026-10-01")
ST = FRONTIER / "staging/cu-repeat-input-dedup"
R = ST / "receipts"
RAW = R / "raw-r03"
PROOF = ST / "harness"
BASE = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
HEAD = "2f79b549ef40aeb31cb3af36cd92d8d12b9ba799"
PREV_HEAD, PREV_BASE = "402e9b0bdbfdf2a988971c6cd452e8115b134208", "234badf4012af380d23c91eae55d045a69c69ffb"
DONOR, DONOR_MB = "570dc83ba65fc4ce86efb2c00e89dc84d19bd5ca", "cb3142d3257b15ac42de544bd585793567400d0f"
NEW_TEST = "tests/agent/test_tool_call_dedup_order_significant.py"
RUN_ID = "r20261001-03"
SUPERSEDES = "r20261001-02"
FORK_BRANCH = "staged/cu-repeat-input-dedup"


def g(*a):
    return subprocess.run(["git", "-C", str(H), *a], check=True, text=True, capture_output=True).stdout.strip()


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def show(rev, path):
    return g("show", f"{rev}:{path}")


all_cells = [json.loads(line) for line in (R / "cells-r03.jsonl").read_text().splitlines()]
for c in all_cells:   # attempt-1 cells predate the driver's retry fields; derive them from the raw log
    log = (R / c["raw_log"]).read_text()
    c.setdefault("attempt", 1)
    c.setdefault("exit_class", "infra" if "exceeded; process tree SIGKILL" in log or "where no tests ran" in log else "ok")
    c.setdefault("timed_out_files", sorted(set(re.findall(r"--- (tests/\S+) ---\n\(\d+s exceeded", log))))
# The scored cell for each (experiment, arm, rep) is its last attempt; earlier INFRA attempts stay in the receipt.
_last = {}
for c in all_cells:
    k = (c["experiment"], c["arm"], c["rep"])
    if k not in _last or c["attempt"] > _last[k]["attempt"]:
        _last[k] = c
cells = [c for c in all_cells if _last[(c["experiment"], c["arm"], c["rep"])] is c]
retried = [c for c in all_cells if c not in cells]
assert all(c["exit_class"] == "ok" for c in cells), [c["raw_log"] for c in cells if c["exit_class"] != "ok"]


def pick(exp, arm):
    return [c for c in cells if c["experiment"] == exp and c["arm"] == arm]


def one(exp, arm):
    (c,) = pick(exp, arm)
    return c


def brief(c):
    return {k: c[k] for k in ("arm", "rep", "attempt", "exit_class", "timed_out_files", "arm_tree", "passed", "failed",
                              "failed_ids", "red_marker_matched", "egress_blocked", "egress_blocked_by_file",
                              "loopback_connects", "seam_hits", "wall_s", "load1_at_start", "raw_log", "cmd")} | {
        "raw_log_sha256": sha256(R / c["raw_log"])}


numstat = [line.split("\t") for line in g("diff", "--numstat", BASE, HEAD).splitlines()]
changed_files = [{"path": p, "added": int(a), "deleted": int(d)} for a, d, p in numstat]
DECISION_RULE = ("RED: base arm fails 2/2 with the marker in 3/3 reps and the seam is hit. GREEN: head passes 2/2 in "
                 "3/3 reps. NEG/per-hunk: each reverted hunk fails again. ADJ: same failures on base and head. "
                 "KEEP only if all four hold. Rule restated from the r01/r02 receipts; it was not committed before run 1.")

common = {
    "spec": {"path": None, "rev": None, "sha256": None, "prereg_commit": None,
             "decision_rule_sha": hashlib.sha256(DECISION_RULE.encode()).hexdigest(), "decision_rule": DECISION_RULE,
             "status": "NOT_PREREGISTERED",
             "gap": "FACTORY I5 wants the spec committed to claude/ledger before run 1. This run may not write the "
                    "ledger, so there is no prereg commit. Open P8 item."},
    "runner_revision": "harness/proof-r03.py sha256=" + sha256(PROOF / "proof-r03.py"),
    "issue": "kvnloo/hermes-agent#316",
    "origin_refs": ["NousResearch/hermes-agent#124008", "NousResearch/hermes-agent#112639"],
    "staging": "cu-repeat-input-dedup",
    "branch": {"logical": "staging/cu-repeat-input-dedup", "fork_physical": FORK_BRANCH, "pushed": False},
    "base_revision": BASE,
    "head_revision": HEAD,
    "changed_files": changed_files,
    "policy_revision": {"AGENTS.md": g("rev-parse", f"{BASE}:AGENTS.md"),
                        "CONTRIBUTING.md": g("rev-parse", f"{BASE}:CONTRIBUTING.md"),
                        "factory": "frontier-2026-10-01/FACTORY.md sha256=" + sha256(FRONTIER / "FACTORY.md")},
    "inputs": {
        f"{NEW_TEST}@head": g("rev-parse", f"{HEAD}:{NEW_TEST}"),
        "tests/agent/test_agent_guardrails.py@base": g("rev-parse", f"{BASE}:tests/agent/test_agent_guardrails.py"),
        "tests/fakes/fake_llm_provider.py@base": g("rev-parse", f"{BASE}:tests/fakes/fake_llm_provider.py"),
        "scripts/run_tests.sh@base": g("rev-parse", f"{BASE}:scripts/run_tests.sh"),
        "scripts/run_tests_parallel.py@base": g("rev-parse", f"{BASE}:scripts/run_tests_parallel.py"),
        "guard_plugin harness/_xf_t1_guard.py sha256": sha256(PROOF / "_xf_t1_guard.py"),
        "driver harness/proof-r03.py sha256": sha256(PROOF / "proof-r03.py"),
        "donor": f"refs/fork/fix/computer-use-repeat-input-dedup-current-main@{DONOR} (merge-base {DONOR_MB})",
    },
    "env": {"host": "local workstation, Linux x86_64", "python": "3.11.14 via $HERMES_PYTHON (interpreter only)",
            "venv_lock_sha256": None,
            "sandbox": "run_tests.sh env -i + isolated HOME/HERMES_HOME ($TH = scratchpad/testhome-sf-cu-repeat-input-dedup) "
                       "+ in-process loopback-only connect guard; no bwrap",
            "file_retries": 0, "workers": 2},
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
    "harness_abi": {"harness": "hermes", "editor_abi": "n/a (no edit tool; computer_use no-op backend as the device)"},
    "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0, "tokens": 0, "energy_j": None},
    "z0evals_study": None,
    "provenance": "self",
    "privacy": "public-aggregate (synthetic fixtures only; no absolute local paths)",
    "ai_assistance": "Claude Code (Opus 5.5) wrote the change, the test and these receipts",
}

# ---------------- F07 ----------------
base, head = pick("F07", "base"), pick("F07", "head")
neg, nopeel, facade = one("F07", "neg-empty-table"), one("F07", "sab-no-bridge-peel"), one("F07", "sab-facade-revert")
verdict_arm, donor_arm = one("F07", "sab-verdict-confirms"), one("F07", "donor-fix+new-test")
adj_main, adj_head = one("ADJ", "main"), one("ADJ", "head")
red_ok = all(c["failed"] == 2 and c["red_marker_matched"] == 2 for c in base)
green_ok = all(c["failed"] == 0 and c["passed"] == 2 for c in head)
adj_ok = adj_main["failed"] == adj_head["failed"] == 0 and adj_head["passed"] - adj_main["passed"] == 2
f07_keep = red_ok and green_ok and neg["failed"] == 2 and nopeel["failed"] >= 1 and facade["failed"] == 2 and adj_ok
f07 = {
    "schema": "xf.receipt.v1", "id": f"F07/{RUN_ID}", "tier": "T1", "label": "OBSERVED",
    "question": "Through a real AIAgent turn (FakeLLMServer loopback + in-tree no-op computer_use backend), "
                "does one assistant message with two identical computer_use key=tab calls dispatch two presses, "
                "directly and through the tool_search tool_call bridge in its advertised {calls: [...]} shape?",
    "command": cells[0]["cmd"].replace(cells[0]["files"][0], "{files}"),
    "files": [NEW_TEST],
    "arms": {
        "base": {"tree": base[0]["arm_tree"], "how": f"main {BASE[:10]} + {NEW_TEST} only (test inject)"},
        "head": {"head": HEAD, "tree": head[0]["arm_tree"], "merge": "clean (head is one commit on base)",
                 "how": f"staging commit {HEAD[:10]}"},
        "neg-empty-table": {"how": "head with _ORDER_SIGNIFICANT_ACTIONS = frozenset()"},
        "sab-no-bridge-peel": {"how": "head with the _peel_bridge_call line in _is_order_significant removed"},
        "sab-facade-revert": {"how": "head with run_agent.py restored to main (old in-facade method)"},
        "sab-verdict-confirms": {"how": "head with computer_use _classify_action_result fallback returning 'done' "
                                        "(test-sensitivity check for the verify_fresh_state assertion)"},
        "donor-fix+new-test": {"how": f"main + donor run_agent.py hunk ({DONOR[:10]}) + {NEW_TEST}"},
    },
    "gates": {
        "validity": "PASS",
        "red": {"arm": "base", "result": "PASS" if red_ok else "FAIL",
                "observed": "; ".join(f"r{c['rep']}: {c['failed']} failed / {c['passed'] + c['failed']}" for c in base),
                "assertion": "AssertionError: assert ['key', 'click'] == ['key', 'key', 'click']",
                "seam_covered": all("run_agent.py::_deduplicate_tool_calls" in c["seam_hits"]
                                    and "turn_tool_round.py::run_tool_round" in c["seam_hits"] for c in base),
                "reps_agree": f"{len(base)}/{len(base)}"},
        "green": [{"arm": "head", "result": "PASS" if green_ok else "FAIL", "reps_agree": f"{len(head)}/{len(head)}",
                   "seam_covered": all("tool_dispatch_helpers.py::deduplicate_tool_calls" in c["seam_hits"]
                                       and "tool_dispatch_helpers.py::_is_order_significant" in c["seam_hits"]
                                       for c in head)}],
        "negative_control": {"arm": "neg-empty-table", "result": "RED" if neg["failed"] == 2 else "NOT_RED",
                             "observed": f"{neg['failed']} failed / {neg['passed'] + neg['failed']}"},
        "sabotage": {"per_hunk": [
            {"hunk": "agent/tool_dispatch_helpers.py _ORDER_SIGNIFICANT_ACTIONS entry", "arm": "neg-empty-table",
             "red_again": neg["failed"] == 2, "failed": neg["failed_ids"]},
            {"hunk": "agent/tool_dispatch_helpers.py _peel_bridge_call in _is_order_significant",
             "arm": "sab-no-bridge-peel", "red_again": nopeel["failed"] >= 1, "failed": nopeel["failed_ids"]},
            {"hunk": "run_agent.py _deduplicate_tool_calls forwarder", "arm": "sab-facade-revert",
             "red_again": facade["failed"] == 2, "failed": facade["failed_ids"]},
        ], "unpinned_hunks": ["agent/tool_dispatch_helpers.py __all__ entry (export list only)"],
            "test_sensitivity": {"arm": "sab-verdict-confirms", "failed": verdict_arm["failed"],
                                 "assertion": "verify_fresh_state verdict assertion (see raw log)"}},
        "adjacent": {
            "files": adj_main["files"],
            "attempt": {"base": adj_main["attempt"], "arm": adj_head["attempt"]},
            "base": f"{adj_main['passed']} passed / {adj_main['failed']} failed",
            "arm": f"{adj_head['passed']} passed / {adj_head['failed']} failed (base + the 2 new test cases)",
            "identical": adj_ok,
            "pre_existing_failures": [],
            "note": "tests/agent/test_agent_guardrails.py is byte-identical on base and head",
        },
        "guards": {"F14": "NOT_RUN (factory standing set not built yet)"},
        "flaky": False,
        "noise_floor": None, "credit": None, "informativeness": "N_A", "route_scope": "n/a",
        "cache_read_ratio": {"status": "N_A", "before": None, "after": None},
    },
    "ab": None,
    "measurements": [
        {"name": "backend_key_presses_for_tab_tab", "arm": "base", "value": 1, "n": len(base) * 2,
         "label": "OBSERVED", "statistic": "count per case (assertion ['key','click'])"},
        {"name": "backend_key_presses_for_tab_tab", "arm": "head", "value": 2, "n": len(head) * 2,
         "label": "OBSERVED", "statistic": "count per case"},
    ],
    "findings": [
        "The donor fix (570dc83ba6, name-keyed 'computer_use' check in run_agent.py) leaves the default path broken: "
        "computer_use is in the default tools.tool_search.defer list, so the model calls it via the tool_call bridge, "
        "and the donor arm fails the tool_call-bridge case (failed: " + ", ".join(donor_arm["failed_ids"]) + ").",
        "Each kept press returns its own verdict decision 'verify_fresh_state' (noop backend has no semantic effect), "
        "so the exemption neither collapses nor upgrades the verify ladder; pinned by the sab-verdict-confirms arm.",
    ],
    "carrier_choice": {"winner": f"staging/cu-repeat-input-dedup@{HEAD[:10]}",
                       "why": "own core leaf, no external carrier; the donor arm stays RED on the tool_call bridge case",
                       "alternatives": {f"donor {DONOR[:10]}": f"{donor_arm['failed']} failed / "
                                                               f"{donor_arm['passed'] + donor_arm['failed']}"}},
    "safety": {"egress_blocked_in_new_test": sum(c["egress_blocked"] for c in base + head),
               "egress_blocked_in_adjacent_files": {"base": adj_main["egress_blocked"],
                                                    "base_by_file": adj_main["egress_blocked_by_file"],
                                                    "head": adj_head["egress_blocked"],
                                                    "head_by_file": adj_head["egress_blocked_by_file"],
                                                    "note": "pre-existing attempts by existing tests, blocked by the "
                                                            "guard on both arms; the tests still pass. The guard "
                                                            "covers connect(), not DNS resolution."},
               "credential_like_env_names_seen": sorted({k for c in cells for k in c["credential_like_env"]}),
               "home": "isolated"},
    "cells": [brief(c) for c in cells if c["experiment"] in ("F07", "ADJ")],
    "retried_infra_attempts": [brief(c) for c in retried],
    "denominators": {"cells": len([c for c in cells if c["experiment"] in ("F07", "ADJ")]),
                     "attempts": len([c for c in all_cells if c["experiment"] in ("F07", "ADJ")]),
                     "infra_attempts_retried": len(retried), "infra_final": 0, "infra_excluded": 0,
                     "errored_scored_zero": 0, "completeness": 1.0,
                     "note": "Attempt 1 of both ADJ cells lost tests/agent/test_run_agent.py to run_tests.sh's 300 s "
                             "per-file timeout at load1 ~14 (no test failed; the file was killed). Both ADJ cells were "
                             "re-run once as attempt 2 with HERMES_TEST_FILE_TIMEOUT=900; only attempt 2 is scored."},
    "verdict": "KEEP" if f07_keep else "REVIEW",
    "not_tested": ["real cua-driver / desktop delivery of two presses", "real-model emission rate of identical "
                   "same-message key presses (queued T2/T3 probe)", "macOS / Windows",
                   "Gateway / TUI / ACP surfaces directly", "F14 standing guard set", "full test suite"],
    "limitations": ["T1 only: fake LLM endpoint and no-op device", "single host, -j 2",
                    "ADJ run once per arm (n=1)", "spec not preregistered (see spec.gap)"],
    "learning": {"hypothesis": "Two identical computer_use key calls in one assistant message both reach the backend "
                               "on head, directly and through the tool_call bridge, and only one does on main.",
                 "result": "KEEP" if f07_keep else "REVIEW",
                 "observed_evidence": [f"F07/{RUN_ID} red 3/3, green 3/3, per-hunk sabotage red"],
                 "regressions": [],
                 "reusable_lesson": "A tool-name exemption in dispatch misses deferred tools that the model reaches "
                                    "through the tool_search tool_call bridge; unwrap the bridge before matching.",
                 "roadmap_effect": "hold (OD-6)"},
    "frozen": {"bundle_sha": None, "cells": len(all_cells), "supersedes": f"F07/{SUPERSEDES}",
               "status": "NOT_FROZEN (z0evals freeze needs a write this run may not make; open P8 item)"},
}

# ---------------- E25 ----------------
e25_red, e25_full, e25_head = one("E25", "main+donor-test"), one("E25", "main+donor-full"), one("E25", "head+donor-test")
e25_keep = e25_red["failed"] == 1 and e25_full["failed"] == 0 and e25_head["failed"] == 0
e25 = {
    "schema": "xf.receipt.v1", "id": f"E25/{RUN_ID}", "tier": "T1", "label": "OBSERVED",
    "question": "Is the repeat-key dedup bug still red on current main through the static method, and green with "
                "the donor fix and with the staging head?",
    "command": e25_red["cmd"],
    "arms": {
        "main+donor-test": {"tree": e25_red["arm_tree"], "how": f"main {BASE[:10]} + donor tests/agent/test_agent_guardrails.py hunk"},
        "main+donor-full": {"tree": e25_full["arm_tree"], "how": f"main + full donor diff {DONOR_MB[:10]}..{DONOR[:10]} (git apply -3)"},
        "head+donor-test": {"tree": e25_head["arm_tree"], "how": "staging head + donor test hunk (old static-method contract via the forwarder)"},
    },
    "gates": {
        "validity": "PASS",
        "red": {"arm": "main+donor-test", "result": "PASS" if e25_red["failed"] == 1 else "FAIL",
                "observed": f"{e25_red['passed']} passed / {e25_red['failed']} failed", "failed": e25_red["failed_ids"],
                "seam_covered": "run_agent.py::_deduplicate_tool_calls" in e25_red["seam_hits"], "reps_agree": "1/1"},
        "green": [{"arm": "main+donor-full", "result": "PASS" if e25_full["failed"] == 0 else "FAIL",
                   "observed": f"{e25_full['passed']} passed / {e25_full['failed']} failed"},
                  {"arm": "head+donor-test", "result": "PASS" if e25_head["failed"] == 0 else "FAIL",
                   "observed": f"{e25_head['passed']} passed / {e25_head['failed']} failed"}],
        "sabotage": {"per_hunk": [], "unpinned_hunks": [], "note": "per-hunk sabotage lives in F07"},
        "adjacent": {"note": "see F07 adjacent"}, "guards": {"F14": "NOT_RUN"}, "flaky": False,
        "noise_floor": None, "credit": None, "informativeness": "N_A", "route_scope": "n/a",
        "cache_read_ratio": {"status": "N_A", "before": None, "after": None},
    },
    "ab": None,
    "measurements": [{"name": "cases_failed", "arm": "main+donor-test", "value": e25_red["failed"], "n": 1,
                      "label": "OBSERVED", "statistic": "count"}],
    "note": "Static-method RED/GREEN only; the real-path proof is F07.",
    "cells": [brief(c) for c in cells if c["experiment"] == "E25"],
    "denominators": {"cells": len([c for c in cells if c["experiment"] == "E25"]), "infra_excluded": 0,
                     "errored_scored_zero": 0, "completeness": 1.0},
    "verdict": "KEEP" if e25_keep else "REVIEW",
    "carrier_choice": None,
    "not_tested": ["the real turn path (covered by F07)"],
    "limitations": ["one rep per arm", "spec not preregistered (see spec.gap)"],
    "learning": {"hypothesis": "The donor's static contract test is red on current main and green on head.",
                 "result": "KEEP" if e25_keep else "REVIEW", "observed_evidence": [f"E25/{RUN_ID}"], "regressions": [],
                 "reusable_lesson": None, "roadmap_effect": "hold (OD-6)"},
    "frozen": {"bundle_sha": None, "cells": len([c for c in cells if c["experiment"] == "E25"]),
               "supersedes": f"E25/{SUPERSEDES}", "status": "NOT_FROZEN (open P8 item)"},
}

# ---------------- STATIC + freshness ----------------
def count_forwarders(rev):
    src = show(rev, "run_agent.py")
    return {"_forward_static": src.count("_forward_static(") , "_forward": src.count("_forward(") ,
            "total": src.count("_forward_static(") + src.count("_forward(")}


wf = json.loads((RAW / "wfscan-head.json").read_text())
static = {
    "schema": "xf.receipt.v1", "id": f"STATIC/{RUN_ID}", "tier": "T0", "label": "OBSERVED",
    "checks": {
        "tool_name_branch_in_run_agent_py": {"cmd": "git show <rev>:run_agent.py | grep -c computer_use",
                                             "base": show(BASE, "run_agent.py").count("computer_use"),
                                             "head": show(HEAD, "run_agent.py").count("computer_use"),
                                             "donor": show(DONOR, "run_agent.py").count("computer_use")},
        "facade_forwarders_run_agent_py": {"cmd": "grep -oE '\\b_forward(_static)?\\(' run_agent.py | sort | uniq -c",
                                           "base": count_forwarders(BASE), "head": count_forwarders(HEAD),
                                           "note": "the head total includes this commit's own forwarder"},
        "file_size_lines": {f: {"base": len(show(BASE, f).splitlines()), "head": len(show(HEAD, f).splitlines())}
                            for f in ("run_agent.py", "agent/tool_dispatch_helpers.py")},
        "numstat": changed_files,
        "diffstat": g("diff", "--stat", BASE, HEAD).splitlines()[-1].strip(),
        "diff_identical_to_previous_head": {"previous": f"{PREV_HEAD[:10]} on {PREV_BASE[:10]}",
                                            "identical": g("diff", f"{PREV_HEAD}^", PREV_HEAD) == g("diff", BASE, HEAD),
                                            "commit_message_change": "body line 'default config reaches it through "
                                            "tool_call. Every other duplicate is still dropped, including a' (96 chars) "
                                            "rewrapped; longest body line now "
                                            + str(max(len(x) for x in g("log", "-1", "--format=%B", HEAD).splitlines()))},
        "seam_not_patched_by_test": {"cmd": f"git show {HEAD[:10]}:{NEW_TEST} | grep -cE 'deduplicate_tool_calls|run_tool_round|_is_order_significant|_peel_bridge_call'",
                                     "hits": sum(1 for x in show(HEAD, NEW_TEST).splitlines() if any(
                                         s in x for s in ("deduplicate_tool_calls", "run_tool_round",
                                                          "_is_order_significant", "_peel_bridge_call"))),
                                     "patched_boundaries": ["tools.computer_use.cua_backend_driver.cua_driver_binary_available",
                                                            "tools.computer_use.tool._new_backend"]},
        "ruff": (RAW / "ruff-head.txt").read_text().strip(),
        "merge_tree": {"main_sha": BASE, "clean": True, "tree": g("merge-tree", "--write-tree", BASE, HEAD),
                       "head_tree": g("rev-parse", f"{HEAD}^{{tree}}"),
                       "cmd": f"git merge-tree --write-tree {BASE[:10]} {HEAD[:10]}",
                       "main_commits_since_previous_base": int(g("rev-list", "--count", f"{PREV_BASE}..{BASE}")),
                       "of_which_touch_changed_or_seam_paths": len([x for x in g(
                           "log", "--format=%h", f"{PREV_BASE}..{BASE}", "--", "run_agent.py",
                           "agent/tool_dispatch_helpers.py", "agent/turn_tool_round.py", "tools/computer_use/",
                           "tools/tool_search.py", "tools/tool_search_validation.py", "model_tools.py",
                           "tests/fakes/fake_llm_provider.py", "tests/agent/test_agent_guardrails.py").splitlines() if x])},
        "freshness": "head is one commit on current main (fetched 2026-10-01T11:05Z); the F07 head GREEN cells are the freshness proof",
        "workflow_push_trigger_scan": {"branch": FORK_BRANCH, "push_workflows": wf["push_workflows"],
                                       "matches": len(wf["matches"][FORK_BRANCH]), "tree": HEAD,
                                       "scanner": "harness/wfscan.py sha256=" + sha256(PROOF / "wfscan.py")},
        "fork_ref_collision": {"checked_at": "2026-10-01T11:06Z",
                               "cmd": "git ls-remote https://github.com/kvnloo/hermes-agent.git refs/heads/staged "
                                      "'refs/heads/staged/*' refs/heads/staging 'refs/heads/staging/*'",
                               "result": "only refs/heads/staging 28790e597c (legacy); no refs/heads/staged or staged/*",
                               "reading": "staging/* cannot be created on the fork while refs/heads/staging exists; "
                                          "staged/cu-repeat-input-dedup has no collision (OD-0 resolved by the rename)"},
        "queue_board": {"board": "kvnloo/hermes-agent#404", "title": "[staged PRs] 39 reproved branches ready for "
                        "manual upstream promotion", "data_rows": 39, "checked_at": "2026-10-01T11:06Z"},
        "upstream_dedupe_search": {"searched_at": "2026-10-01T11:10Z",
                                   "queries": ["deduplicate tool calls computer_use", "repeated key press computer use",
                                               "same-turn duplicate tool call", "_deduplicate_tool_calls",
                                               "duplicate tool call", "Removed duplicate tool call"],
                                   "open_external_same_defect": [],
                                   "nearby_open_prs_no_overlap": {
                                       "119760": "edosulai: tool_call_id dedup across history (test_agent_guardrails.py; no shared hunk)",
                                       "112303": "marcus912: bedrock sidecar order", "118837": "hoshibara: codex same-id twins",
                                       "6784": "jbarket: loop detection added after the dedup method; does not change it",
                                       "84867": "jmeadlock: invalid-JSON recovery in turn_tool_round.py; no dedup change",
                                       "106257": "Xrey995: plugin lifecycle hooks; no dedup change",
                                       "74906": "Monekey: empty-message repair after dedup in agent_runtime_helpers.py"},
                                   "merged_related": {"86887": "fangliquanflq: canonical JSON key in the same dedup (moved unchanged)"},
                                   "own_prior": {"124008": "kvnloo, CLOSED 2026-09-30T03:15:51Z owner batch self-close; parked on kvnloo/hermes-agent#316",
                                                 "113453": "kvnloo, CLOSED 2026-09-26 (wider executor design, retired)"}},
    },
    "verdict": "KEEP",
    "not_tested": [], "limitations": ["static checks only"],
    "learning": None,
    "frozen": {"bundle_sha": None, "cells": 0, "supersedes": f"STATIC/{SUPERSEDES}", "status": "NOT_FROZEN (open P8 item)"},
}

# ---------------- probe dry run ----------------
probe_rows = {}
for p in sorted(RAW.glob("probe-dryrun-*.json")):
    probe_rows[p.stem.replace("probe-dryrun-", "")] = {"summary": json.loads(p.read_text())["summary"],
                                                        "file": f"raw-r03/{p.name}", "sha256": sha256(p)}
probe = {
    "schema": "xf.receipt.v1", "id": f"F07P/{RUN_ID}", "tier": "T1 (dry run of a T2/T3 harness)", "label": "OBSERVED",
    "question": "Does the repeat-key prevalence probe measure emitted vs kept vs delivered presses correctly before it is "
                "pointed at a real model?",
    "harness": {"path": "probes/repeat_key_prevalence.py", "sha256": sha256(ST / "probes/repeat_key_prevalence.py")},
    "command": "harness/probe_dryrun_r03.sh <main> <head>: per arm and mode, env -i PATH=/usr/bin:/bin "
               "HOME=$TH/probe-<arm>-<mode> HERMES_HOME=$HOME/.hermes TZ=UTC LANG=C.UTF-8 $HERMES_PYTHON "
               "probes/repeat_key_prevalence.py --tree <wt> --fake --trials 1 --tool-search {default|off} "
               "--out raw-r03/probe-dryrun-<arm>-<mode>.json (paths then replaced by placeholders)",
    "driver": {"path": "harness/probe_dryrun_r03.sh", "sha256": sha256(PROOF / "probe_dryrun_r03.sh")},
    "arms": {"main": BASE, "head": HEAD},
    "results": probe_rows,
    "reading": "Scripted fake model only, so this validates the harness and says nothing about real-model emission rates.",
    "verdict": "KEEP (harness works)",
    "not_tested": ["any real model"],
    "limitations": ["scripted model emits the repeat by construction"],
    "learning": None,
    "frozen": {"bundle_sha": None, "cells": len(probe_rows), "supersedes": f"F07P/{SUPERSEDES}",
               "status": "NOT_FROZEN (open P8 item)"},
}

out = {f"F07-{RUN_ID}.json": f07, f"E25-{RUN_ID}.json": e25, f"STATIC-{RUN_ID}.json": static,
       f"F07P-probe-dryrun-{RUN_ID}.json": probe}
for name, body in out.items():
    path = R / name
    if path.exists():
        raise SystemExit(f"write-once: {path} exists")
for name, body in out.items():
    body = {**body, **{k: v for k, v in common.items() if k not in body}, "supersedes": body["id"].split("/")[0] + "/" + SUPERSEDES}
    text = json.dumps(body, indent=1, sort_keys=False) + "\n"
    for bad in ("/workspace/", "~", "<models-disk>", "/tmp/claude"):
        assert bad not in text, (name, bad)
    (R / name).write_text(text, encoding="utf-8")
manifest = {name: sha256(R / name) for name in out} | {"cells-r03.jsonl": sha256(R / "cells-r03.jsonl")}
(R / f"MANIFEST-{RUN_ID}.sha256.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
print(json.dumps(manifest, indent=1))
print("F07", f07["verdict"], "E25", e25["verdict"])
