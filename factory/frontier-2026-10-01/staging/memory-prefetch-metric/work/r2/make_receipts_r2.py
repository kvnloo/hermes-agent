"""Write the round-2 receipts for memory-prefetch-metric (rebased head 519876fa02 on main aea969677c).

Receipts carry repo-relative paths and placeholders only (<scratch>, <read-only py3.11 venv>, <worktree>).
Run from work/r2:  python3 make_receipts_r2.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGING = HERE.parent.parent
RECEIPTS = STAGING / "receipts"

BASE = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
HEAD = "519876fa02f5e5812f5763cef03c5fed054d6cf7"
HEAD_TREE = "81c2e4fab31c9a6622c57d928e399dbe8afa2986"
V1_HEAD = "c815543bc2504eccaae9f6adce5046f41710f38c"
V1_BASE = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0"
PY = "<read-only py3.11 venv>/bin/python"
CHANGED = [
    "agent/memory_manager.py",
    "hermes_cli/observability/schemas/hermes.shared_metrics.v3.schema.json",
    "hermes_cli/observability/shared_metrics_contract.py",
    "hermes_cli/observability/shared_metrics_loop.py",
    "tests/hermes_cli/test_shared_metrics_loop.py",
    "website/docs/developer-guide/relay-shared-metrics.md",
]
ENV = {
    "host": "<local-host>",
    "python": "3.11.14 (<read-only py3.11 venv>, used read-only as HERMES_PYTHON)",
    "pytest": "9.1.1",
    "nemo_relay_native": True,
    "sandbox": "no bwrap; HOME/HERMES_HOME forced to a scratch test home; run_tests.sh clean env (TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0)",
    "network": "none used by tests or probes; probes install a loopback-only socket.connect guard",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(STAGING))


def write(name: str, data: dict) -> None:
    path = RECEIPTS / name
    assert not path.exists(), f"write-once: {name} exists"
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    for needle in ("/tmp/", "/mnt/", "/workspace/", "/home/", "100.113."):
        assert needle not in text, (name, needle)
    path.write_text(text, encoding="utf-8")
    print(name, sha(path))


old_sha = {p.name: sha(p) for p in RECEIPTS.glob("*.json")}

# ---- F08 r02 ---------------------------------------------------------------------------------------
prove = json.loads((HERE / "prove" / "prove_results.json").read_text(encoding="utf-8"))
assert prove["head"] == HEAD and prove["base"] == BASE and prove["head_tree"] == HEAD_TREE
runs = prove["runs"]
CONTRACT = "tests/hermes_cli/test_shared_metrics_loop.py::test_external_prefetch_records_each_exit_with_how_long_the_turn_waited"
red_log = (HERE / "prove" / "red.log").read_text(encoding="utf-8")
assert "AssertionError: assert {} == {('honcho', '...0ms'): 1, ...}" in red_log and "Right contains 5 more items" in red_log
assert runs["red"]["failed"] == [CONTRACT]
assert all(g["failed"] == [] and "16 tests passed, 0 failed" in g["summary"] for g in runs["green"])
assert all(s["failed"] == [CONTRACT] for s in runs["sabotage"])
assert runs["adjacent_base"]["failed"] == [] and runs["adjacent_head"]["failed"] == []
f08 = {
    "schema": "xf.receipt.v1",
    "id": "F08/r20261001-02",
    "experiment": "F08 (new): per-outcome RED/GREEN with each record_ call reverted, plus RED-on-base, GREEN x3, adjacent; rerun on the head rebased onto current main",
    "tier": "T1",
    "cost_usd": 0.0,
    "lane": "cpu",
    "spec": {"path": None, "prereg_commit": None,
             "note": "Not pre-registered on claude/ledger (xf not built yet); oracle fixed in the test before the round-1 runs and unchanged."},
    "runner_revision": {"driver": f"work/r2/mpm_prove_r2.py (sha256 {sha(HERE / 'mpm_prove_r2.py')})",
                        "test_runner": "scripts/run_tests.sh blob 8fcc4294f4"},
    "issue": None,
    "origin_refs": ["NousResearch/hermes-agent@25c1b008c8", "NousResearch/hermes-agent#124151"],
    "staging": "memory-prefetch-metric",
    "base_revision": BASE,
    "head_revision": HEAD,
    "head_tree": HEAD_TREE,
    "changed_files": CHANGED,
    "inputs": {
        "test_file_blob_head": "df30f9a2a0efe28512303bb3231191baa7b45b5e",
        "test_file_blob_base": "3d29db97d853ef0f0277f5f8217e42919a225492",
        "production_seam": {"file": "agent/memory_manager.py", "symbol": "MemoryManager._prefetch_provider",
                            "blob_head": "a099c392586a074fe3be651ed60336ea76c89602",
                            "blob_base": "d023a57f8bc8ddde607c1f7ba519331aedc5952f"},
        "rebase_note": f"cherry-pick of {V1_HEAD[:10]} onto {BASE[:10]}; all 6 changed-file blobs and the base blobs are byte-identical to round 1 (main touched none of them between {V1_BASE[:10]} and {BASE[:10]})",
    },
    "policy_revision": {"AGENTS.md": f"65aa3e61bcba610da21279a17385671263be39e9@{BASE[:10]}",
                        "CONTRIBUTING.md": f"b0baa59b5057c204b3c09d3dd170c0955cfdb39c@{BASE[:10]}",
                        "factory": "FACTORY.md sha256 7726ba18b43a9367… (frontier-2026-10-01)"},
    "env": {**ENV, "load1_at_start": prove["load1_at_start"], "load1_at_end": prove["load1_at_end"]},
    "command": f"HOME=<scratch>/testhome-sf-memory-prefetch-metric HERMES_HOME=$HOME/.hermes HERMES_PYTHON={PY} bash scripts/run_tests.sh -j 2 tests/hermes_cli/test_shared_metrics_loop.py -q",
    "gates": {
        "red": {"arm": f"base (test file at head, the 5 production files checked out from {BASE[:10]})", "result": "PASS",
                "observed": runs["red"]["summary"], "failed": runs["red"]["failed"],
                "assertion": "AssertionError: assert {} == {('honcho', '...0ms'): 1, ...}  (Right contains 5 more items)",
                "seam_covered": "yes by construction: the test calls MemoryManager.prefetch_all -> _prefetch_provider; no monkeypatch of the seam",
                "log_sha256": runs["red"]["log_sha256"]},
        "green": [{"rep": i + 1, "observed": g["summary"], "failed": g["failed"], "log_sha256": g["log_sha256"]}
                  for i, g in enumerate(runs["green"])],
        "green_reps_agree": f"{len(runs['green'])}/{len(runs['green'])}",
        "sabotage": {
            "per_hunk": [{"mutation": s["label"].removeprefix("sabotage_"), "file": s["mutation"]["file"], "red_again": s["failed"] == [CONTRACT],
                          "observed": s["summary"], "failed": s["failed"], "log_sha256": s["log_sha256"]} for s in runs["sabotage"]],
            "unpinned_hunks": ["website/docs row (checked by T0-SCHEMA, not by pytest)",
                               "schema JSON def (checked by T0-SCHEMA; the pytest store path does not read the JSON schema)"],
        },
        "adjacent": {"files": runs["adjacent_head"]["cmd"].split()[4:-1],
                     "base": runs["adjacent_base"]["summary"], "head": runs["adjacent_head"]["summary"],
                     "base_failed": runs["adjacent_base"]["failed"], "head_failed": runs["adjacent_head"]["failed"],
                     "identical": True, "note": "head has one more test (the new contract test); no failures on either side",
                     "pre_existing_failures": []},
        "disabled_collection": {"test": "test_disabled_shared_metrics_record_no_loop_rows (extended with a prefetch call)",
                                "head": "PASS in all GREEN reps", "base": "PASS (guard, not a red test: base records nothing either)"},
        "flaky": False,
    },
    "measurements": [
        {"name": "contract_test_red_on_base", "value": 1, "unit": "failed tests", "label": "OBSERVED"},
        {"name": "green_reps_passing", "value": 3, "n": 3, "unit": "reps", "label": "OBSERVED"},
        {"name": "sabotage_mutations_re_red", "value": sum(s["failed"] == [CONTRACT] for s in runs["sabotage"]),
         "n": len(runs["sabotage"]), "unit": "mutations", "label": "OBSERVED"},
        {"name": "adjacent_tests_passed_base", "value": 330, "unit": "tests", "label": "OBSERVED"},
        {"name": "adjacent_tests_passed_head", "value": 331, "unit": "tests", "label": "OBSERVED"},
    ],
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
    "not_tested": ["real provider backends (Honcho/Hindsight/mem0 servers)", "py3.14 CI matrix", "Windows/macOS"],
    "limitations": ["Timing-bucket assertions use a 0.3 s timeout and instant fakes; a host stalled >200 ms could flake the bucket",
                    "Relay is the test fixture fake (direct_runtime) in pytest; E17 covers the real binding"],
    "verdict": "KEEP",
    "provenance": "self",
    "privacy": "public-aggregate",
    "ai_assistance": "Claude Code (Opus 5.5) wrote the change, tests and this receipt",
    "raw_artifacts": {"results": {"path": rel(HERE / "prove" / "prove_results.json"), "sha256": sha(HERE / "prove" / "prove_results.json")}},
    "supersedes": {"id": "F08/r20261001-01", "path": "receipts/F08-r20261001-01.json",
                   "sha256_as_written": "aeee1549bcc8e0668699abacb94002e6bdcb0b1541d11f9846433db0a6763bc6",
                   "why": f"rerun on the head rebased onto {BASE[:10]} ({HEAD[:10]}); r01's command field held a local scratch path (now redacted in place)"},
}
assert f08["gates"]["adjacent"]["files"][-1] == "tests/hermes_cli/test_shared_metrics_loop.py", f08["gates"]["adjacent"]["files"]
assert "330 tests passed, 0 failed" in runs["adjacent_base"]["summary"] and "331 tests passed, 0 failed" in runs["adjacent_head"]["summary"]
write("F08-r20261001-02.json", f08)

# ---- T0-SCHEMA r02 ---------------------------------------------------------------------------------
t0 = json.loads((HERE / "t0_schema_contract_check_r2.json").read_text(encoding="utf-8"))
assert t0["all_pass"]
write("T0-SCHEMA-r20261001-02.json", {
    "schema": "xf.receipt.v1",
    "id": "T0-SCHEMA/r20261001-02",
    "experiment": "Static schema <-> contract <-> doc agreement for hermes.memory.prefetch.count; which layer bounds each label",
    "tier": "T0",
    "cost_usd": 0.0,
    "lane": "cpu",
    "staging": "memory-prefetch-metric",
    "base_revision": BASE,
    "head_revision": HEAD,
    "head_tree": HEAD_TREE,
    "inputs": {"checker": {"path": rel(HERE / "t0_schema_contract_check_r2.py"), "sha256": sha(HERE / "t0_schema_contract_check_r2.py")},
               "schema_blob": "21cfe11bf70b3669a1a781e87aff0b2a5e09db26", "contract_blob": "c8443e460013288c2523bbb90157d3aede66766f",
               "loop_blob": "0e5e68bf26e431c31e75ffb7e7e78e76d97e9343"},
    "command": f"env -i PATH=/usr/bin:/bin {PY} work/r2/t0_schema_contract_check_r2.py --repo <worktree at {HEAD[:10]}> --out work/r2/t0_schema_contract_check_r2.json",
    "results": {k: t0[k] for k in ("metric", "schema", "checks", "rejection_split", "schema_provider_type", "doc_row", "bundled_memory_providers", "all_pass")},
    "measurements": [
        {"name": "contract_combinations_schema_valid", "value": t0["checks"]["all_contract_combinations_valid"], "label": "OBSERVED"},
        {"name": "out_of_contract_rows_rejected", "value": t0["checks"]["out_of_contract_rows_rejected"], "label": "OBSERVED"},
        {"name": "builder_samples_pass", "value": all(x["pass"] for x in t0["checks"]["builder_samples"]), "label": "OBSERVED"},
    ],
    "interpretation": {
        "provider_bound": "The JSON schema types provider as vocabulary_identifier (pattern ^[a-z0-9][a-z0-9_]{0,63}$, the same type as memory_op_counter.provider), so it checks the pattern only: a lowercase raw provider name such as `hindsight` validates against the schema. The closed provider set is enforced by the contract (counter_dimensions_are_valid over _COUNTER_DIMENSION_VALUES, applied at the mark projection and at the store write) and by the builder's memory_provider_name rule, which sabotage S6 pins (F08). Of the 6 out-of-contract rows, the schema rejects 5 and the contract rejects 6.",
        "correction": "T0-SCHEMA/r20261001-01 said 5/5 out-of-contract rows were rejected, including a 'raw provider name'; its sample (`Acme Private Memory`) failed the schema only on capitals and spaces, which overstated what the schema enforces.",
    },
    "negative_control": "On main the metric constant does not exist (contract has no MEMORY_PREFETCH_METRIC); not run as a separate cell.",
    "verdict": "KEEP",
    "provenance": "self",
    "privacy": "public-aggregate",
    "raw_artifacts": {"result": {"path": rel(HERE / "t0_schema_contract_check_r2.json"), "sha256": sha(HERE / "t0_schema_contract_check_r2.json")}},
    "supersedes": {"id": "T0-SCHEMA/r20261001-01", "path": "receipts/T0-SCHEMA-r20261001-01.json",
                   "sha256_as_written": "ad89767764a9aeaf0d792fd7797f549c5ff693983ba304cdf8715c0e3a08f722",
                   "why": "rerun on the rebased head; corrects the provider-bound wording (schema checks the pattern only) and adds the per-layer rejection split; r01's command held local paths (now redacted in place)"},
})

# ---- MERGE r02 -------------------------------------------------------------------------------------
write("MERGE-r20261001-02.json", {
    "schema": "xf.receipt.v1",
    "id": "MERGE/r20261001-02",
    "experiment": "Freshness and overlap: the head rebased onto current main, a simulated merge with the open PR that edits the same function, and the workflow push-trigger scan for the fork branch name",
    "tier": "T0",
    "cost_usd": 0.0,
    "lane": "cpu",
    "staging": "memory-prefetch-metric",
    "base_revision": BASE,
    "head_revision": HEAD,
    "results": {
        "rebase": {"from": {"head": V1_HEAD, "base": V1_BASE}, "to": {"head": HEAD, "base": BASE, "tree": HEAD_TREE},
                   "commits_between_bases": 47, "invalidate_on_changed": False,
                   "method": f"git cherry-pick {V1_HEAD[:10]} onto {BASE[:10]} (clean); diff byte-identical to round 1; HEAD^{{tree}} equals `git merge-tree --write-tree {BASE[:10]} {V1_HEAD[:10]}`",
                   "main_checked": {"sha": BASE, "how": "git ls-remote https://github.com/NousResearch/hermes-agent.git refs/heads/main", "committed_at": "2026-10-01T05:56:05-05:00"}},
        "with_NousResearch_124151": {
            "pr": 124151, "author": "kweez007", "state": "OPEN", "head": "3ee6189dbad0485790893c5098b20f00d27a1d51",
            "diff_sha256": "7242a5eb7a1b6e1590fd4ab7023e167be25d10a6d6bace505113efa87cbf2078",
            "diff_note": "round 1 recorded e43f8f1d… for the same head; the two diffs differ only in abbreviated index-hash width",
            "method": f"gh pr diff applied onto {BASE[:10]} as an unreferenced temp commit 3ed268422f (tree d43d03a2f0), then merge-tree with the staging commit both ways",
            "merge_tree": "e39976d7b2c00cee0346b379eae0cb94d1cfc979", "clean_both_ways": True,
            "tests_on_merged_tree": {"commit": "e5e0a7e336 (temp, unreferenced)",
                                     "command": "scripts/run_tests.sh -j 2 tests/hermes_cli/test_shared_metrics_loop.py tests/agent/test_memory_provider.py -q",
                                     "observed": "2 files, 74 tests passed, 0 failed",
                                     "log_sha256": sha(HERE / "merged_124151_tests.log")},
            "semantics": {"label": "DERIVED (not run)",
                          "statement": "The record calls time the real wait, so a timeout under #124151's per-provider 20 s Hindsight bound would land in latency_bucket 10s_to_30s, under provider `plugin` (Hindsight is not a bundled memory provider).",
                          "basis": "tool_latency_bucket(20000) == '10s_to_30s' (T0 builder sample mem0/EMPTY/20000) and memory_provider_name('hindsight') == 'plugin' (T0 builder sample hindsight/timed_out/8000.4). No run exercised #124151's 20 s path; the merged-tree run is the 74 targeted tests only."},
        },
        "workflow_push_trigger_scan": {"tree": HEAD_TREE, "workflows": 52, "with_push_trigger": 11,
                                       "branch_names": ["staged/memory-prefetch-metric", "staging/memory-prefetch-metric"],
                                       "matches_for_branch": 0,
                                       "note": "push filters are main (9), wine2e/** and wine2e-install/**; live-providers.yml is tag-only"},
        "fork_ref_check": {"command": "git ls-remote https://github.com/kvnloo/hermes-agent.git 'refs/heads/staged/*' refs/heads/staging",
                           "staged_refs": 0, "legacy_staging_ref": "28790e597c",
                           "note": "staged/memory-prefetch-metric is free on the fork; the legacy refs/heads/staging is why the fork branch is staged/<id> (OD-0 resolved by that rename)"},
    },
    "label": "OBSERVED (except results.with_NousResearch_124151.semantics, which is DERIVED)",
    "verdict": "KEEP",
    "provenance": "self",
    "privacy": "public-aggregate",
    "raw_artifacts": {"merged_tree_tests_log": {"path": rel(HERE / "merged_124151_tests.log"), "sha256": sha(HERE / "merged_124151_tests.log")},
                      "pr_124151_diff": {"path": rel(HERE / "pr124151.diff"), "sha256": sha(HERE / "pr124151.diff")}},
    "supersedes": {"id": "MERGE/r20261001-01", "path": "receipts/MERGE-r20261001-01.json",
                   "sha256_as_written": "95e81c42398cb6fa4fea8aaef7c67a028d9b513379b13ab60ba1256bf2f71a22",
                   "why": f"head rebased onto {BASE[:10]}; r01's semantics sentence read as observed, it is derived; adds the staged/<id> fork-name checks"},
})

# ---- OWNERSHIP r01 ---------------------------------------------------------------------------------
tek = json.loads((HERE / "ownership_teknium1_scan.json").read_text(encoding="utf-8"))
srch = json.loads((HERE / "ownership_prefetch_search.json").read_text(encoding="utf-8"))
assert tek["open_prs"] == 260 and tek["title_hits"] == [] and [h["number"] for h in tek["file_hits"]] == [113678]
write("OWNERSHIP-r20261001-01.json", {
    "schema": "xf.receipt.v1",
    "id": "OWNERSHIP/r20261001-01",
    "experiment": "P2 ownership: does any open upstream PR already add a memory prefetch metric? Full scan of teknium1's open PRs plus the prefetch search queries",
    "tier": "T0",
    "cost_usd": 0.0,
    "lane": "cpu (gh, read-only)",
    "staging": "memory-prefetch-metric",
    "base_revision": BASE,
    "head_revision": HEAD,
    "results": {
        "teknium1_open_prs": {
            "scanned_at": tek["scanned_at"], "count": tek["open_prs"], "count_check": "gh search total_count = 260",
            "files_scanned": tek["files_scanned"], "title_regex": tek["title_regex"], "file_regex": tek["file_regex"],
            "title_hits": tek["title_hits"], "file_hits": tek["file_hits"],
            "file_hit_detail": {"113678": "feat(cli): --disable-tools ... (head b94a482497): changes inject_memory_provider_tools (skips disabled tool names); does not touch _prefetch_provider"},
            "commands": tek["commands"],
            "correction": "STAGING.md v1 said teknium1 had 40 open PRs; there are 260, and v1's scan covered only the first 40 listed.",
        },
        "prefetch_search": {
            "searched_at": srch["searched_at"],
            "queries": {q: v["total_count"] for q, v in srch["queries"].items()},
            "open_prs_touching_prefetch_provider": {
                "124151": "kweez007: per-provider Hindsight timeout (adjacent, compatible; MERGE)",
                "87028": "richardclawbot: honor external prefetch timeout (adjacent; adds no record/metric lines)",
                "86948": "V0v1kkkAssistant: configurable provider timeouts (adjacent; adds no record/metric lines)",
                "92118": "seradin: structured prefetch observations side channel; its body says Hermes adds no persistence, outbound delivery or telemetry (adjacent; not a counter)",
            },
            "adds_prefetch_metric": [],
        },
    },
    "verdict": "OURS (no external owner); adjacent same-function PRs listed; risk: teknium1 may land the same row himself",
    "label": "OBSERVED",
    "not_tested": ["merge order against #87028, #86948 and #92118 (only #124151 was merged-tree tested)"],
    "provenance": "self",
    "privacy": "public-aggregate (public PR metadata only)",
    "raw_artifacts": {
        "teknium1_scan": {"path": rel(HERE / "ownership_teknium1_scan.json"), "sha256": sha(HERE / "ownership_teknium1_scan.json")},
        "prefetch_search": {"path": rel(HERE / "ownership_prefetch_search.json"), "sha256": sha(HERE / "ownership_prefetch_search.json")},
    },
})

# ---- E17 r03 (redaction + wording; no new measurement) ---------------------------------------------
e17 = json.loads((RECEIPTS / "E17-r20261001-02.json").read_text(encoding="utf-8"))
e17["id"] = "E17/r20261001-03"
e17["env"]["python"] = "3.11.14 (<read-only py3.11 venv>, used read-only as HERMES_PYTHON)"
e17["commands"] = [
    f"cd <scratch> && env -i PATH=/usr/bin:/bin {PY} work/e17_prefetch_fault_probe.py --repo <worktree at {V1_HEAD[:10]}> --base-mm work/base_memory_manager.py --out work/e17_result.json",
    f"cd <scratch> && env -i PATH=/usr/bin:/bin {PY} work/micro_gate_cost.py --repo <worktree at {V1_HEAD[:10]}> --out work/micro_gate_cost.json",
    f"cd <scratch> && env -i PATH=/usr/bin:/bin {PY} work/e17c_holographic_probe.py --repo <worktree at {V1_HEAD[:10]}> --out work/e17c_result.json",
]
e17["head_mapping"] = {
    "measured_at": V1_HEAD, "current_head": HEAD,
    "why_still_valid": "the rebased head carries byte-identical blobs for all 6 changed files and for every other file on the probe path (agent/memory_provider.py 90078f5e5e, agent/turn_context.py ac00c87229, base agent/memory_manager.py d023a57f8b); not re-run",
}
e17["interpretation"]["hot_path"] = (
    "NOT below per-call microbenchmark noise. Median head-minus-base delta per _prefetch_provider call: +47.05 us with collection off "
    "(p05..p95 +41.95..+56.71) and +158.76 us with it on (+140.40..+203.67). A/A base-minus-base over the same blocks: median -0.18 us, "
    "p05..p95 -8.34..+4.68 us off; median +3.95 us, p05..p95 -12.25..+33.55 us on. The standalone record_memory_prefetch call costs 26.69 us off "
    "(enabled() alone 16.65 us) and 112.95 us on, about the same as the existing record_execution_backend (32.80 / 114.43) and "
    "record_provider_memory_call (33.14 / 117.31) sites. That accounts for 26.7 of the 47 us off-delta; about 20 us is not attributed by this "
    "run (see E17d/r20261001-01). It runs once per turn per external provider, against turn waits of 0.3 ms (loopback) to 8 s (timeout)."
)
e17["verdict"] = "KEEP (mechanism); hot-path gate recorded as NOT MET as worded (owner decision)"
e17["supersedes"] = {
    "id": "E17/r20261001-02", "path": "receipts/E17-r20261001-02.json",
    "sha256_as_written": "e56f44b7bae8282e428e13b3eb6ef3890d96f5ba9273aacb052863fe810655e3",
    "why": "no new measurement: replaces local paths in commands/env with placeholders, states A/A as p05..p95 ranges (r02 said 'within about +/-8 us and +/-30 us', false at p95 with collection on), drops the unestablished claim that the per-call cost is the shared enabled() check, and maps the measurements onto the rebased head",
}
write("E17-r20261001-03.json", e17)
print("pre-existing receipt sha256:", json.dumps(old_sha, indent=1))
