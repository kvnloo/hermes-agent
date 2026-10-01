"""Write the round-3 receipts (F08 r03, T0-SCHEMA r03, MERGE r03, OWNERSHIP r02) for memory-prefetch-metric.

Reads only local result files under work/r3 and writes receipts/ with repo-relative paths and placeholders
(no absolute local paths). Usage: python make_receipts_r3.py  (run from the staging item directory)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # the staging item directory
R3 = ROOT / "work" / "r3"
RECEIPTS = ROOT / "receipts"

BASE = "040b6df2c40b0f4f88f51e4c2062eafc4d7463c5"
HEAD = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"
HEAD_TREE = "50ce6da7df616635f9edd958200c2065072b643c"
OLD_HEAD = "519876fa02f5e5812f5763cef03c5fed054d6cf7"
CHANGED = [
    "agent/memory_manager.py",
    "hermes_cli/observability/schemas/hermes.shared_metrics.v3.schema.json",
    "hermes_cli/observability/shared_metrics_contract.py",
    "hermes_cli/observability/shared_metrics_loop.py",
    "tests/hermes_cli/test_shared_metrics_loop.py",
    "website/docs/developer-guide/relay-shared-metrics.md",
]
CONTRACT_TEST = ("tests/hermes_cli/test_shared_metrics_loop.py::"
                 "test_external_prefetch_records_each_exit_with_how_long_the_turn_waited")
TEST_CMD = ("HOME=<scratch>/testhome-sf-memory-prefetch-metric HERMES_HOME=$HOME/.hermes "
            "HERMES_PYTHON=<read-only py3.11 venv>/bin/python bash scripts/run_tests.sh -j 2 "
            "tests/hermes_cli/test_shared_metrics_loop.py -q")
ENV_PY = "3.11.14 (<read-only py3.11 venv>, used read-only as HERMES_PYTHON)"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def write(name: str, receipt: dict) -> None:
    text = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    assert "/home/" not in text and "/tmp/" not in text and "/mnt/" not in text and "/workspace/" not in text, name
    (RECEIPTS / name).write_text(text, encoding="utf-8")
    print(name, hashlib.sha256(text.encode()).hexdigest())


def cell(run: dict) -> dict:
    out = {"observed": run["summary"], "failed": run["failed"], "log_sha256": run["log_sha256"]}
    if run.get("flaky_retry_printed"):
        out["flaky_retry_printed"] = True
    return out


def first_assertion(run: dict) -> str:
    lines = [ln for ln in run["assertion_lines"] if ln.startswith("E       AssertionError")]
    return lines[0].removeprefix("E       ").strip() if lines else ""


# ---- F08 r03 -------------------------------------------------------------------------------------
prove = json.loads((R3 / "prove" / "prove_results.json").read_text(encoding="utf-8"))
runs = prove["runs"]
assert prove["head"] == HEAD and prove["base"] == BASE
red = runs["red"]
sab = runs["sabotage"]
stall_new, stall_old = runs["stall_amended_1500ms"], runs["stall_round2_150ms"]
assert red["failed"] == [CONTRACT_TEST]
assert all(g["failed"] == [] and g["summary"].startswith("=== Summary: 1 files, 16 tests passed, 0 failed") for g in runs["green"])
assert all(s["failed"] == [CONTRACT_TEST] for s in sab) and len(sab) == 10
assert stall_new["failed"] == [] and stall_old["failed"] == [CONTRACT_TEST]
assert runs["adjacent_base"]["failed"] == [] and runs["adjacent_head"]["failed"] == []
assert not any(r.get("flaky_retry_printed") for r in [red, *runs["green"], *sab, stall_new])

f08 = {
    "schema": "xf.receipt.v1",
    "id": "F08/r20261001-03",
    "experiment": ("F08: RED on base, GREEN x3, per-hunk sabotage, stall tolerance and adjacent for the amended head on "
                   "current main. Round-1 re-verifier: the contract test pinned sub-2 s wall-clock buckets "
                   "(lt_100ms rows; 250ms_to_500ms at a 0.3 s timeout), against AGENTS.md's timing-test rule."),
    "tier": "T1",
    "cost_usd": 0.0,
    "lane": "cpu",
    "spec": {"path": None, "prereg_commit": None,
             "note": ("Not pre-registered on claude/ledger (xf not built yet). The new oracle was fixed before these runs: "
                      "exact (provider, outcome, count) rows, the timed-out row in the timeout's own bucket "
                      "(tool_latency_bucket(2000) = 2s_to_5s), every other row in a bucket a wait shorter than the "
                      "timeout can produce.")},
    "runner_revision": {"driver": f"work/r3/mpm_prove_r3.py (sha256 {sha(R3 / 'mpm_prove_r3.py')})",
                        "test_runner": "scripts/run_tests.sh blob 8fcc4294f4"},
    "issue": None,
    "origin_refs": ["NousResearch/hermes-agent@25c1b008c8", "NousResearch/hermes-agent#124151",
                    "NousResearch/hermes-agent#120042"],
    "staging": "memory-prefetch-metric",
    "base_revision": BASE,
    "head_revision": HEAD,
    "head_tree": HEAD_TREE,
    "changed_files": CHANGED,
    "inputs": {
        "test_file_blob_head": "b196fa421f0be0519338e09c6c449f310f810304",
        "test_file_blob_base": "3d29db97d853ef0f0277f5f8217e42919a225492",
        "production_seam": {"file": "agent/memory_manager.py", "symbol": "MemoryManager._prefetch_provider",
                            "blob_head": "d7302aeb1187be575de352d29336f73c4288290a",
                            "blob_base": "d023a57f8bc8ddde607c1f7ba519331aedc5952f"},
        "builder": {"file": "hermes_cli/observability/shared_metrics_loop.py",
                    "symbols": ["memory_prefetch_fields", "record_memory_prefetch"],
                    "blob_head": "0689e32eaf7779a2e767775ea6a6eb201da67878"},
        "amendment": ("Round-2 head 519876fa02 (on aea969677c) cherry-picked onto e8c97320ac, amended, then cherry-picked "
                      "onto 040b6df2c4 (clean; main's 2 commits touch no invalidate_on path): (1) the "
                      "contract test uses a 2.0 s timeout and asserts the timed-out row in the timeout's bucket and "
                      "every other row below it, instead of lt_100ms / 250ms_to_500ms at 0.3 s; (2) success vs empty is "
                      "classified inside the guarded builder from the raw returned value (record_memory_prefetch(..., "
                      "'success', started, recalled=result)) instead of in the caller. Schema, contract and doc blobs "
                      "are unchanged."),
    },
    "policy_revision": {
        "AGENTS.md": f"65aa3e61bcba610da21279a17385671263be39e9@{BASE[:10]}",
        "AGENTS.md:384-385": ("\"Timing tests must not assume a quiet runner: wall-clock bounds >= 2s, event-based sync, "
                              "no `assert not _wait_until(...)` races.\" (4441a2a28d2, 2026-09-04)"),
        "CONTRIBUTING.md": f"b0baa59b5057c204b3c09d3dd170c0955cfdb39c@{BASE[:10]}",
        "factory": "FACTORY.md (frontier-2026-10-01)",
    },
    "env": {"host": "<local-host>", "python": ENV_PY, "pytest": "9.1.1", "nemo_relay_native": True,
            "sandbox": ("no bwrap; HOME/HERMES_HOME forced to a scratch test home; run_tests.sh clean env "
                        "(TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0)"),
            "network": "none used by tests",
            "load1_at_start": prove["load1_at_start"], "load1_at_end": prove["load1_at_end"],
            "window": f"{prove['started']} .. {prove['finished']}"},
    "command": TEST_CMD,
    "gates": {
        "red": {"arm": f"base (test file at head, the 5 production files checked out from {BASE[:10]})",
                "result": "PASS", **cell(red), "assertion": first_assertion(red) +
                "  (Right contains 5 more items, first extra item: ('honcho', 'success', 1))",
                "seam_covered": "yes by construction: the test calls MemoryManager.prefetch_all -> _prefetch_provider; no monkeypatch of the seam"},
        "green": [{"rep": i + 1, **cell(g)} for i, g in enumerate(runs["green"])],
        "green_reps_agree": f"{len(runs['green'])}/{len(runs['green'])}",
        "sabotage": {
            "per_hunk": [{"mutation": s["label"].removeprefix("sabotage_"), "file": s["mutation"]["file"],
                          "red_again": True, "assertion": first_assertion(s), **cell(s)} for s in sab],
            "new_in_round_3": {
                "S9-empty-classification": "removes the builder's success->empty rule (the new hunk)",
                "S10-constant-latency-above-timeout": ("waited_ms=2500 for every row: with the 2 s timeout no constant "
                                                       "latency can satisfy both the timed-out bound and the shorter "
                                                       "bound, so S8 (constant 0) and S10 (constant above) both re-RED"),
            },
            "unpinned_hunks": ["website/docs row (checked by T0-SCHEMA, not by pytest)",
                               "schema JSON def (checked by T0-SCHEMA; the pytest store path does not read the JSON schema)"],
        },
        "stall_tolerance": {
            "method": ("every fake provider's prefetch() sleeps before answering (exact string replacement in the test "
                       "file for that cell only)"),
            "amended_test_1500ms_stall": {"result": "PASS (expected PASS)", **cell(stall_new)},
            "round2_test_150ms_stall": {
                "arm": f"the 6 changed files from the round-2 head {OLD_HEAD[:10]} on {BASE[:10]}",
                "result": "FAIL (expected FAIL: shows the flake the re-verifier named)",
                "assertion": "the success/empty/failed rows land in 100ms_to_250ms instead of lt_100ms", **cell(stall_old)},
        },
        "adjacent": {
            "files": ["tests/agent/test_memory_provider.py", "tests/agent/test_memory_async_sync.py",
                      "tests/agent/test_memory_session_switch.py", "tests/agent/test_memory_skill_scaffolding.py",
                      "tests/agent/test_memory_sync_interrupted.py", "tests/agent/test_turn_context.py",
                      "tests/hermes_cli/test_relay_shared_metrics.py", "tests/hermes_cli/test_relay_shared_metrics_runtime.py",
                      "tests/hermes_cli/test_shared_metrics_signals.py", "tests/hermes_cli/test_shared_metrics_efficiency.py",
                      "tests/hermes_cli/test_shared_metrics_harness.py", "tests/hermes_cli/test_shared_metrics_loop.py"],
            "base": runs["adjacent_base"]["summary"], "head": runs["adjacent_head"]["summary"],
            "base_failed": [], "head_failed": [], "identical": True,
            "note": "head has one more test (the new contract test); no failures on either side",
            "pre_existing_failures": [],
            "log_sha256": {"base": runs["adjacent_base"]["log_sha256"], "head": runs["adjacent_head"]["log_sha256"]},
        },
        "disabled_collection": {"test": "test_disabled_shared_metrics_record_no_loop_rows (extended with a prefetch call)",
                                "head": "PASS in all GREEN reps",
                                "base": "PASS (guard, not a red test: base records nothing either)"},
        "timing_bounds": {
            "timed_out_row": ("waited >= 2.0 s is guaranteed by Thread.join(timeout); it must stay below the 5 s bucket "
                              "edge, so the slack is 3 s"),
            "other_rows": "waited < 2.0 s (the skip row does not call the provider at all)",
            "smallest_wall_clock_bound": "2.0 s (AGENTS.md: >= 2s)",
            "test_wall_cost": "about 2 s per run (one 2 s join on the stuck provider)",
        },
        "flaky": False,
        "flaky_basis": ("no wall-clock bound below 2 s in the contract test; GREEN 3/3 with no FLAKY retry line; the "
                        "test still passes with every fake provider stalled 1.5 s"),
    },
    "measurements": [
        {"name": "contract_test_red_on_base", "value": 1, "unit": "failed tests", "label": "OBSERVED"},
        {"name": "green_reps_passing", "value": 3, "n": 3, "unit": "reps", "label": "OBSERVED"},
        {"name": "sabotage_mutations_re_red", "value": 10, "n": 10, "unit": "mutations", "label": "OBSERVED"},
        {"name": "stall_1500ms_amended_test_passes", "value": 1, "n": 1, "unit": "runs", "label": "OBSERVED"},
        {"name": "stall_150ms_round2_test_fails", "value": 1, "n": 1, "unit": "runs", "label": "OBSERVED"},
        {"name": "adjacent_tests_passed_base", "value": 330, "unit": "tests", "label": "OBSERVED"},
        {"name": "adjacent_tests_passed_head", "value": 331, "unit": "tests", "label": "OBSERVED"},
    ],
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
    "not_tested": ["real provider backends (Honcho/Hindsight/mem0 servers)", "py3.14 CI matrix", "Windows/macOS"],
    "limitations": [
        "A runner stall longer than 3 s inside the one 2 s join would push the timed-out row to 5s_to_10s and fail the test (bound >= 2 s, as AGENTS.md allows)",
        "The 1.5 s stall cell slows the providers, not the caller's thread",
        "Relay is the test fixture fake (direct_runtime) in pytest; E17 covers the real binding",
    ],
    "verdict": "KEEP",
    "provenance": "self",
    "privacy": "public-aggregate",
    "ai_assistance": "Claude Code (Opus 5.5) wrote the change, tests and this receipt",
    "raw_artifacts": {"results": {"path": rel(R3 / "prove" / "prove_results.json"), "sha256": sha(R3 / "prove" / "prove_results.json")}},
    "intermediate_run": ("The same driver ran first on an intermediate amend, 61fc6ea62d on e8c97320ac (same production code; "
                         "the test's timeout comment overclaimed and was reworded). Every cell gave the same result. Its "
                         "outputs are kept under work/r3/superseded-61fc6ea62d/ and are not cited."),
    "supersedes": {"id": "F08/r20261001-02", "path": "receipts/F08-r20261001-02.json",
                   "sha256_as_written": "160bd52592adbd0a06b8687903f4db88d5b9b55620e16d3cc50b0174c9fcc13f",
                   "why": ("its contract test asserted sub-2 s wall-clock buckets (flake risk listed under limitations "
                           "while flaky=false); head amended and moved to current main")},
}
write("F08-r20261001-03.json", f08)

# ---- T0-SCHEMA r03 -------------------------------------------------------------------------------
t0 = json.loads((R3 / "t0_schema_contract_check_r3.json").read_text(encoding="utf-8"))
assert t0["all_pass"]
t0r = {
    "schema": "xf.receipt.v1",
    "id": "T0-SCHEMA/r20261001-03",
    "experiment": "Static schema <-> contract <-> doc agreement for hermes.memory.prefetch.count; which layer bounds each label; builder samples for the amended builder",
    "tier": "T0",
    "cost_usd": 0.0,
    "lane": "cpu",
    "staging": "memory-prefetch-metric",
    "base_revision": BASE,
    "head_revision": HEAD,
    "head_tree": HEAD_TREE,
    "inputs": {"checker": {"path": rel(R3 / "t0_schema_contract_check_r3.py"), "sha256": sha(R3 / "t0_schema_contract_check_r3.py")},
               "schema_blob": "21cfe11bf70b3669a1a781e87aff0b2a5e09db26",
               "contract_blob": "c8443e460013288c2523bbb90157d3aede66766f",
               "loop_blob": "0689e32eaf7779a2e767775ea6a6eb201da67878",
               "note": "schema, contract and doc blobs are identical to T0-SCHEMA/r20261001-02; only the builder (loop) changed"},
    "command": ("env -i PATH=/usr/bin:/bin <read-only py3.11 venv>/bin/python work/r3/t0_schema_contract_check_r3.py "
                f"--repo <worktree at {HEAD[:10]}> --out work/r3/t0_schema_contract_check_r3.json"),
    "results": {"metric": t0["metric"], "checks": t0["checks"], "rejection_split": t0.get("rejection_split"),
                "schema_provider_type": t0.get("schema_provider_type")},
    "interpretation": {
        "provider_bound": ("The schema types provider as vocabulary_identifier and checks the pattern only, so a lowercase "
                           "raw name such as `hindsight` validates. The closed set is enforced by the contract "
                           "(counter_dimensions_are_valid at the mark projection and the store write) and the builder's "
                           "provider rule, which sabotage S6 pins."),
        "empty_rule": ("The builder turns `success` into `empty` when the raw returned value holds no text: '  ', None and "
                       "a non-str value all give `empty`, and none raises. A non-str value with text (for example a "
                       "structured result) also counts as `empty`."),
    },
    "label": "OBSERVED",
    "verdict": "KEEP",
    "provenance": "self",
    "privacy": "public-aggregate",
    "raw_artifacts": {"result": {"path": rel(R3 / "t0_schema_contract_check_r3.json"), "sha256": sha(R3 / "t0_schema_contract_check_r3.json")}},
    "supersedes": {"id": "T0-SCHEMA/r20261001-02", "path": "receipts/T0-SCHEMA-r20261001-02.json",
                   "sha256_as_written": "c333b0e7c47e55ffd4f7ef6078e6c63c24a71f692995283d22065c948da1ecf8",
                   "why": "the builder changed (success/empty classified inside it); same schema/contract/doc checks, builder samples 5 -> 9"},
}
write("T0-SCHEMA-r20261001-03.json", t0r)

# ---- E17 r04 (fault probe + microbenchmark + holographic, rerun on the amended head) --------------
e17 = json.loads((R3 / "e17_result_r3.json").read_text(encoding="utf-8"))
e17c = json.loads((R3 / "e17c_result_r3.json").read_text(encoding="utf-8"))
assert all(e17["checks"]["outcome_classes_match_expected"].values()) and all(e17["checks"]["one_row_per_turn_head"].values())
assert e17["checks"]["base_records_nothing"] and e17["checks"]["returned_context_identical_across_arms"]
assert e17["checks"]["profile_scope"]["pass"] and e17["checks"]["collection_off"]["pass"] and not e17["checks"]["egress_blocked_attempts"]
assert e17c["rows_match_turns"] and not e17c["egress_blocked_attempts"]
mic = e17["microbenchmark"]
faults = {}
for name, r in e17["faults"].items():
    if isinstance(r.get("turn_wait_ms"), dict):
        faults[name] = {"backend_fault": r["backend_path"], "expected_outcome": r["expected_outcome"],
                        "observed_head_rows": r["head_rows"], "observed_base_rows": r["base_rows"],
                        "turn_wait_ms": r["turn_wait_ms"],
                        "returned_context_identical_across_arms": r["returned_context_identical_across_arms"]}
    else:
        faults[name] = r
off, on = mic["collection_off"], mic["collection_on"]
e17r = {
    "schema": "xf.receipt.v1",
    "id": "E17/r20261001-04",
    "experiment": ("E17 rerun on the amended head: delay/hang/empty/error fault probe against a local fake memory backend "
                   "through the real turn-start prefetch path, profile-scope and collection-off checks, a base-vs-head "
                   "microbenchmark, and the bundled holographic provider (E17c)"),
    "tier": "T1",
    "cost_usd": 0.0,
    "lane": "cpu",
    "spec": {"path": None, "prereg_commit": None, "note": "Not pre-registered; same probe and expectations as r03, unchanged."},
    "staging": "memory-prefetch-metric",
    "origin_refs": ["NousResearch/hermes-agent#124151", "NousResearch/hermes-agent#120042",
                    "evals/memory/honcho_current_query.py pattern",
                    "evals/provider_fallback/probe_104260.py:11-39 isolation + loopback guard"],
    "base_revision": BASE,
    "head_revision": HEAD,
    "head_tree": HEAD_TREE,
    "arms": {"head": f"MemoryManager from the staging commit {HEAD[:10]}",
             "base": ("main's agent/memory_manager.py (blob d023a57f8b, sha256 048842c1...) loaded from source into the head "
                      "tree; it is the only file on the prefetch call path whose record calls differ")},
    "inputs": {"probe": {"path": "work/e17_prefetch_fault_probe.py", "sha256": sha(ROOT / "work" / "e17_prefetch_fault_probe.py")},
               "holographic_probe": {"path": "work/e17c_holographic_probe.py", "sha256": sha(ROOT / "work" / "e17c_holographic_probe.py")},
               "base_memory_manager": {"path": "work/r3/base_memory_manager_d023a57f8b.py",
                                       "sha256": sha(R3 / "base_memory_manager_d023a57f8b.py")}},
    "env": {"host": "<local-host>", "python": "3.11.14 (<read-only py3.11 venv>, used read-only)", "nemo_relay_native": e17["relay_native"],
            "relay": "REAL nemo_relay native binding (0.8.4 in this venv; main pins >=0.9 on py3.14)",
            "sandbox": "env -i; os.environ cleared; HOME/HERMES_HOME in a fresh scratch sandbox; send: false",
            "network": "none; loopback-only socket.connect guard", "load1_end": e17["load1_end"]},
    "commands": [
        ("env -i PATH=/usr/bin:/bin <read-only py3.11 venv>/bin/python work/e17_prefetch_fault_probe.py "
         f"--repo <worktree at {HEAD[:10]}> --base-mm work/r3/base_memory_manager_d023a57f8b.py --out work/r3/e17_result_r3.json"),
        ("env -i PATH=/usr/bin:/bin <read-only py3.11 venv>/bin/python work/e17c_holographic_probe.py "
         f"--repo <worktree at {HEAD[:10]}> --out work/r3/e17c_result_r3.json"),
    ],
    "reps_per_fault_per_arm": e17["reps"],
    "timeout_s": e17["timeout_s"],
    "results": {"faults": faults, "checks": e17["checks"], "microbenchmark": mic, "holographic": e17c},
    "measurements": [
        {"name": "outcome_class_matches_fault", "value": 7, "n": 7, "label": "OBSERVED"},
        {"name": "rows_per_turn_head", "value": "1 row per turn for every fault (12/12 x 7 faults)", "label": "OBSERVED"},
        {"name": "rows_base", "value": 0, "label": "OBSERVED"},
        {"name": "hang_skips_while_stuck", "value": "1 timed_out (1s_to_2s) then 3 skipped (lt_100ms); 1 backend call while hung; 1 success after release", "label": "OBSERVED"},
        {"name": "shipped_8s_bound_hang", "value": f"{e17['faults']['hang_default_timeout']['turn_wait_ms']} ms -> 5s_to_10s timed_out", "label": "OBSERVED"},
        {"name": "delta_head_minus_base_us_off", "value": off["delta_head_minus_base_us"], "aa": off["aa_base_minus_base_us"],
         "n": f"{off['blocks']} blocks x {off['calls_per_block']}", "label": "OBSERVED"},
        {"name": "delta_head_minus_base_us_on", "value": on["delta_head_minus_base_us"], "aa": on["aa_base_minus_base_us"],
         "n": f"{on['blocks']} blocks x {on['calls_per_block']}", "label": "OBSERVED"},
        {"name": "holographic_rows", "value": e17c["row_outcome_counts"], "n": e17c["turns"], "label": "OBSERVED"},
    ],
    "interpretation": {
        "outcomes": "unchanged from r03 after the amendment: every fault class gives the expected outcome, one row per turn, none on base",
        "prompt_prefix": "unchanged: the context string returned to the turn is identical across arms for all 7 faults",
        "hot_path": (f"NOT below per-call microbenchmark noise. Median head-minus-base per _prefetch_provider call: "
                     f"+{off['delta_head_minus_base_us']['median']} us collection off (p05..p95 "
                     f"+{off['delta_head_minus_base_us']['p05']}..+{off['delta_head_minus_base_us']['p95']}; A/A median "
                     f"{off['aa_base_minus_base_us']['median']:+}, p05..p95 {off['aa_base_minus_base_us']['p05']:+}..{off['aa_base_minus_base_us']['p95']:+}) "
                     f"and +{on['delta_head_minus_base_us']['median']} us on (+{on['delta_head_minus_base_us']['p05']}..+{on['delta_head_minus_base_us']['p95']}; "
                     f"A/A median {on['aa_base_minus_base_us']['median']:+}, p05..p95 {on['aa_base_minus_base_us']['p05']:+}..{on['aa_base_minus_base_us']['p95']:+}). "
                     "r03 (round-1 head, load1 5-17) measured +47.05 off / +158.76 on. Owner decision."),
    },
    "evidence_class": {"local": True, "ci": "none", "simulation": True, "runtime": False, "kind": "mechanism"},
    "not_tested": ["real memory backends (Honcho, Hindsight, mem0, Supermemory servers)", "packages sent upstream (send: false)",
                   "the turn's other phases (model call, tools)", "py3.14 interpreter with nemo-relay 0.9 (the shipped shared-metrics runtime)",
                   "remote memory backends with real network latency"],
    "limitations": ["The fake backend is a local HTTP server; real backend latency distributions are not measured here",
                    f"The microbenchmark ran on a shared host (load1 {e17['load1_end']:.1f} at the end); A/A is reported beside every delta",
                    "Store drain uses relay_shared_metrics._reset_for_tests(), the same hook the upstream tests use",
                    "holographic swallows its own errors and returns \"\", so a failing holographic recall reports as empty, not failed"],
    "verdict": "KEEP (mechanism); hot-path gate recorded as NOT MET as worded (owner decision)",
    "provenance": "self",
    "privacy": "public-aggregate (synthetic fixtures only)",
    "raw_artifacts": {"e17_result": {"path": rel(R3 / "e17_result_r3.json"), "sha256": sha(R3 / "e17_result_r3.json")},
                      "e17c_result": {"path": rel(R3 / "e17c_result_r3.json"), "sha256": sha(R3 / "e17c_result_r3.json")}},
    "supersedes": {"id": "E17/r20261001-03", "path": "receipts/E17-r20261001-03.json",
                   "sha256_as_written": "c0e152d4f9123bac071bf1dd05a8e88b5172076def0c6827cde26b99731d761d",
                   "why": "measured at c815543bc2; the amended head changes the success/empty call, so E17 was rerun on it"},
}
write("E17-r20261001-04.json", e17r)

# ---- E17d r02 (in-place attribution, amended head) -----------------------------------------------
e17d = json.loads((R3 / "micro_attribution_r3.json").read_text(encoding="utf-8"))
assert not e17d["egress_blocked_attempts"]
mo, mn = e17d["modes"]["collection_off"], e17d["modes"]["collection_on"]
c_off, c_on = mo["contrasts_us"], mn["contrasts_us"]
e17dr = {
    "schema": "xf.receipt.v1",
    "id": "E17d/r20261001-02",
    "experiment": ("E17d rerun on the amended head: attribute the per-call cost the staging commit adds to "
                   "MemoryManager._prefetch_provider (in place, base vs head variants), collection off and on"),
    "tier": "T1",
    "cost_usd": 0.0,
    "lane": "cpu",
    "spec": {"path": None, "prereg_commit": None, "note": "Same arms and contrasts as r01; only the no-op stand-in takes the amended signature."},
    "staging": "memory-prefetch-metric",
    "origin_refs": ["E17d/r20261001-01", "E17/r20261001-04"],
    "base_revision": BASE,
    "head_revision": HEAD,
    "head_tree": HEAD_TREE,
    "arms": {"base": "main's agent/memory_manager.py (blob d023a57f8b) loaded from source into the head tree",
             "base_aa": "the same base class again (A/A)", "head": "the staging commit's MemoryManager",
             "head_noop": "head, with record_memory_prefetch swapped for a no-op during the block (head - head_noop = the record call in place)",
             "head_hoisted": "head source with the function-level import moved to module level (head - head_hoisted = the per-call import statement)"},
    "inputs": {"script": {"path": rel(R3 / "micro_attribution_r3.py"), "sha256": sha(R3 / "micro_attribution_r3.py")},
               "base_memory_manager": {"path": "work/r3/base_memory_manager_d023a57f8b.py", "sha256": sha(R3 / "base_memory_manager_d023a57f8b.py")}},
    "env": {"host": "<local-host>", "python": "3.11.14 (<read-only py3.11 venv>, used read-only)", "nemo_relay_native": True,
            "sandbox": "env -i; os.environ cleared; collection-off and collection-on profiles in a fresh scratch sandbox (send: false)",
            "network": "none; loopback-only socket.connect guard",
            "load1": {"start": e17d["load1_start"], "end": e17d["load1_end"]},
            "provider": "in-process instant provider (not bundled, reports as plugin); every call takes the success exit"},
    "command": ("env -i PATH=/usr/bin:/bin <read-only py3.11 venv>/bin/python work/r3/micro_attribution_r3.py "
                f"--repo <worktree at {HEAD[:10]}> --base-mm work/r3/base_memory_manager_d023a57f8b.py --sandbox-root <scratch> "
                "--out work/r3/micro_attribution_r3.json"),
    "design": {"blocks": e17d["blocks"], "calls_per_block": e17d["calls_per_block"],
               "order": "arms rotated by block index, reversed on odd blocks",
               "statistic": "median and p05/p95 of per-block differences (us per call)", "standalone_calls_per_block": 2000},
    "results": e17d["modes"],
    "measurements": [
        {"name": "delta_head_minus_base_us_off", "value": c_off["head_minus_base"], "aa": c_off["aa_base_aa_minus_base"], "label": "OBSERVED"},
        {"name": "record_call_in_place_us_off (head - head_noop)", "value": c_off["head_minus_head_noop"], "label": "OBSERVED"},
        {"name": "everything_but_the_record_call_us_off (head_noop - base)", "value": c_off["head_noop_minus_base"], "label": "OBSERVED"},
        {"name": "per_call_import_statement_us_off (head - head_hoisted)", "value": c_off["head_minus_head_hoisted"], "label": "OBSERVED"},
        {"name": "delta_head_minus_base_us_on", "value": c_on["head_minus_base"], "aa": c_on["aa_base_aa_minus_base"], "label": "OBSERVED"},
        {"name": "record_call_in_place_us_on (head - head_noop)", "value": c_on["head_minus_head_noop"], "label": "OBSERVED"},
        {"name": "everything_but_the_record_call_us_on (head_noop - base)", "value": c_on["head_noop_minus_base"], "label": "OBSERVED"},
        {"name": "standalone_us_median", "value": {"off": mo["standalone_us_median"], "on": mn["standalone_us_median"]}, "label": "OBSERVED"},
    ],
    "interpretation": {
        "attribution": (f"Collection off: head - base median +{c_off['head_minus_base']['median']} us "
                        f"(p05..p95 +{c_off['head_minus_base']['p05']}..+{c_off['head_minus_base']['p95']}); A/A "
                        f"{c_off['aa_base_aa_minus_base']['median']:+} ({c_off['aa_base_aa_minus_base']['p05']:+}..{c_off['aa_base_aa_minus_base']['p95']:+}). "
                        f"With the record call swapped for a no-op: {c_off['head_noop_minus_base']['median']:+} us "
                        f"({c_off['head_noop_minus_base']['p05']:+}..{c_off['head_noop_minus_base']['p95']:+}), so the import, the clock read "
                        f"and the lock reshuffle cost a few us at most and the record call in place costs about "
                        f"{round(c_off['head_minus_head_noop']['median'])} us. Collection on: +{c_on['head_minus_base']['median']} us, "
                        f"no-op {c_on['head_noop_minus_base']['median']:+}, record call in place +{c_on['head_minus_head_noop']['median']}."),
        "standalone": (f"Alone in a tight loop record_memory_prefetch costs {mo['standalone_us_median']['record_memory_prefetch']} us off "
                       f"(enabled() alone {mo['standalone_us_median']['enabled_gate_only']}) and {mn['standalone_us_median']['record_memory_prefetch']} on, "
                       f"against record_execution_backend {mo['standalone_us_median']['record_execution_backend_existing']} / "
                       f"{mn['standalone_us_median']['record_execution_backend_existing']}. The in-place cost of the existing record_* sites "
                       "was not measured."),
        "gate": "The selection gate 'hot-path overhead stays below noise in a microbenchmark' is still NOT met. Owner decision.",
    },
    "evidence_class": {"local": True, "ci": "none", "simulation": True, "runtime": False, "kind": "cost"},
    "not_tested": ["py3.14 with nemo-relay 0.9", "the in-place cost of the existing record_* call sites",
                   "why the in-place record call costs more than the tight-loop call", "other exits (only the success exit is benchmarked)"],
    "limitations": [f"Shared host (load1 {e17d['load1_start']:.1f} -> {e17d['load1_end']:.1f}, other agents); absolute microseconds are inflated, A/A included",
                    "On this quieter run the no-op arm sits just above the A/A range, so the non-record edits are measurable but small"],
    "verdict": "KEEP (cost attribution); hot-path gate NOT MET as worded",
    "provenance": "self",
    "privacy": "public-aggregate (synthetic fixtures only)",
    "raw_artifacts": {"result": {"path": rel(R3 / "micro_attribution_r3.json"), "sha256": sha(R3 / "micro_attribution_r3.json")}},
    "supersedes": {"id": "E17d/r20261001-01", "path": "receipts/E17d-r20261001-01.json",
                   "sha256_as_written": "7e3a8638ab38c5cff3ec137cb2f5e2941d2df40297a44feaf3c6eabd29a897ba",
                   "why": "measured at 519876fa02; rerun on the amended head"},
}
write("E17d-r20261001-02.json", e17dr)

# ---- MERGE r03 -----------------------------------------------------------------------------------
mm = json.loads((R3 / "merge_matrix_r3.json").read_text(encoding="utf-8"))
NEWEST_MAIN = mm["main"]
TOUCHES = {
    "124151": "agent/memory_manager.py: per-provider prefetch bound (Hindsight 20 s)",
    "120042": "agent/memory_manager.py: default external prefetch bound 8 s -> 12 s",
    "98045": "agent/agent_init.py + config: configurable external prefetch timeout (does not edit memory_manager.py)",
    "92118": "agent/memory_manager.py _prefetch_provider return path: str or MemoryPrefetchResult (structured observations)",
    "126457": "agent/memory_manager.py _prefetch_provider timeout exit: marks the provider unavailable for a CLI health indicator",
    "87028": "agent/memory_manager.py _prefetch_provider: honor the external prefetch timeout",
    "86948": "agent/memory_manager.py: configurable provider timeouts",
    "65329": "agent/turn_context.py: opt-in local turn trace with a prologue.memory_prefetch span around prefetch_all",
    "125802": "agent/turn_context.py: decouple memory prefetch from the user-message channel (does not edit our files)",
    "78584": "temporary chats (91 files incl. agent/memory_manager.py); not about prefetch metrics",
}
overlaps = {}
for n, row in mm["prs"].items():
    overlaps[n] = {"author": row["author"], "head": row["pr_head"], "touches": TOUCHES[n],
                   "vs_main": row["main"], "vs_staging_head": row["staging_head"], "vs_round2_head": row["round2_head"]}
overlaps["124151"]["tests_on_merged_tree"] = {
    "method": "git merge --no-commit of the PR head into the staging head in the stfix worktree (clean), then aborted",
    "command": "scripts/run_tests.sh -j 2 tests/hermes_cli/test_shared_metrics_loop.py tests/agent/test_memory_provider.py -q",
    "observed": "2 files, 74 tests passed, 0 failed", "log_sha256": sha(R3 / "merged_124151_tests.log")}
overlaps["120042"]["tests_on_merged_tree"] = {
    "method": "git merge --no-commit of the PR head into the staging head (clean), then aborted",
    "command": "scripts/run_tests.sh -j 2 tests/hermes_cli/test_shared_metrics_loop.py tests/agent/test_memory_provider.py -q",
    "observed": "2 files, 72 tests passed, 0 failed", "log_sha256": sha(R3 / "merged_120042_tests.log")}
overlaps["126457"]["conflict"] = {
    "hunk": ("timeout exit of _prefetch_provider: ours adds `record_memory_prefetch(provider.name, \"timed_out\", started)`, "
             "theirs adds `self._record_provider_failure(provider, ...)` at the same place before `return \"\"`"),
    "resolution": "keep both lines (work/r3/resolve_keep_both.py); both calls are internally guarded and never raise",
    "tests_on_resolved_tree": {
        "command": ("scripts/run_tests.sh -j 2 tests/hermes_cli/test_shared_metrics_loop.py tests/agent/test_memory_provider.py "
                    "tests/agent/test_memory_health.py -q"),
        "observed": "3 files, 115 tests passed, 0 failed", "log_sha256": sha(R3 / "merged_126457_tests.log")}}
overlaps["92118"]["conflict"] = {
    "hunk": ("return path of _prefetch_provider: ours inserts the success/empty record line right before "
             "`if result and result.strip():`, which #92118 rewrites to `if isinstance(result, str) and result.strip():`"),
    "hazard_round2": ("the round-2 head computed the outcome in the caller (`\"success\" if result and result.strip() else "
                      "\"empty\"`), outside _emit's guard; with #92118 `result` can be a MemoryPrefetchResult, so a "
                      "keep-both resolution raised AttributeError and #92118's per-provider except dropped that provider's "
                      "recalled context"),
    "fix_round3": ("the amended head passes the raw value (`record_memory_prefetch(provider.name, \"success\", started, "
                   "recalled=result)`) and the builder classifies it inside _emit's guard with an isinstance check, so "
                   "nothing on the prefetch path can raise because of the metric"),
    "naive_resolution_probe": {
        "method": ("git merge --no-commit of 2ad5cc73fa into each head, conflict resolved by keeping our record line plus "
                   "their isinstance line (work/r3/resolve_92118.py), then a temporary test (work/r3/test_zz_probe_92118.py, "
                   "never committed) prefetches through a provider returning MemoryPrefetchResult(context='- prefers tabs') "
                   "with shared metrics on; merge aborted afterwards"),
        "round2_head": "context '' (dropped), no row; probe FAILED (also on the runner's one retry)",
        "staging_head": "context '- prefers tabs' (kept); one row ('honcho', 'empty'); probe PASSED",
        "output_sha256": sha(R3 / "probe_92118_out.txt"),
        "remaining_semantics": ("with #92118 merged, a structured result counts as `empty` until the builder reads its "
                                "`.context`; a one-line follow-up for whichever PR lands second"),
    }}
merge = {
    "schema": "xf.receipt.v1",
    "id": "MERGE/r20261001-03",
    "experiment": ("Freshness and overlap for the amended head: move to current main, merge-tree against every open PR "
                   "that edits the prefetch path, targeted tests on the clean merges, the #92118 keep-both hazard probe, "
                   "the workflow push-trigger scan and the fork-name check"),
    "tier": "T0",
    "cost_usd": 0.0,
    "lane": "cpu",
    "staging": "memory-prefetch-metric",
    "base_revision": BASE,
    "head_revision": HEAD,
    "results": {
        "rebase": {
            "from": {"head": OLD_HEAD, "base": "aea969677c60a1bb72fe227fdfb98f196a2092cc"},
            "to": {"head": HEAD, "base": BASE, "tree": HEAD_TREE},
            "commits_between_bases": 8, "invalidate_on_changed": False,
            "method": ("git cherry-pick 519876fa02 onto e8c97320ac (clean), `git commit --amend` with the test and builder "
                       "changes, then a clean cherry-pick onto 040b6df2c4 (author Kevin Rajan, author date kept). An "
                       "intermediate amend 61fc6ea62d (same code, an overclaiming test comment) was proven first and "
                       "superseded; its run is kept under work/r3/superseded-61fc6ea62d/"),
            "main_checked": {"sha": BASE, "how": "git ls-remote https://github.com/NousResearch/hermes-agent.git refs/heads/main",
                             "committed_at": "2026-10-01T12:03:56Z"},
        },
        "freshness_recheck": {"main": NEWEST_MAIN, "checked_at": mm["checked_at"], "commits_since_base": 0 if NEWEST_MAIN == BASE else None,
                              "invalidate_on_changed": False, "merge_tree": mm["staging_head_vs_main"]},
        "overlapping_open_prs": overlaps,
        "workflow_push_trigger_scan": {"tree": HEAD_TREE, "workflows": 52, "with_push_trigger": 11,
                                       "branch_names": ["staged/memory-prefetch-metric", "staging/memory-prefetch-metric"],
                                       "matches_for_branch": 0,
                                       "note": "push filters are main (9), wine2e/** and wine2e-install/**; live-providers.yml is tag-only"},
        "fork_ref_check": {"command": "git ls-remote https://github.com/kvnloo/hermes-agent.git 'refs/heads/staged/*' refs/heads/staging",
                           "staged_refs": 0, "legacy_staging_ref": "28790e597c",
                           "note": "staged/memory-prefetch-metric is free on the fork (OD-0 resolved by the staged/<id> rename)"},
    },
    "label": "OBSERVED",
    "verdict": "KEEP",
    "provenance": "self",
    "privacy": "public-aggregate",
    "raw_artifacts": {
        "merge_matrix": {"path": rel(R3 / "merge_matrix_r3.json"), "sha256": sha(R3 / "merge_matrix_r3.json")},
        "merged_124151_tests_log": {"path": rel(R3 / "merged_124151_tests.log"), "sha256": sha(R3 / "merged_124151_tests.log")},
        "merged_120042_tests_log": {"path": rel(R3 / "merged_120042_tests.log"), "sha256": sha(R3 / "merged_120042_tests.log")},
        "merged_126457_tests_log": {"path": rel(R3 / "merged_126457_tests.log"), "sha256": sha(R3 / "merged_126457_tests.log")},
        "probe_92118": {"path": rel(R3 / "probe_92118_out.txt"), "sha256": sha(R3 / "probe_92118_out.txt")},
    },
    "supersedes": {"id": "MERGE/r20261001-02", "path": "receipts/MERGE-r20261001-02.json",
                   "sha256_as_written": "5d721ad49a573add9373a7fd7b0a473dc0e43c908a7b03906f2bde6b36882fa1",
                   "why": ("old head and base; did not test merge order against #87028, #86948, #92118 (the #92118 conflict "
                           "and its hazard went unrecorded), and missed #120042, #98045, #126457 and #65329")},
}
write("MERGE-r20261001-03.json", merge)

# ---- OWNERSHIP r02 -------------------------------------------------------------------------------
search = json.loads((R3 / "ownership_prefetch_search_r3.json").read_text(encoding="utf-8"))
tek = json.loads((R3 / "teknium1_open_r3.json").read_text(encoding="utf-8"))
own = {
    "schema": "xf.receipt.v1",
    "id": "OWNERSHIP/r20261001-02",
    "experiment": ("P2 ownership refresh: does any open upstream PR add a memory prefetch metric, and which open PRs "
                   "carry demand for it or touch the same code? teknium1 open-PR recount plus 10 prefetch search queries"),
    "tier": "T0",
    "cost_usd": 0.0,
    "lane": "cpu (gh, read-only)",
    "staging": "memory-prefetch-metric",
    "base_revision": BASE,
    "head_revision": HEAD,
    "results": {
        "teknium1_open_prs": {"count": len(tek), "count_check": "gh search total_count = 260",
                              "same_set_as_r01": True, "added": [], "removed": [],
                              "title_regex": "prefetch|telemetry|metric", "title_hits": [],
                              "file_scan": "r01's scan of all 2871 changed files stands (same 260 PRs): only #113678 touches agent/memory_manager.py, outside prefetch"},
        "prefetch_search": {"searched_at": search["searched_at"],
                            "queries": {q: r.get("total") for q, r in search["queries"].items()},
                            "command": "gh api -X GET search/issues -f q='repo:NousResearch/hermes-agent is:pr is:open <query>'"},
        "adds_prefetch_metric": [],
        "demand_signals": {
            "124151": "kweez007, OPEN since 2026-09-26: timed Hindsight recall by hand, raises its prefetch bound to 20 s",
            "120042": ("Navlem, OPEN since 2026-09-23 (head 641f6b94c5): raises the default bound to 12 s after a production "
                       "audit of 18-27 s recalls and about 53 dropped prefetches in one day"),
            "98045": "Navlem, OPEN since 2026-08-29: makes the external prefetch timeout configurable",
        },
        "same_code_not_a_counter": {
            "126457": ("mozhongzhou, OPEN since 2026-09-28: CLI status-bar health indicator; marks the provider unavailable at "
                       "the _prefetch_provider timeout exit; process-local UI state, not a shared metric"),
            "65329": ("Soju06, OPEN since 2026-07-16 (head c868eaaa02, last update 2026-07-30): opt-in local JSONL turn trace "
                      "(agent.turn_trace) with a prologue.memory_prefetch span around prefetch_all tagged hit/empty; overlaps "
                      "the latency half for one machine, records nothing shared, conflicts with main in 11 files"),
            "92118": "seradin: structured prefetch observations; its body says Hermes adds no persistence, outbound delivery or telemetry",
            "87028": "richardclawbot: honor external prefetch timeout; no record/metric lines",
            "86948": "V0v1kkkAssistant: configurable provider timeouts; no record/metric lines",
            "125802": "Finn763: prefetch delivery channel in turn_context.py; no metric",
        },
        "search_hits_checked_not_overlapping": {
            "128757": "Finn763: model-switch cost message; no memory_manager/shared_metrics file",
            "129324": "OPGokuVPS: mem0 prefetch gate (plugin side, 2 files)",
            "78584": "iso2kx: temporary chats; touches memory_manager.py for session scope, not prefetch metrics",
            "68028": "jkobject: supermemory recall precision gate (plugin)",
            "106813": "remi-td: holographic retrieval usage tracking (plugin)",
            "121513": "Roblmvp: holographic fact_id in prefetch (plugin)",
        },
    },
    "verdict": "OURS (no open PR adds a prefetch counter); demand from #124151 and #120042; risk: teknium1 may land the same row himself",
    "label": "OBSERVED",
    "provenance": "self",
    "privacy": "public-aggregate (public PR metadata only)",
    "raw_artifacts": {
        "prefetch_search": {"path": rel(R3 / "ownership_prefetch_search_r3.json"), "sha256": sha(R3 / "ownership_prefetch_search_r3.json")},
        "teknium1_open": {"path": rel(R3 / "teknium1_open_r3.json"), "sha256": sha(R3 / "teknium1_open_r3.json")},
        "pr120042": {"path": rel(R3 / "pr120042.json"), "sha256": sha(R3 / "pr120042.json")},
        "pr65329": {"path": rel(R3 / "pr65329.json"), "sha256": sha(R3 / "pr65329.json")},
    },
    "supersedes": {"id": "OWNERSHIP/r20261001-01", "path": "receipts/OWNERSHIP-r20261001-01.json",
                   "sha256_as_written": "07b1659df318b5517772105c5e2b84f054516aa4b81ef3b7057d2e3d37a1869d",
                   "why": "missed #120042 (a second demand signal) and #65329, #126457, #98045 (same code, not counters)"},
}
write("OWNERSHIP-r20261001-02.json", own)
