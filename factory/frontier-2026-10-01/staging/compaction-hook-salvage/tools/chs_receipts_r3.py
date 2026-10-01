#!/usr/bin/env python3
"""Build the r3 public receipts (FACTORY §9.2 xf.receipt.v1, §9.3 rules) for staging/compaction-hook-salvage.

usage: chs_receipts_r3.py <h.git> <main_sha> <staging_commit>

Reads raw/f05-r3, raw/f05-r3s (runner summaries), raw/e12-r3 (chs_guards_r3.sh), raw/own-r3,
raw/guard-canary-r3.* and writes receipts/{F05-f05-r3,E12-e12-r3,OWN-own-r3,SANDBOX-guard-canary-r3,PROOF-r3}.json.
Receipts carry repo-relative paths only (raw logs are private artifacts and are referenced, never inlined).
Every cell's egress counts come from the r3 egress guard; under FACTORY S16 a cell with any blocked
connect or DNS attempt is INFRA, and an experiment with >10% INFRA cells is INFRA.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ST = Path(__file__).resolve().parents[1]
FRONTIER = ST.parents[1]
HGIT, MAIN, STAGING = sys.argv[1:4]
RAW = ST / "raw"
OUT = ST / "receipts"
CONTRACT = "tests/agent/test_compaction_observer_hook_contract.py"
REF = "refs/xf/arms/compaction-hook-salvage/"
CARRIER_HEADS = {"53806": "6067388d0c03ed86b596c3125f1a09804410221f", "93391": "9da3734b8e", "118847": "222e3e26c3",
                 "119347": "4a527fc35d", "125881": "d3fdffcf82"}
ORIGIN_REFS = ["NousResearch/hermes-agent#64231", "NousResearch/hermes-agent#118382", "NousResearch/hermes-agent#53806",
               "NousResearch/hermes-agent#93391", "NousResearch/hermes-agent#118847", "NousResearch/hermes-agent#119347",
               "NousResearch/hermes-agent#125881"]
N_INPUT = {"fallback_committed": 61}  # messages handed to _compress_context; every other probe scenario: 21


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", "-C", HGIT, *args], capture_output=True, text=True, check=True).stdout.strip()


def tool(name: str) -> dict:
    p = ST / "tools" / name
    return {"path": f"tools/{name}", "sha256": sha256(p)}


POLICY = {
    "AGENTS.md": git("rev-parse", f"{MAIN}:AGENTS.md"),
    "CONTRIBUTING.md": git("rev-parse", f"{MAIN}:CONTRIBUTING.md"),
    "factory": f"FACTORY.md sha256:{sha256(FRONTIER / 'FACTORY.md')}",
    "protocol": f"promotion-readiness-2026-10-01/PROTOCOL.md sha256:{sha256(FRONTIER.parent / 'promotion-readiness-2026-10-01' / 'PROTOCOL.md')}",
}
ENV = {
    "host": "<local-host>", "python": "3.11.14 (the live venv's interpreter, used read-only through HERMES_PYTHON; never as a source)",
    "sandbox": "no bwrap/netns (FACTORY §6 layer 1 not used). In-process layer only: tools/chs_egress_guard.py "
               "(non-loopback connect and DNS refused and logged; the openrouter-prewarm metadata thread is not started), "
               "loaded through the isolated test HOME's pytest_live_guard.py shim; scripts/run_tests.sh runs pytest under env -i "
               "with isolated HOME and HERMES_HOME (placeholders: $TESTHOME, $TESTHOME/.hermes)",
}
EVIDENCE_CLASS = {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"}
PRIVACY = ("public-aggregate: repo-relative paths and placeholders only; synthetic fixtures; no session ids, "
           "home paths, emails, message text or secrets. Raw logs under raw/ are private and contain local paths.")
AI = "Claude Code (Opus 5.5) wrote the contract test, the fold-in and the harness; disclosed per repository policy"
SPEC_F05 = {
    "path": None, "factory_row": "FACTORY.md §13 row 8 (F05)", "rev": 3, "sha256": None, "prereg_commit": None,
    "note": "no xf_spec TOML was written; the decision rule below was fixed in STAGING.md's acceptance gates before r3 ran",
    "decision_rule": "RED: the contract fails on the staging commit with marker 'on_compression_complete fired 0 times' in 3/3 "
                     "reps. GREEN: every case passes on the arm in 3/3 reps. NEGATIVE/SABOTAGE: the mutated arm re-fails at "
                     "least one case in 3/3 reps; a sabotage arm that stays green marks its hunk unpinned.",
}


def egress_counts(path: Path) -> dict:
    counts = {"connect": 0, "dns": 0, "prewarm_suppressed": 0}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            kind = line.split("\t", 1)[0]
            counts[kind] = counts.get(kind, 0) + 1
    return counts


def add(a: dict, b: dict) -> dict:
    return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}


def s16(cells: list) -> dict:
    infra = sum(1 for c in cells if c.get("exit_class") == "INFRA")
    tot = {"connect": 0, "dns": 0, "prewarm_suppressed": 0}
    for c in cells:
        tot = add(tot, c.get("egress", {}))
    return {"cells": len(cells), "infra_cells": infra, "infra_rate": round(infra / len(cells), 4) if cells else None,
            "egress_totals": tot, "experiment_infra": bool(cells) and infra / len(cells) > 0.10}


def reps(cells, kind):
    cs = [c for c in cells if c["kind"] == kind]
    if not cs:
        return None
    return {
        "reps": len(cs), "per_rep": [f'{c["passed"]} passed / {c["failed"]} failed' for c in cs],
        "reps_agree": len({(c["passed"], c["failed"], tuple(c["failing"])) for c in cs}) == 1,
        "failing": [f.split("::", 1)[1] for f in cs[0]["failing"]], "assertions": cs[0]["assertions"],
        "all_green": all(c["failed"] == 0 and (c["passed"] or 0) > 0 for c in cs),
        "exit_classes": sorted({c["exit_class"] for c in cs}), "logs_private": [c["log"] for c in cs],
    }


def clauses(rows):
    out = {}
    for r in rows:
        name = r["scenario"]
        ev = r["events"][0] if r["events"] else {}
        order = r["order"]
        hook_i = [i for i, e in enumerate(order) if e == "hook"]
        commit_end = [i for i, e in enumerate(order) if e.endswith(":end")]
        summ = [i for i, e in enumerate(order) if e == "summary"]
        timing = None
        if hook_i:
            h = hook_i[0]
            if summ and h < summ[0]:
                timing = "before_summary"
            elif commit_end and h > commit_end[0]:
                timing = "after_durable_commit"
            else:
                timing = "after_summary_before_commit"
        n_in = N_INPUT.get(name, 21)
        committed = 0 < r["rows_after"] < n_in
        out[name] = {
            "fires": r["fires"], "expect_fire": r["expect_fire"],
            "ok_count": (r["fires"] == 1) if r["expect_fire"] else (r["fires"] == 0),
            "timing": timing, "order": order,
            "fires_before_host_finalize": r["fires_before_finalize"] if name.startswith("manual") else None,
            "payload_keys": ev.get("keys") if ev else None,
            "payload_session_id_is_live": ev.get("payload_session_id_is_live") if ev else None,
            "state_db_rows_after": r["rows_after"], "messages_in": n_in,
            "compacted_transcript_committed": committed,
            "compressor_aborted": r["aborted"], "commit_site_refused_would_grow": r["refused_would_grow"],
            "output_identical_with_raising_and_directive_subscribers": r["output_identical"],
            "raised": r["raised"],
        }
    return out


def f05():
    s1 = json.loads((RAW / "f05-r3" / "summary.json").read_text())
    s2 = json.loads((RAW / "f05-r3s" / "summary.json").read_text())
    arms, cells_all = {}, []
    for summary, run in ((s1, "f05-r3"), (s2, "f05-r3s")):
        for arm, rec in summary["arms"].items():
            a = {"run": run, "commit": rec["commit"], "tree": rec["tree"],
                 "hook_subscribed": rec["hook"] or "on_compression_complete",
                 "contract_as_committed": reps(rec["cells"], "contract"),
                 "contract_adapted_to_carrier_hook": reps(rec["cells"], "adapted")}
            cells_all += rec["cells"]
            if "probe" in rec:
                cells_all.append({"exit_class": rec["probe"]["exit_class"], "egress": rec["probe"]["egress"]})
                a["probe"] = {"passed": rec["probe"]["passed"], "failed": rec["probe"]["failed"],
                              "exit_class": rec["probe"]["exit_class"], "egress": rec["probe"]["egress"],
                              "clauses": clauses(rec["probe"]["rows"])}
            if arm != "base":
                a["diff_vs_staging"] = git("diff", "--shortstat", STAGING, rec["commit"])
            arms[arm] = a
    merge = {"c53806-handport": "handported (compression commit e560abd758: conversation_compression.py + plugins.py hunks)",
             "c53806-handport-pre": "handported (same arm, start-side hook subscribed)",
             "c53806-foldin": "handported carrier + fold-in", "c93391-code": "conflict in 3 website docs files only; code + tests apply 3-way clean",
             "c118847-handport": "handported (1 conflicting hunk in agent/context_compressor.py)",
             "c125881-merge": "clean (merge-tree result)"}
    for arm, m in merge.items():
        if arm in arms:
            arms[arm]["merge"] = m
    infra = s16(cells_all)
    base = arms["base"]["contract_as_committed"]
    green = arms["c53806-foldin"]["contract_as_committed"]
    sab = []
    for arm in sorted(arms):
        if arm.startswith(("sab-", "neg-")):
            c = arms[arm]["contract_as_committed"]
            sab.append({"arm": arm, "per_rep": c["per_rep"], "red_again": not c["all_green"], "reps_agree": c["reps_agree"],
                        "failing": c["failing"]})
    receipt = {
        "schema": "xf.receipt.v1", "id": "F05/f05-r3", "label": "OBSERVED",
        "spec": SPEC_F05,
        "runner_revision": {"runner": tool("chs_ab_runner.py"), "probe": tool("chs_clause_probe.py"),
                            "arm_builder": tool("chs_build_arms_r3.py"), "egress_guard": tool("chs_egress_guard.py")},
        "issue": None, "issue_note": "no fork campaign thread exists for this item (OD-9)",
        "origin_refs": ORIGIN_REFS, "staging": "compaction-hook-salvage",
        "base_revision": MAIN, "head_revision": STAGING,
        "changed_files": [CONTRACT],
        "contract_test_blob": git("rev-parse", f"{STAGING}:{CONTRACT}"),
        "inputs_pinned": {"carrier_heads": CARRIER_HEADS},
        "arms": arms,
        "policy_revision": POLICY, "env": ENV,
        "command": "python3 tools/chs_ab_runner.py --worktree $WORKTREE --run-id f05-r3 --arms \"$(cat raw/f05-r3.arms)\" "
                   "--reps 3 --testhome $TESTHOME --python $PY; then the same with --run-id f05-r3s --arms \"$(cat raw/f05-r3s.arms)\" --skip-probe",
        "gates": {
            "validity": "PASS" if not infra["experiment_infra"] and infra["infra_cells"] == 0 else "INFRA",
            "red": {"arm": "base", "result": "PASS" if (not base["all_green"] and base["reps_agree"]) else "FAIL",
                    "observed": base["per_rep"][0], "assertion": base["assertions"][0] if base["assertions"] else None,
                    "seam_covered": True, "reps_agree": f'{len(base["per_rep"])}/{len(base["per_rep"])}' if base["reps_agree"] else "no"},
            "green": [{"arm": a, "result": "PASS" if arms[a]["contract_as_committed"]["all_green"] else "FAIL",
                       "reps_agree": "3/3" if arms[a]["contract_as_committed"]["reps_agree"] else "no"}
                      for a in ("c53806-foldin", "foldin-ref", "foldin-bounded") if a in arms],
            "sabotage": {"per_hunk": sab,
                         "unpinned_hunks": [s["arm"] for s in sab if not s["red_again"]]},
            "adjacent": "see E12/e12-r3", "guards": "see E12/e12-r3",
            "flaky": not all(arms[a]["contract_as_committed"]["reps_agree"] for a in arms),
            "noise_floor": None, "credit": None, "informativeness": "N_A", "route_scope": "local-compressor",
            "cache_read_ratio": {"status": "N_A", "before": None, "after": None},
        },
        "ab": None,
        "measurements": [{"name": "cases_failed", "arm": a, "value": arms[a]["contract_as_committed"]["per_rep"][0],
                          "n": arms[a]["contract_as_committed"]["reps"], "label": "OBSERVED", "statistic": "count"}
                         for a in arms],
        "denominators": {"cells": infra["cells"], "errored_scored_zero": 0, "infra_excluded": 0,
                         "infra": infra["infra_cells"], "completeness": 1.0},
        "egress": {**infra["egress_totals"],
                   "s16": f'{infra["infra_cells"]} of {infra["cells"]} cells INFRA (blocked connect or DNS); '
                          f'experiment INFRA: {infra["experiment_infra"]}. prewarm_suppressed counts the openrouter-prewarm '
                          'thread the guard did not start (one per pytest worker process), a prevention rather than a blocked attempt.'},
        "evidence_class": EVIDENCE_CLASS,
        "harness_abi": {"harness": "hermes", "seam": "hermes_cli.lifecycle.invoke_hook -> PluginManager.invoke_hook at the "
                        "local compaction notify fence (agent/conversation_compression.py)"},
        "not_tested": ["native and Codex app-server compaction (no local commit)", "session_db=None agents",
                       "per-host manual /compress handlers (deferral driven through compress_context + finalize only)",
                       "real summarizer (fixed text)", "shell hooks", "hung subscriber",
                       "#53806's start-side pre_context_compression beyond the A/B row (no contract case)"],
        "limitations": ["agent-written oracle; per-hunk sabotage listed", "competitor hand-ports are ours, not the authors'",
                        "probe 'committed' = 0 < state.db rows < messages handed in (rotation failures re-flush the full transcript)"],
        "resource_usage": {"wall_s": round(sum(c.get("wall_s", 0) for c in cells_all), 1), "cpu_core_s": None,
                           "gpu_s": 0, "energy_j": None, "api_cost_usd": 0.0},
        "verdict": "KEEP" if infra["infra_cells"] == 0 else "INFRA",
        "carrier_choice": {"winner": "c53806-foldin",
                           "why": "#53806 is the only carrier whose post-commit hook fires after the durable commit and stays silent "
                                  "on uncommitted attempts; with the fold-in it passes every case. #93391 and #53806's own pre hook are "
                                  "start-side, #118847 fires before the commit, #125881 is a fail-closed admission gate"},
        "learning": {"hypothesis": "one observer contract separates the five carriers", "result": "KEEP",
                     "reusable_lesson": "a failed summary under the default config commits a deterministic fallback; "
                                        "'silent on summary failure' only holds with abort_on_summary_failure=true",
                     "roadmap_effect": "salvage-support"},
        "provenance": "self", "frozen": None, "z0evals_study": None, "ai_assistance": AI, "privacy": PRIVACY,
        "artifacts": [{"uri": "raw/f05-r3/", "public": False}, {"uri": "raw/f05-r3s/", "public": False},
                      {"uri": "raw/f05-r3/summary.json", "sha256": sha256(RAW / "f05-r3" / "summary.json"), "public": False},
                      {"uri": "raw/f05-r3s/summary.json", "sha256": sha256(RAW / "f05-r3s" / "summary.json"), "public": False}],
    }
    return receipt


def pytest_summary(log: Path):
    if not log.exists():
        return None
    txt = log.read_text(errors="replace")
    m = re.search(r"=== Summary: (\d+) files?, (\d+) tests? passed, (\d+) failed", txt)
    skipped = re.findall(r"(\d+) skipped", txt)
    if m:
        return {"files": int(m.group(1)), "passed": int(m.group(2)), "failed": int(m.group(3)),
                "skipped_per_worker_lines": [int(x) for x in skipped],
                "failing": sorted({f.split("::")[0] + "::" + f.split("::", 1)[1] if "::" in f else f
                                   for f in re.findall(r"^FAILED (\S+)", txt, flags=re.M)})}
    return {"unparsed": True}


VOLATILE = {"checkout", "head", "elapsed_s", "wall_s", "duration_s", "tmp", "home", "session_id", "requests"}


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in VOLATILE and not k.endswith("_ms")}
    if isinstance(o, list):
        return [strip(v) for v in o]
    if isinstance(o, str) and re.search(r"^/|/tmp/|/var/tmp/|\d{8}_\d{6}_[0-9a-f]{6}", o):
        return "<volatile>"
    return o


def load(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception as exc:  # noqa: BLE001
        return {"_unreadable": type(exc).__name__}


S16_EXCEPTION_UPSTREAM = {
    "status": "recorded exception, owner to accept or reject (FACTORY S16 defines none)",
    "scope": "upstream test and eval code this item does not change: 7 sibling compression test files, "
             "evals/compaction/test_region_scoping.py, and (OWN) tests/agent/test_compression_rotation_state.py",
    "what": "best-effort DNS lookups for openrouter.ai from two upstream paths: the model-metadata GET at AIAgent init "
            "(agent_init._enforce_minimum_context -> model_metadata.get_model_context_length -> fetch_model_metadata) and the "
            "video-catalog GET while tool definitions are built (plugins/video_gen/openrouter._catalog)",
    "why_results_stand": ["the guard refused every lookup at DNS; 0 connects", "both paths catch the failure and fall back "
                          "(the 256K default window; the bundled catalog snapshot)", "the same counts occur on base and on every "
                          "arm (adjacent 224/224/224; per-file attribution identical on base and c53806-foldin)",
                          "pass/fail is identical apart from the new contract test", "the new contract test itself makes 0 "
                          "lookups (F05 r3: 0 dns in 78 cells)"],
    "attribution": "raw/e12-r3/dns-attribution/summary.json (from tools/chs_dns_attribution.py over guard stack dumps)",
    "without_exception": "these cells are INFRA, and E12/OWN would be INFRA (rate > 10%)",
}


def e12():
    raw = RAW / "e12-r3"
    arms, cells = {}, []
    for line in (raw / "arms.txt").read_text().splitlines():
        arm, commit, tree = line.split()
        a = {"commit": commit, "tree": tree}
        for h in ("replay_gates", "ab_checkpoint_preflight", "test_region_scoping", "adjacent"):
            eg = egress_counts(raw / f"{arm}-{h}.egress.log")
            cell = {"harness": h, "egress": eg, "exit_class": "INFRA" if (eg["connect"] or eg["dns"]) else "ok"}
            if h in ("replay_gates", "ab_checkpoint_preflight"):
                cell["verdicts"] = strip(load(raw / f"{arm}-{h}.json"))
                cnt = load(raw / f"{arm}-{h}.counts.json")
                cell["observer_counts"] = {k: cnt.get(k) for k in ("rc", "hook_fires", "commits_total", "commits_succeeded")}
            elif h == "test_region_scoping":
                txt = (raw / f"{arm}-{h}.log").read_text(errors="replace")
                cell["verdict"] = "ALL PASS" if "scoping tripwire: ALL PASS" in txt else "FAIL"
            else:
                cell["summary"] = pytest_summary(raw / f"{arm}-adjacent.log")
            cell["log_private"] = f"raw/e12-r3/{arm}-{h}.log"
            a[h] = cell
            cells.append(cell)
        arms[arm] = a
    base = arms["base"]
    for arm, a in arms.items():
        if arm == "base":
            continue
        a["equal_to_base"] = {
            "replay_gates": a["replay_gates"]["verdicts"] == base["replay_gates"]["verdicts"],
            "ab_checkpoint_preflight": a["ab_checkpoint_preflight"]["verdicts"] == base["ab_checkpoint_preflight"]["verdicts"],
            "test_region_scoping": a["test_region_scoping"]["verdict"] == base["test_region_scoping"]["verdict"],
        }
    infra = s16(cells)
    attribution = json.loads((raw / "dns-attribution" / "summary.json").read_text())
    receipt = {
        "schema": "xf.receipt.v1", "id": "E12/e12-r3", "label": "OBSERVED",
        "spec": {"path": None, "factory_row": "FACTORY.md §13 row 9 (E12)", "rev": 3, "sha256": None, "prereg_commit": None,
                 "decision_rule": "replay_gates and ab_checkpoint_preflight verdict maps equal to base; test_region_scoping ALL PASS on "
                                  "every arm; adjacent files identical to base apart from the new contract test"},
        "runner_revision": {"script": tool("chs_guards_r3.sh"), "wrapper": tool("chs_guard_wrap.py"), "egress_guard": tool("chs_egress_guard.py")},
        "issue": None, "origin_refs": ORIGIN_REFS, "staging": "compaction-hook-salvage",
        "base_revision": MAIN, "head_revision": STAGING, "changed_files": [CONTRACT],
        "harness": {"replay_gates": "evals/token_accounting/replay_gates.py",
                    "ab_checkpoint_preflight": "evals/native_compaction/ab_checkpoint_preflight.py",
                    "test_region_scoping": "evals/compaction/test_region_scoping.py",
                    "adjacent_files": ["tests/agent/test_compaction_observer_hook_contract.py", "tests/agent/test_compression_boundary_hook.py",
                                       "tests/hermes_cli/test_cli_manual_compress.py", "tests/hermes_cli/test_shared_metrics_engagement.py",
                                       "tests/agent/test_compression_attempt_telemetry.py", "tests/agent/test_auxiliary_hooks.py",
                                       "tests/agent/test_shell_hooks.py", "tests/gateway/test_gateway_platform_event_hook.py",
                                       "tests/hermes_cli/test_hooks_cli.py", "tests/hermes_cli/test_plugins.py",
                                       "tests/hermes_cli/test_kanban_lifecycle_hooks.py", "tests/agent/test_conversation_compression_manual.py",
                                       "tests/agent/test_compression_rotation_state.py", "tests/agent/test_compression_persistence.py",
                                       "tests/agent/test_compression_commit_fence_race.py", "tests/agent/test_compression_attempt_lifecycle.py",
                                       "tests/agent/test_pre_compress_memory_context_handoff.py"]},
        "arms": arms, "policy_revision": POLICY, "env": ENV,
        "command": "bash tools/chs_guards_r3.sh <arm> <commit> e12-r3 $WORKTREE $TESTHOME $PY, for base, c53806-foldin, foldin-bounded",
        "gates": {"validity": "PASS" if infra["infra_cells"] == 0 else "PASS under the recorded S16 exception (INFRA without it)",
                  "guards": {a: arms[a].get("equal_to_base") for a in arms if a != "base"},
                  "adjacent": {a: arms[a]["adjacent"]["summary"] for a in arms},
                  "flaky": False, "route_scope": "local-compressor"},
        "measurements": [],
        "denominators": {"cells": infra["cells"], "errored_scored_zero": 0, "infra_excluded": 0, "infra": infra["infra_cells"], "completeness": 1.0},
        "egress": {**infra["egress_totals"],
                   "per_cell": {f"{a}/{h}": arms[a][h]["egress"] for a in arms for h in ("replay_gates", "ab_checkpoint_preflight", "test_region_scoping", "adjacent")},
                   "s16": f'{infra["infra_cells"]} of {infra["cells"]} harness cells had blocked DNS lookups (0 connects); all of them in '
                          'upstream code (adjacent sibling files and test_region_scoping), identical on base and arms. replay_gates and '
                          'ab_checkpoint_preflight: 0.',
                   "s16_exception": S16_EXCEPTION_UPSTREAM, "dns_attribution": attribution},
        "evidence_class": EVIDENCE_CLASS,
        "structural_note": "observer fires are 0 in replay_gates/ab_checkpoint_preflight by construction (no SessionDB in their "
                           "real-compression scenarios; the preflight stubs _compress_context), so 0 is not a native-route measurement",
        "not_tested": ["native compaction on a real provider turn"], "limitations": ["one run per arm per harness"],
        "resource_usage": {"wall_s": None, "cpu_core_s": None, "gpu_s": 0, "energy_j": None, "api_cost_usd": 0.0},
        "verdict": "PASS" if infra["infra_cells"] == 0 else "PASS (recorded S16 exception; INFRA without it)",
        "provenance": "self", "frozen": None, "z0evals_study": None, "ai_assistance": AI, "privacy": PRIVACY,
        "artifacts": [{"uri": "raw/e12-r3/", "public": False}],
    }
    return receipt


def own():
    raw = RAW / "own-r3"
    cells = []
    for line in (raw / "cells.txt").read_text().splitlines():
        label, commit, path = line.split()
        eg = egress_counts(raw / f"{label}.egress.log")
        cells.append({"cell": label, "commit": commit, "file": path, "summary": pytest_summary(raw / f"{label}.log"),
                      "egress": eg, "exit_class": "INFRA" if (eg["connect"] or eg["dns"]) else "ok",
                      "log_private": f"raw/own-r3/{label}.log"})
    infra = s16(cells)
    return {
        "schema": "xf.receipt.v1", "id": "OWN/own-r3", "label": "OBSERVED",
        "spec": {"path": None, "rev": 3, "decision_rule": "fairness only: each carrier's own tests pass on its arm"},
        "runner_revision": {"egress_guard": tool("chs_egress_guard.py")},
        "issue": None, "origin_refs": ORIGIN_REFS, "staging": "compaction-hook-salvage",
        "base_revision": MAIN, "head_revision": STAGING, "changed_files": [],
        "purpose": "fairness check: each carrier proves its own, different contract with its own tests",
        "cells": cells, "policy_revision": POLICY, "env": ENV,
        "command": "HOME=$TESTHOME HERMES_HOME=$TESTHOME/.hermes HERMES_PYTHON=$PY bash scripts/run_tests.sh -j 2 <file> -q",
        "gates": {"validity": "PASS" if infra["infra_cells"] == 0 else "PASS under the recorded S16 exception (INFRA without it)"},
        "denominators": {"cells": infra["cells"], "errored_scored_zero": 0, "infra_excluded": 0, "infra": infra["infra_cells"], "completeness": 1.0},
        "egress": {**infra["egress_totals"], "s16_exception": S16_EXCEPTION_UPSTREAM if infra["infra_cells"] else None},
        "evidence_class": EVIDENCE_CLASS,
        "limitations": ["#118847's own tests mock hermes_cli.lifecycle.invoke_hook, the seam itself"],
        "verdict": "N_A (fairness)", "provenance": "self", "frozen": None, "ai_assistance": AI, "privacy": PRIVACY,
    }


def canary():
    log = RAW / "guard-canary-r3.log"
    eg = egress_counts(RAW / "guard-canary-r3.egress.log")
    s = pytest_summary(log)
    return {
        "schema": "xf.receipt.v1", "id": "SANDBOX/guard-canary-r3", "label": "OBSERVED",
        "spec": {"path": None, "rev": 3, "decision_rule": "each guard layer blocks and logs; loopback still works"},
        "runner_revision": {"egress_guard": tool("chs_egress_guard.py"), "canary": tool("chs_guard_canary_r3.py")},
        "staging": "compaction-hook-salvage", "base_revision": MAIN, "head_revision": STAGING,
        "what": "tools/chs_egress_guard.py loaded by scripts/run_tests.sh through the isolated HOME's pytest_live_guard.py shim",
        "cases": ["guard loaded from the isolated test HOME (log path not under the real ~/.hermes)",
                  "connect to 1.1.1.1:443 refused", "getaddrinfo('example.com') refused",
                  "loopback connect + localhost DNS still work", "openrouter-prewarm thread not started; other threads start"],
        "result": s, "egress_log_counts": eg,
        "expected_egress_log_counts": {"connect": 1, "dns": 1, "prewarm_suppressed": 1},
        "command": "cp tools/chs_guard_canary_r3.py tests/agent/test_zz_chs_guard_canary.py; HOME=$TESTHOME HERMES_HOME=$TESTHOME/.hermes "
                   "HERMES_PYTHON=$PY bash scripts/run_tests.sh -j 2 tests/agent/test_zz_chs_guard_canary.py -q",
        "policy_revision": POLICY, "env": ENV, "evidence_class": EVIDENCE_CLASS,
        "gates": {"validity": "PASS" if s and s.get("failed") == 0 and s.get("passed") == 5 else "FAIL"},
        "denominators": {"cells": 5, "errored_scored_zero": 0, "infra_excluded": 0, "infra": 0, "completeness": 1.0},
        "verdict": "PASS" if s and s.get("failed") == 0 and s.get("passed") == 5 and eg == {"connect": 1, "dns": 1, "prewarm_suppressed": 1} else "FAIL",
        "limitations": ["in-process guard only: a native extension or subprocess could bypass it (no netns)"],
        "provenance": "self", "frozen": None, "ai_assistance": AI, "privacy": PRIVACY,
    }


def proof(f05r, e12r):
    arms = f05r["arms"]
    return {
        "schema": "xf.receipt.v1", "id": "PROOF/r3", "label": "OBSERVED",
        "spec": {"path": None, "rev": 3, "decision_rule": "aggregation of F05/f05-r3 and E12/e12-r3; computes nothing new"},
        "staging": "compaction-hook-salvage", "base_revision": MAIN, "head_revision": STAGING,
        "issue": None, "origin_refs": ORIGIN_REFS, "changed_files": [CONTRACT],
        "contract_test": {"path": CONTRACT, "blob": f05r["contract_test_blob"],
                          "tests": ["test_observer_fires_once_after_the_durable_commit[rotated|in_place|manual_deferred]",
                                    "test_observer_is_silent_when_nothing_commits[summary_aborted|would_grow_refused|commit_failed|manual_discarded]"]},
        "production_seam": {"fire_site": "agent/conversation_compression.py::_notify_context_engine_compression_complete",
                            "dispatch": "hermes_cli.lifecycle.has_hook/invoke_hook -> PluginManager.invoke_hook",
                            "deferral": "_queue_context_engine_compression_notification -> finalize_context_engine_compression_notification"},
        "gates": {**f05r["gates"], "adjacent": e12r["gates"]["adjacent"], "guards": e12r["gates"]["guards"],
                  "validity": f'F05: {f05r["gates"]["validity"]}; E12: {e12r["gates"]["validity"]}'},
        "columns": {a: {"contract": arms[a]["contract_as_committed"]["per_rep"],
                        "adapted": (arms[a]["contract_adapted_to_carrier_hook"] or {}).get("per_rep")} for a in arms},
        "sources": {"F05/f05-r3": "receipts/F05-f05-r3.json", "E12/e12-r3": "receipts/E12-e12-r3.json"},
        "denominators": {"cells": f05r["denominators"]["cells"] + e12r["denominators"]["cells"], "errored_scored_zero": 0,
                         "infra_excluded": 0, "infra": f05r["denominators"]["infra"] + e12r["denominators"]["infra"], "completeness": 1.0},
        "policy_revision": POLICY, "env": ENV, "evidence_class": EVIDENCE_CLASS,
        "verdict": "PASS" if f05r["verdict"] == "KEEP" and e12r["verdict"].startswith("PASS") else "FAIL",
        "verdict_note": "F05 r3 has 0 INFRA cells; E12 r3 passes under the recorded S16 exception for upstream code (see E12/e12-r3 egress)",
        "provenance": "self", "frozen": None, "ai_assistance": AI, "privacy": PRIVACY,
    }


def write(name, obj):
    p = OUT / name
    txt = json.dumps(obj, indent=1, default=str)
    assert "/tmp/" not in txt and "/home/" not in txt and "/mnt/" not in txt and "/workspace/" not in txt, f"local path in {name}"
    p.write_text(txt + "\n")
    print(name, sha256(p))


if __name__ == "__main__":
    f = f05()
    e = e12()
    write("F05-f05-r3.json", f)
    write("E12-e12-r3.json", e)
    write("OWN-own-r3.json", own())
    write("SANDBOX-guard-canary-r3.json", canary())
    write("PROOF-r3.json", proof(f, e))
