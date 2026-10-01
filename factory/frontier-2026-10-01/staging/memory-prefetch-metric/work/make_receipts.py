"""Build the public-aggregate receipts for staging/memory-prefetch-metric from the raw run outputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

R = Path("$ARTIFACTS/frontier-2026-10-01/staging/memory-prefetch-metric")
W = R / "work"
OUT = R / "receipts"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0"
HEAD = "c815543bc2504eccaae9f6adce5046f41710f38c"
HEAD_TREE = "9569d4977ca74896070bc85425145742ee835291"
MAIN_NOW = "234badf4012af380d23c91eae55d045a69c69ffb"
WT = "$ARTIFACTS/promotion-readiness-2026-10-01/wt/staging/memory-prefetch-metric"
PY = "<hermes-home>/hermes-agent/venv/bin/python"
TH = "$S/testhome-st-memory-prefetch-metric"
CHANGED = [
    "agent/memory_manager.py", "hermes_cli/observability/schemas/hermes.shared_metrics.v3.schema.json",
    "hermes_cli/observability/shared_metrics_contract.py", "hermes_cli/observability/shared_metrics_loop.py",
    "tests/hermes_cli/test_shared_metrics_loop.py", "website/docs/developer-guide/relay-shared-metrics.md",
]
POLICY = {"AGENTS.md": "65aa3e61bcba610da21279a17385671263be39e9@572e4f4fad",
          "CONTRIBUTING.md": "b0baa59b5057c204b3c09d3dd170c0955cfdb39c@572e4f4fad",
          "factory": "FACTORY.md sha256 7726ba18b43a9367… (frontier-2026-10-01)"}
ENV = {"host": "<local-host>", "python": "3.11.14 (<hermes-home>/hermes-agent/venv, read-only use as HERMES_PYTHON)",
       "pytest": "9.1.1", "nemo_relay_native": True,
       "sandbox": "no bwrap; HOME/HERMES_HOME forced to scratch test home; run_tests.sh clean env (TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0)",
       "network": "none used; probes install a loopback-only socket.connect guard"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(name: str, data: dict) -> None:
    path = OUT / name
    assert not path.exists(), f"write-once: {path} exists"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(name, sha(path))


prove = json.loads((W / "prove_results.json").read_text())
red = prove["runs"]["red"]
greens = prove["runs"]["green"]
sab = prove["runs"]["sabotage"]
adj_b, adj_h = prove["runs"]["adjacent_base"], prove["runs"]["adjacent_head"]
CONTRACT_TEST = ("tests/hermes_cli/test_shared_metrics_loop.py::"
                 "test_external_prefetch_records_each_exit_with_how_long_the_turn_waited")
run_cmd = (f"HOME={TH} HERMES_HOME={TH}/.hermes HERMES_PYTHON={PY} bash scripts/run_tests.sh -j 2 "
           "tests/hermes_cli/test_shared_metrics_loop.py -q")

f08 = {
    "schema": "xf.receipt.v1",
    "id": "F08/r20261001-01",
    "experiment": "F08 (new): per-outcome RED/GREEN with each record_ call reverted, plus RED-on-base, GREEN x3, adjacent",
    "tier": "T1", "cost_usd": 0.0, "lane": "cpu",
    "spec": {"path": None, "prereg_commit": None,
             "note": "Not pre-registered on claude/ledger (xf not built yet); oracle fixed in the test before the runs below."},
    "runner_revision": {"driver": "work/mpm_prove.py (scratchpad copy)", "test_runner": "scripts/run_tests.sh blob 8fcc4294f4"},
    "issue": None,
    "origin_refs": ["NousResearch/hermes-agent@25c1b008c8", "NousResearch/hermes-agent#124151"],
    "staging": "memory-prefetch-metric",
    "base_revision": BASE,
    "head_revision": HEAD, "head_tree": HEAD_TREE,
    "changed_files": CHANGED,
    "inputs": {
        "test_file_blob_head": "df30f9a2a0efe28512303bb3231191baa7b45b5e",
        "test_file_blob_base": "3d29db97d853ef0f0277f5f8217e42919a225492",
        "production_seam": {"file": "agent/memory_manager.py", "symbol": "MemoryManager._prefetch_provider",
                            "blob_head": "a099c392586a074fe3be651ed60336ea76c89602",
                            "blob_base": "d023a57f8bc8ddde607c1f7ba519331aedc5952f"},
    },
    "policy_revision": POLICY,
    "env": {**ENV, "load1_at_start": prove["load1_at_start"]},
    "command": run_cmd,
    "gates": {
        "red": {"arm": "base (test file at head, the 5 production files checked out from main)", "result": "PASS",
                "observed": red["summary"], "failed": red["failed"],
                "assertion": "AssertionError: assert {} == {('honcho', '...0ms'): 1, ...}  (Right contains 5 more items)",
                "seam_covered": "yes by construction: the test calls MemoryManager.prefetch_all -> _prefetch_provider; no monkeypatch of the seam",
                "log_sha256": red["log_sha256"]},
        "green": [{"rep": i + 1, "observed": g["summary"], "failed": g["failed"], "log_sha256": g["log_sha256"]}
                  for i, g in enumerate(greens)],
        "green_reps_agree": "3/3",
        "sabotage": {"per_hunk": [
            {"mutation": s["label"].replace("sabotage_", ""), "file": s["mutation"]["file"],
             "red_again": bool(s["failed"]) and s["failed"] == [CONTRACT_TEST], "observed": s["summary"],
             "failed": s["failed"], "log_sha256": s["log_sha256"]} for s in sab],
            "unpinned_hunks": ["website/docs row (checked by T0-SCHEMA receipt, not by pytest)",
                               "schema JSON def (checked by T0-SCHEMA receipt; pytest store path does not read the JSON schema)"]},
        "adjacent": {"files": adj_h["cmd"].split("-j 2 ")[1].replace(" -q", "").split(),
                     "base": adj_b["summary"], "head": adj_h["summary"], "base_failed": adj_b["failed"],
                     "head_failed": adj_h["failed"], "identical": adj_b["failed"] == adj_h["failed"] == [],
                     "note": "head has one more test (the new contract test); no failures on either side",
                     "pre_existing_failures": []},
        "disabled_collection": {"test": "test_disabled_shared_metrics_record_no_loop_rows (extended with a prefetch call)",
                                "head": "PASS in all GREEN reps", "base": "PASS (guard, not a red test: base records nothing either)"},
        "flaky": False,
    },
    "measurements": [
        {"name": "contract_test_red_on_base", "value": 1, "unit": "failed tests", "label": "OBSERVED"},
        {"name": "green_reps_passing", "value": 3, "n": 3, "unit": "reps", "label": "OBSERVED"},
        {"name": "sabotage_mutations_re_red", "value": sum(1 for s in sab if s["failed"] == [CONTRACT_TEST]),
         "n": len(sab), "unit": "mutations", "label": "OBSERVED"},
        {"name": "adjacent_tests_passed_base", "value": 330, "unit": "tests", "label": "OBSERVED"},
        {"name": "adjacent_tests_passed_head", "value": 331, "unit": "tests", "label": "OBSERVED"},
    ],
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
    "not_tested": ["real provider backends (Honcho/Hindsight/mem0 servers)", "py3.14 CI matrix", "Windows/macOS"],
    "limitations": ["Timing-bucket assertions use a 0.3 s timeout and instant fakes; a host stalled >200 ms could flake the bucket",
                    "Relay is the test fixture fake (direct_runtime) in pytest; the E17 receipt covers the real binding"],
    "verdict": "KEEP",
    "provenance": "self",
    "privacy": "public-aggregate",
    "ai_assistance": "Claude Code (Opus 5.5) wrote the change, tests and this receipt",
    "raw_artifacts": {"results": {"path": "work/prove_results.json", "sha256": sha(W / "prove_results.json")}},
}
write("F08-r20261001-01.json", f08)

e17 = json.loads((W / "e17_result.json").read_text())
faults = {}
for name, r in e17["faults"].items():
    if isinstance(r.get("turn_wait_ms"), dict):
        faults[name] = {
            "backend_fault": r["backend_path"], "expected_outcome": r["expected_outcome"],
            "observed_head_rows": r["head_rows"], "observed_base_rows": r["base_rows"],
            "turn_wait_ms": r["turn_wait_ms"], "returned_context_identical_across_arms": r["returned_context_identical_across_arms"],
        }
    else:
        faults[name] = r
gate = json.loads((W / "micro_gate_cost.json").read_text())
e17_cmd = (f"cd <scratchpad> && env -i PATH=/usr/bin:/bin {PY} work/e17_prefetch_fault_probe.py --repo {WT} "
           "--base-mm work/base_memory_manager.py --out work/e17_result.json")
gate_cmd = f"cd <scratchpad> && env -i PATH=/usr/bin:/bin {PY} work/micro_gate_cost.py --repo {WT} --out work/micro_gate_cost.json"
e17r = {
    "schema": "xf.receipt.v1",
    "id": "E17/r20261001-01",
    "experiment": "E17: delay/hang/empty/error fault probe against a local fake memory backend through the real turn-start "
                  "prefetch path, plus profile-scope and collection-off checks and a base-vs-head microbenchmark",
    "tier": "T1", "cost_usd": 0.0, "lane": "cpu",
    "spec": {"path": None, "prereg_commit": None, "note": "Not pre-registered; expectations fixed in the probe before the run."},
    "staging": "memory-prefetch-metric",
    "origin_refs": ["NousResearch/hermes-agent#124151", "evals/memory/honcho_current_query.py pattern",
                    "evals/provider_fallback/probe_104260.py:11-39 isolation + loopback guard"],
    "base_revision": BASE, "head_revision": HEAD, "head_tree": HEAD_TREE,
    "arms": {"head": f"MemoryManager from the staging commit {HEAD[:10]}",
             "base": "main's agent/memory_manager.py (blob d023a57f8b, sha256 048842c1…) loaded from source into the head tree; "
                     "it is the only changed file on the prefetch call path"},
    "inputs": {
        "probe": {"path": "work/e17_prefetch_fault_probe.py", "sha256": sha(W / "e17_prefetch_fault_probe.py")},
        "base_memory_manager": {"path": "work/base_memory_manager.py", "sha256": sha(W / "base_memory_manager.py")},
        "gate_cost_micro": {"path": "work/micro_gate_cost.py", "sha256": sha(W / "micro_gate_cost.py")},
    },
    "env": {**ENV, "relay": "REAL nemo_relay native binding + real SharedMetricsStore in an isolated HERMES_HOME "
                            "(config.yaml: telemetry.shared_metrics.enabled true, send false)",
            "load1": {"probe_end": e17["load1_end"], "gate_micro": [gate["load1_start"], gate["load1_end"]]},
            "prefetch_timeout_s": {"bulk": e17["timeout_s"], "default_case": 8.0}},
    "commands": [e17_cmd, gate_cmd],
    "reps_per_fault_per_arm": e17["reps"],
    "results": {
        "faults": faults,
        "checks": e17["checks"],
        "microbenchmark_prefetch_provider_us_per_call": e17["microbenchmark"],
        "gate_cost_attribution_us_per_call": gate["modes"],
    },
    "measurements": [
        {"name": "outcome_class_matches_fault", "value": sum(e17["checks"]["outcome_classes_match_expected"].values()),
         "n": len(e17["checks"]["outcome_classes_match_expected"]), "label": "OBSERVED"},
        {"name": "rows_per_turn_head", "value": "1 row per turn for every fault (12/12 x 7 faults)", "label": "OBSERVED"},
        {"name": "rows_base", "value": 0, "label": "OBSERVED"},
        {"name": "hang_skips_while_stuck", "value": "1 timed_out (1s_to_2s) then 3 skipped (lt_100ms); 1 backend call while hung",
         "label": "OBSERVED"},
        {"name": "default_8s_timeout_bucket", "value": e17["faults"]["hang_default_timeout"]["head_rows"][0]["dims"]["latency_bucket"],
         "turn_wait_ms": e17["faults"]["hang_default_timeout"]["turn_wait_ms"], "label": "OBSERVED"},
        {"name": "profile_scope", "value": "pass (row in owning profile, 0 in default home)", "label": "OBSERVED"},
        {"name": "collection_off_rows", "value": 0, "store_created": False, "label": "OBSERVED"},
        {"name": "prefetch_provider_overhead_us_collection_off", "statistic": "median of 12 block deltas (400 calls each)",
         "value": e17["microbenchmark"]["collection_off"]["delta_head_minus_base_us"],
         "aa_noise": e17["microbenchmark"]["collection_off"]["aa_base_minus_base_us"], "label": "OBSERVED"},
        {"name": "prefetch_provider_overhead_us_collection_on", "statistic": "median of 12 block deltas (400 calls each)",
         "value": e17["microbenchmark"]["collection_on"]["delta_head_minus_base_us"],
         "aa_noise": e17["microbenchmark"]["collection_on"]["aa_base_minus_base_us"], "label": "OBSERVED"},
        {"name": "record_call_cost_vs_existing_sites_us", "value": {
            "off": {"record_memory_prefetch": gate["modes"]["off"]["record_memory_prefetch"]["median_us"],
                    "record_execution_backend": gate["modes"]["off"]["record_execution_backend_existing"]["median_us"],
                    "record_provider_memory_call": gate["modes"]["off"]["record_provider_memory_call_existing"]["median_us"],
                    "enabled_gate_alone": gate["modes"]["off"]["enabled_gate_only"]["median_us"]},
            "on": {"record_memory_prefetch": gate["modes"]["on"]["record_memory_prefetch"]["median_us"],
                   "record_execution_backend": gate["modes"]["on"]["record_execution_backend_existing"]["median_us"],
                   "record_provider_memory_call": gate["modes"]["on"]["record_provider_memory_call_existing"]["median_us"]}},
         "label": "OBSERVED"},
    ],
    "interpretation": {
        "prompt_prefix": "unchanged: the context string returned to the turn is identical across arms for all 7 faults",
        "hot_path": "NOT below per-call microbenchmark noise: +~47 us per external prefetch with collection off, +~159 us "
                    "with it on (A/A within about +/-8 us and +/-30 us). The record call costs the same as the existing "
                    "record_execution_backend / record_provider_memory_call sites; it runs once per turn per external "
                    "provider, against turn waits of 0.3 ms (loopback) to 8 s (timeout).",
        "host_noise": "load1 was 11-17 during these runs (other agents); absolute microseconds are inflated, A/A included",
    },
    "evidence_class": {"local": True, "ci": "none", "simulation": True, "runtime": False, "kind": "mechanism"},
    "not_tested": ["real memory backends (Honcho, Hindsight, mem0, Supermemory servers)", "packages sent upstream (send: false)",
                   "py3.14 interpreter", "the turn's other phases (model call, tools)"],
    "limitations": ["The fake backend is a local HTTP server; real backend latency distributions are not measured here",
                    "The microbenchmark ran on a loaded shared host; A/A is reported beside every delta",
                    "Store drain uses relay_shared_metrics._reset_for_tests(), the same hook the upstream tests use"],
    "verdict": "KEEP (mechanism); hot-path gate recorded as not met as worded",
    "provenance": "self",
    "privacy": "public-aggregate (synthetic fixtures only)",
    "raw_artifacts": {"e17_result": {"path": "work/e17_result.json", "sha256": sha(W / "e17_result.json")},
                      "gate_cost": {"path": "work/micro_gate_cost.json", "sha256": sha(W / "micro_gate_cost.json")}},
}
write("E17-r20261001-01.json", e17r)

t0 = json.loads((W / "t0_schema_contract_check.json").read_text())
t0r = {
    "schema": "xf.receipt.v1",
    "id": "T0-SCHEMA/r20261001-01",
    "experiment": "Static schema <-> contract <-> doc agreement for hermes.memory.prefetch.count, bounded label values",
    "tier": "T0", "cost_usd": 0.0, "lane": "cpu",
    "staging": "memory-prefetch-metric",
    "base_revision": BASE, "head_revision": HEAD, "head_tree": HEAD_TREE,
    "inputs": {"checker": {"path": "work/t0_schema_contract_check.py", "sha256": sha(W / "t0_schema_contract_check.py")},
               "schema_blob": "21cfe11bf70b3669a1a781e87aff0b2a5e09db26", "contract_blob": "c8443e460013288c2523bbb90157d3aede66766f",
               "loop_blob": "0e5e68bf26e431c31e75ffb7e7e78e76d97e9343"},
    "command": f"env -i PATH=/usr/bin:/bin {PY} work/t0_schema_contract_check.py --repo {WT} --out work/t0_schema_contract_check.json",
    "results": t0,
    "measurements": [
        {"name": "contract_combinations_schema_valid", "value": t0["checks"]["all_contract_combinations_valid"], "label": "OBSERVED"},
        {"name": "out_of_contract_rows_rejected", "value": t0["checks"]["out_of_contract_rows_rejected"], "label": "OBSERVED"},
        {"name": "builder_samples_pass", "value": all(x["pass"] for x in t0["checks"]["builder_samples"]), "label": "OBSERVED"},
    ],
    "negative_control": "On main the metric constant does not exist (contract has no MEMORY_PREFETCH_METRIC); not run as a separate cell.",
    "verdict": "KEEP" if t0["all_pass"] else "DISCARD",
    "provenance": "self", "privacy": "public-aggregate",
    "raw_artifacts": {"result": {"path": "work/t0_schema_contract_check.json", "sha256": sha(W / "t0_schema_contract_check.json")}},
}
write("T0-SCHEMA-r20261001-01.json", t0r)

merge = {
    "schema": "xf.receipt.v1",
    "id": "MERGE/r20261001-01",
    "experiment": "Freshness and overlap: merge-tree on current main, and a simulated merge with the open PR that edits the same function",
    "tier": "T0", "cost_usd": 0.0, "lane": "cpu",
    "staging": "memory-prefetch-metric",
    "base_revision": BASE, "head_revision": HEAD,
    "results": {
        "current_main": {"sha": MAIN_NOW, "commits_since_base": 11, "invalidate_on_changed": False,
                         "command": f"git merge-tree --write-tree {MAIN_NOW} {HEAD}", "tree": "6dad8cd3ed88da6143bc2494dec2750dba79324f",
                         "clean": True},
        "with_NousResearch_124151": {
            "pr": 124151, "author": "kweez007", "head": "3ee6189dbad0485790893c5098b20f00d27a1d51",
            "diff_sha256": sha(W / "pr124151.diff"),
            "method": "gh pr diff applied onto main as an unreferenced temp commit 9812d4f212, then merge-tree with the staging commit",
            "merge_tree": "2e08be356dc5999d01f8d0fa4da582080a523b23", "clean": True,
            "tests_on_merged_tree": {"commit": "2698613f0a (temp, unreferenced)",
                                     "command": "scripts/run_tests.sh -j 2 tests/hermes_cli/test_shared_metrics_loop.py tests/agent/test_memory_provider.py -q",
                                     "observed": "2 files, 74 tests passed, 0 failed", "log_sha256": sha(W / "merge_124151_tests.log")},
            "semantics": "compatible: the record calls time the real wait, so #124151's per-provider 20 s Hindsight bound lands in 10s_to_30s",
        },
        "workflow_push_trigger_scan": {"tree": HEAD_TREE, "workflows": 52, "matches_for_branch": 0},
    },
    "label": "OBSERVED", "verdict": "KEEP", "provenance": "self", "privacy": "public-aggregate",
}
write("MERGE-r20261001-01.json", merge)
