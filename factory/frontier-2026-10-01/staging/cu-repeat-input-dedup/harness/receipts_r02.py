#!/usr/bin/env python3
"""Aggregate cells.jsonl + static checks into xf.receipt.v1-shaped receipts (write-once)."""
import hashlib
import json
import subprocess
from pathlib import Path

S = Path("$S")
H = S / "h.git"
ST = Path("$ARTIFACTS/frontier-2026-10-01/staging/cu-repeat-input-dedup")
R = ST / "receipts"
PROOF = ST / "harness"
BASE = "234badf4012af380d23c91eae55d045a69c69ffb"
HEAD = "402e9b0bdbfdf2a988971c6cd452e8115b134208"
import sys
NEWMAIN = sys.argv[1]
DONOR, DONOR_MB = "570dc83ba65fc4ce86efb2c00e89dc84d19bd5ca", "cb3142d3257b15ac42de544bd585793567400d0f"
NEW_TEST = "tests/agent/test_tool_call_dedup_order_significant.py"
RUN_ID = "r20261001-02"
SUPERSEDES = "r20261001-01"


def g(*a):
    return subprocess.run(["git", "-C", str(H), *a], check=True, text=True, capture_output=True).stdout.strip()


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


cells = [json.loads(line) for line in (R / "cells-r02.jsonl").read_text().splitlines()]


def pick(exp, arm):
    return [c for c in cells if c["experiment"] == exp and c["arm"] == arm]


def brief(c):
    return {k: c[k] for k in ("arm", "rep", "arm_tree", "passed", "failed", "failed_ids", "red_marker_matched",
                              "egress_blocked", "loopback_connects", "seam_hits", "wall_s", "load1_at_start",
                              "raw_log")} | {"raw_log_sha256": sha256(R / c["raw_log"])}


common = {
    "base_revision": BASE,
    "head_revision": HEAD,
    "branch": "staging/cu-repeat-input-dedup",
    "origin_refs": ["NousResearch/hermes-agent#124008", "NousResearch/hermes-agent#112639", "kvnloo/hermes-agent#316"],
    "policy_revision": {"AGENTS.md": g("rev-parse", f"{BASE}:AGENTS.md"),
                        "agent/AGENTS.md": g("rev-parse", f"{BASE}:agent/AGENTS.md"),
                        "factory": "frontier-2026-10-01/FACTORY.md sha256=" + sha256(
                            "$ARTIFACTS/frontier-2026-10-01/FACTORY.md")},
    "inputs": {
        f"{NEW_TEST}@head": g("rev-parse", f"{HEAD}:{NEW_TEST}"),
        "tests/agent/test_agent_guardrails.py@base": g("rev-parse", f"{BASE}:tests/agent/test_agent_guardrails.py"),
        "tests/fakes/fake_llm_provider.py@base": g("rev-parse", f"{BASE}:tests/fakes/fake_llm_provider.py"),
        "scripts/run_tests.sh@base": g("rev-parse", f"{BASE}:scripts/run_tests.sh"),
        "scripts/run_tests_parallel.py@base": g("rev-parse", f"{BASE}:scripts/run_tests_parallel.py"),
        "guard_plugin _xf_t1_guard.py sha256": sha256(PROOF / "_xf_t1_guard.py"),
        "driver proof-r02.py sha256": sha256(PROOF / "proof-r02.py"),
        "donor": f"refs/fork/fix/computer-use-repeat-input-dedup-current-main@{DONOR} (merge-base {DONOR_MB})",
    },
    "env": {"host": "<local-host>", "python": "3.11.14 (HERMES_PYTHON=<hermes-home>/hermes-agent/venv/bin/python, "
            "interpreter only)", "sandbox": "run_tests.sh env -i + isolated HOME/HERMES_HOME "
            "(scratchpad/testhome-st-cu-repeat-input-dedup) + in-process loopback-only connect guard; no bwrap",
            "file_retries": 0, "workers": 2},
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
    "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0, "tokens": 0},
    "provenance": "self",
    "privacy": "public-aggregate (synthetic fixtures only)",
    "ai_assistance": "Claude Code (Opus 5.5) wrote the change, the test and these receipts",
}

# ---------------- F07 ----------------
base, head = pick("F07", "base"), pick("F07", "head")
f07 = {
    "schema": "xf.receipt.v1", "id": f"F07/{RUN_ID}", "tier": "T1", "label": "OBSERVED",
    "question": "Through a real AIAgent turn (FakeLLMServer loopback + in-tree no-op computer_use backend), "
                "does one assistant message with two identical computer_use key=tab calls dispatch two presses? "
                "Bridge case uses the advertised tool_call shape {calls: [{name, arguments}]} (r01 used the tolerated legacy single shape).",
    "command": cells[0]["cmd"].replace(cells[0]["files"][0], "{files}"),
    "files": [NEW_TEST],
    "arms": {
        "base": {"tree": base[0]["arm_tree"], "how": f"main {BASE[:10]} + {NEW_TEST} only (test inject)"},
        "head": {"tree": head[0]["arm_tree"], "how": f"staging commit {HEAD[:10]}"},
        "neg-empty-table": {"how": "head with _ORDER_SIGNIFICANT_ACTIONS = frozenset()"},
        "sab-no-bridge-peel": {"how": "head with the _peel_bridge_call line in _is_order_significant removed"},
        "sab-facade-revert": {"how": "head with run_agent.py restored to main (old in-facade method)"},
        "sab-verdict-confirms": {"how": "head with computer_use _classify_action_result fallback returning 'done' "
                                        "(test-sensitivity check for the verify_fresh_state assertion)"},
        "donor-fix+new-test": {"how": f"main + donor run_agent.py hunk ({DONOR[:10]}) + {NEW_TEST}"},
    },
    "gates": {
        "red": {"arm": "base", "result": "PASS" if all(c["failed"] == 2 and c["red_marker_matched"] == 2 for c in base) else "FAIL",
                "observed": "2 failed / 2 in each of 3 reps",
                "assertion": "AssertionError: assert ['key', 'click'] == ['key', 'key', 'click']",
                "seam_covered": all("run_agent.py::_deduplicate_tool_calls" in c["seam_hits"] for c in base),
                "reps_agree": f"{len(base)}/{len(base)}"},
        "green": [{"arm": "head", "result": "PASS" if all(c["failed"] == 0 and c["passed"] == 2 for c in head) else "FAIL",
                   "reps_agree": f"{len(head)}/{len(head)}",
                   "seam_covered": all("tool_dispatch_helpers.py::deduplicate_tool_calls" in c["seam_hits"] for c in head)}],
        "negative_control": {"arm": "neg-empty-table", "result": "RED" if pick("F07", "neg-empty-table")[0]["failed"] == 2 else "NOT_RED",
                             "observed": "2 failed / 2"},
        "sabotage": {"per_hunk": [
            {"hunk": "agent/tool_dispatch_helpers.py _ORDER_SIGNIFICANT_ACTIONS entry", "arm": "neg-empty-table",
             "red_again": pick("F07", "neg-empty-table")[0]["failed"] == 2, "failed": pick("F07", "neg-empty-table")[0]["failed_ids"]},
            {"hunk": "agent/tool_dispatch_helpers.py _peel_bridge_call in _is_order_significant", "arm": "sab-no-bridge-peel",
             "red_again": pick("F07", "sab-no-bridge-peel")[0]["failed"] >= 1, "failed": pick("F07", "sab-no-bridge-peel")[0]["failed_ids"]},
            {"hunk": "run_agent.py _deduplicate_tool_calls forwarder", "arm": "sab-facade-revert",
             "red_again": pick("F07", "sab-facade-revert")[0]["failed"] == 2, "failed": pick("F07", "sab-facade-revert")[0]["failed_ids"]},
        ], "unpinned_hunks": ["agent/tool_dispatch_helpers.py __all__ entry (export list only)"],
            "test_sensitivity": {"arm": "sab-verdict-confirms", "failed": pick("F07", "sab-verdict-confirms")[0]["failed"],
                                 "assertion": "AssertionError: assert ['done', 'done'] == ['verify_fres..._fresh_state']"}},
        "adjacent": {
            "files": pick("ADJ", "main")[0]["files"],
            "base": f"{pick('ADJ', 'main')[0]['passed']} passed / {pick('ADJ', 'main')[0]['failed']} failed",
            "arm": f"{pick('ADJ', 'head')[0]['passed']} passed / {pick('ADJ', 'head')[0]['failed']} failed "
                   f"(= base + the 2 new test cases)",
            "identical": pick("ADJ", "main")[0]["failed"] == pick("ADJ", "head")[0]["failed"] == 0
                         and pick("ADJ", "head")[0]["passed"] - pick("ADJ", "main")[0]["passed"] == 2,
            "pre_existing_failures": [],
            "note": "tests/agent/test_agent_guardrails.py is byte-identical on base and head",
        },
        "guards": {"F14": "NOT_RUN (factory standing set not built yet)"},
        "flaky": False,
    },
    "findings": [
        "The donor fix (570dc83ba6, name-keyed 'computer_use' check in run_agent.py) leaves the default path broken: "
        "computer_use is in the default tools.tool_search.defer list, so the model calls it via the tool_call bridge, "
        "and the donor arm fails the tool_call-bridge case (failed: " + ", ".join(pick("F07", "donor-fix+new-test")[0]["failed_ids"]) + ").",
        "Each kept press returns its own verdict decision 'verify_fresh_state' (noop backend has no semantic effect), "
        "so the exemption neither collapses nor upgrades the verify ladder; pinned by the sab-verdict-confirms arm.",
    ],
    "safety": {"egress_blocked_in_new_test": sum(c["egress_blocked"] for c in pick("F07", "base") + pick("F07", "head")),
               "egress_blocked_in_adjacent_files": {"base": pick("ADJ", "main")[0]["egress_blocked"],
                                                    "head": pick("ADJ", "head")[0]["egress_blocked"],
                                                    "note": "pre-existing attempts by tests/agent/test_run_agent.py (84), "
                                                            "test_tool_batch_segmentation.py (4), test_tool_call_guardrail_runtime.py (4) "
                                                            "to Cloudflare IPs; blocked by the guard on both arms, tests still pass. "
                                                            "The guard covers connect(), not DNS resolution."},
               "credential_like_env_names_seen": sorted({k for c in cells for k in c["credential_like_env"]}),
               "home": "isolated"},
    "cells": [brief(c) for c in cells if c["experiment"] in ("F07", "ADJ")],
    "denominators": {"cells": len([c for c in cells if c["experiment"] in ("F07", "ADJ")]), "infra_excluded": 0,
                     "errored_scored_zero": 0, "completeness": 1.0},
    "verdict": "KEEP",
    "not_tested": ["real cua-driver / desktop delivery of two presses", "real-model emission rate of identical "
                   "same-message key presses (queued T2/T3 probe)", "macOS / Windows", "F14 standing guard set"],
}

# ---------------- E25 ----------------
e25 = {
    "schema": "xf.receipt.v1", "id": f"E25/{RUN_ID}", "tier": "T1", "label": "OBSERVED",
    "question": "Is the repeat-key dedup bug still red on current main through the static method, and green with the guard?",
    "command": pick("E25", "main+donor-test")[0]["cmd"],
    "arms": {
        "main+donor-test": {"tree": pick("E25", "main+donor-test")[0]["arm_tree"],
                            "how": f"main {BASE[:10]} + donor tests/agent/test_agent_guardrails.py hunk"},
        "main+donor-full": {"tree": pick("E25", "main+donor-full")[0]["arm_tree"],
                            "how": f"main + full donor diff {DONOR_MB[:10]}..{DONOR[:10]} (git apply -3 clean)"},
        "head+donor-test": {"tree": pick("E25", "head+donor-test")[0]["arm_tree"],
                            "how": "staging head + donor test hunk (old static-method contract via the forwarder)"},
    },
    "gates": {
        "red": {"arm": "main+donor-test", "result": "PASS" if pick("E25", "main+donor-test")[0]["failed"] == 1 else "FAIL",
                "observed": "27 passed / 1 failed",
                "failed": pick("E25", "main+donor-test")[0]["failed_ids"],
                "assertion": "assert [namespace(...keys tab...)] == [namespace(...), namespace(...)]; Right contains one more item"},
        "green_donor": {"arm": "main+donor-full", "observed": "28 passed / 0 failed"},
        "green_head": {"arm": "head+donor-test", "observed": "28 passed / 0 failed"},
    },
    "note": "Static-method RED/GREEN only; the real-path proof is F07. Donor diff applies with git apply -3 on main.",
    "cells": [brief(c) for c in cells if c["experiment"] == "E25"],
    "verdict": "KEEP",
}

# ---------------- STATIC + freshness ----------------
static = {
    "schema": "xf.receipt.v1", "id": f"STATIC/{RUN_ID}", "tier": "T0", "label": "OBSERVED",
    "checks": {
        "tool_name_branch_in_run_agent_py": {"cmd": "git show <rev>:run_agent.py | grep -c computer_use",
                                             "base": 0, "head": 0, "donor": 2},
        "facade_size_lines": {f: {"base": len(g("show", f"{BASE}:{f}").splitlines()), "head": len(g("show", f"{HEAD}:{f}").splitlines())}
                              for f in ("run_agent.py", "agent/tool_dispatch_helpers.py")},
        "diffstat": g("diff", "--stat", BASE, HEAD).splitlines()[-1].strip(),
        "seam_not_patched_by_test": {"cmd": f"git show {HEAD[:10]}:{NEW_TEST} | grep -nE 'deduplicate_tool_calls|run_tool_round|_is_order_significant|_peel_bridge_call'",
                                     "hits": 0, "patched_boundaries": ["tools.computer_use.cua_backend_driver.cua_driver_binary_available",
                                                                       "tools.computer_use.tool._new_backend"]},
        "ruff": "All checks passed (agent/tool_dispatch_helpers.py run_agent.py test file)",
        "merge_tree": {"main_sha": NEWMAIN, "clean": True, "tree": g("merge-tree", "--write-tree", NEWMAIN, HEAD),
                       "cmd": f"git merge-tree --write-tree {NEWMAIN[:10]} {HEAD[:10]}",
                       "main_commits_since_base": int(g("rev-list", "--count", f"{BASE}..{NEWMAIN}")),
                       "of_which_touch_changed_or_seam_paths": len([x for x in g("log", "--format=%h", f"{BASE}..{NEWMAIN}", "--",
                           "run_agent.py", "agent/tool_dispatch_helpers.py", "agent/turn_tool_round.py", "tools/computer_use/",
                           "tools/tool_search.py", "tools/tool_search_validation.py", "model_tools.py",
                           "tests/fakes/fake_llm_provider.py", "tests/agent/test_agent_guardrails.py").splitlines() if x])},
        "freshness": ("base is current main at check time; the F07 head GREEN cells are the freshness proof"
                      if NEWMAIN == BASE else "main moved; re-run F07 RED/GREEN on the merge before queueing"),
        "workflow_push_trigger_scan": {"branch": "staging/cu-repeat-input-dedup", "push_workflows": int(sys.argv[2]), "matches": int(sys.argv[3]),
                                       "tree": HEAD},
        "upstream_dedupe_search": {"searched_at": "2026-10-01T09:10Z",
                                   "queries": ["deduplicate tool calls computer_use", "repeated key press computer use",
                                               "same-turn duplicate tool call", "_deduplicate_tool_calls",
                                               "duplicate tool call", "Removed duplicate tool call"],
                                   "open_external_same_defect": [],
                                   "nearby_open_prs_no_overlap": {"119760": "edosulai: tool_call_id dedup across history "
                                                                  "(agent_runtime_helpers.py + test_agent_guardrails.py; no shared hunk)",
                                                                  "112303": "marcus912: bedrock sidecar order", "118837": "hoshibara: codex same-id twins"},
                                   "merged_related": {"86887": "fangliquanflq: canonical JSON key in the same dedup (kept as is)"},
                                   "own_prior": {"124008": "kvnloo, CLOSED 2026-09-30T03:15:51Z owner batch self-close; parked on kvnloo/hermes-agent#316",
                                                 "113453": "kvnloo, CLOSED 2026-09-26 (wider executor design, retired)"}},
    },
}

# ---------------- probe dry run ----------------
probe_rows = {}
for p in sorted((R / "raw-r02").glob("probe-dryrun-*.json")):
    probe_rows[p.stem.replace("probe-dryrun-", "")] = {"summary": json.loads(p.read_text())["summary"],
                                                        "file": f"raw-r02/{p.name}", "sha256": sha256(p)}
probe = {
    "schema": "xf.receipt.v1", "id": f"F07P/{RUN_ID}", "tier": "T1 (dry run of a T2/T3 harness)", "label": "OBSERVED",
    "question": "Does the repeat-key prevalence probe measure emitted vs kept vs delivered presses correctly before it is "
                "pointed at a real model?",
    "harness": {"path": "probes/repeat_key_prevalence.py", "sha256": sha256(ST / "probes/repeat_key_prevalence.py")},
    "command": "env -i PATH=/usr/bin:/bin HOME=$T HERMES_HOME=$T/.hermes $PY probes/repeat_key_prevalence.py --tree <wt> "
               "--fake --trials 1 --tool-search {default|off} --out raw-r02/probe-dryrun-<arm>-<mode>.json",
    "arms": {"main": BASE, "head": HEAD},
    "results": probe_rows,
    "reading": "main: 6 emitted, 3 kept, 3 delivered; head: 6/6/6, in both tool_search modes. Scripted fake model only, "
               "so this validates the harness and says nothing about real-model emission rates.",
}

out = {f"F07-{RUN_ID}.json": f07, f"E25-{RUN_ID}.json": e25, f"STATIC-{RUN_ID}.json": static,
       f"F07P-probe-dryrun-{RUN_ID}.json": probe}
for name, body in out.items():
    path = R / name
    if path.exists():
        raise SystemExit(f"write-once: {path} exists")
    body = {**body, **{k: v for k, v in common.items() if k not in body}, "supersedes": body["id"].split("/")[0] + "/" + SUPERSEDES}
    path.write_text(json.dumps(body, indent=1, sort_keys=False) + "\n", encoding="utf-8")
manifest = {name: sha256(R / name) for name in out} | {"cells-r02.jsonl": sha256(R / "cells-r02.jsonl")}
(R / f"MANIFEST-{RUN_ID}.sha256.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
print(json.dumps(manifest, indent=1))
