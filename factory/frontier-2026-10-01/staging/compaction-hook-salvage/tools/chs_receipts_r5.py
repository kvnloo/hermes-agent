#!/usr/bin/env python3
"""Build the r5 public receipts (FACTORY §9.2 xf.receipt.v1, §9.3 rules) for staging/compaction-hook-salvage.

usage: chs_receipts_r5.py <h.git> <main_sha> <staging_commit>

Reads raw/f05-r5, raw/f05-r5s (runner summaries), raw/e12-r5 (chs_guards_r5.sh), raw/own-r5 (chs_own_r5.sh),
raw/mrg-r5 (chs_merge127058_r5.sh) and raw/prewarm-r4/ (the r4 prewarm check, cited) and writes
receipts/{F05-f05-r5,E12-e12-r5,OWN-own-r5,MRG-mrg-r5,PROOF-r5}.json. The egress guard is the r4 guard, unchanged
(same sha256 as in SANDBOX/guard-canary-r4), so no new canary was run. Receipts name no host.
Receipts carry repo-relative paths only (raw logs are private artifacts and are referenced, never inlined).
Every cell's egress counts come from the r4 egress guard, which blocks non-loopback connect and DNS and
suppresses nothing (r3 also refused to start the openrouter-prewarm thread, which hid one lookup per pytest
worker). Under FACTORY S16 a cell with any blocked connect or DNS attempt is INFRA, and an experiment with
>10% INFRA cells is INFRA. No S16 exception is applied here: cells that need one are reported INFRA, with
the verdict they would have if the owner accepts the recorded exception alongside.
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
sys.path.insert(0, str(ST / "tools"))
HGIT, MAIN, STAGING = sys.argv[1:4]
RAW = ST / "raw"
OUT = ST / "receipts"
CONTRACT = "tests/agent/test_compaction_observer_hook_contract.py"
REF = "refs/xf/arms/compaction-hook-salvage/"
CARRIER_HEADS = {"53806": "6067388d0c03ed86b596c3125f1a09804410221f", "93391": "9da3734b8e", "118847": "222e3e26c3",
                 "119347": "4a527fc35d", "125881": "d3fdffcf82", "4123": "16c60cd623", "7150": "f823aebeb2",
                 "127058": "f306319fe7d7d349f329a496be10afa9650943cc"}
ORIGIN_REFS = ["NousResearch/hermes-agent#64231", "NousResearch/hermes-agent#118382", "NousResearch/hermes-agent#53806",
               "NousResearch/hermes-agent#93391", "NousResearch/hermes-agent#118847", "NousResearch/hermes-agent#119347",
               "NousResearch/hermes-agent#125881", "NousResearch/hermes-agent#4123", "NousResearch/hermes-agent#7150",
               "NousResearch/hermes-agent#118120", "NousResearch/hermes-agent#127058"]
N_INPUT = {"fallback_committed": 61}  # messages handed to _compress_context; every other probe scenario: 21


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args, check_ok=False) -> str:
    p = subprocess.run(["git", "-C", HGIT, *args], capture_output=True, text=True, check=not check_ok)
    return p.stdout.strip()


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
    "host": "withheld (one local workstation; receipts name no host)", "python": "3.11.14 (the live venv's interpreter, used read-only through HERMES_PYTHON; never as a source)",
    "sandbox": "no bwrap/netns (FACTORY §6 layer 1 not used). In-process layer only: tools/chs_egress_guard_r4.py "
               "(non-loopback connect and DNS refused and logged with the calling thread's name; nothing suppressed, so the "
               "openrouter-prewarm thread starts and any lookup it makes is counted), loaded through the isolated test HOME's "
               "pytest_live_guard.py shim; scripts/run_tests.sh runs pytest under env -i with isolated HOME and HERMES_HOME "
               "(placeholders: $TESTHOME, $TESTHOME/.hermes)",
}
EVIDENCE_CLASS = {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"}
PRIVACY = ("public-aggregate: repo-relative paths and placeholders only; synthetic fixtures; no session ids, "
           "home paths, emails, message text or secrets. Raw logs under raw/ are private and contain local paths.")
AI = ("Claude Code (Opus 5.5) wrote the contract test, the fold-in (including the sibling module), the harness and these "
      "receipts; disclosed per repository policy")
SPEC_F05 = {
    "path": None, "factory_row": "FACTORY.md §13 row 8 (F05)", "rev": 5, "sha256": None, "prereg_commit": None,
    "note": "no xf_spec TOML was written; the decision rule below was fixed in STAGING.md's acceptance gates before r1 ran "
            "and is unchanged in r5 (r5 adds the fence/lease assertions to the fires-once case)",
    "decision_rule": "RED: the contract fails on the staging commit with marker 'on_compression_complete fired 0 times' in 3/3 "
                     "reps. GREEN: every case passes on the arm in 3/3 reps. NEGATIVE/SABOTAGE: the mutated arm re-fails at "
                     "least one case in 3/3 reps; a sabotage arm that stays green marks its hunk unpinned.",
}


def egress_counts(path: Path) -> dict:
    counts = {"connect": 0, "dns": 0, "by_thread": {}}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            kind = parts[0]
            counts[kind] = counts.get(kind, 0) + 1
            thread = next((p[7:] for p in parts[1:] if p.startswith("thread=")), "?")
            key = f"{kind}:{thread}"
            counts["by_thread"][key] = counts["by_thread"].get(key, 0) + 1
    return counts


def runner_egress(eg: dict) -> dict:
    """Runner summaries carry {connect, dns, prewarm_suppressed, detail?}; normalise to the receipt shape."""
    out = {"connect": eg.get("connect", 0), "dns": eg.get("dns", 0), "by_thread": {}}
    for key, n in (eg.get("detail") or {}).items():
        kind = key.split(":", 1)[0]
        thread = key.rsplit(":", 1)[-1]
        out["by_thread"][f"{kind}:{thread}"] = out["by_thread"].get(f"{kind}:{thread}", 0) + n
    assert not eg.get("prewarm_suppressed"), "the r4 guard (used in r5) must not suppress anything"
    return out


def add(a: dict, b: dict) -> dict:
    out = {"connect": a.get("connect", 0) + b.get("connect", 0), "dns": a.get("dns", 0) + b.get("dns", 0), "by_thread": {}}
    for d in (a.get("by_thread", {}), b.get("by_thread", {})):
        for k, v in d.items():
            out["by_thread"][k] = out["by_thread"].get(k, 0) + v
    return out


def s16(cells: list) -> dict:
    infra = sum(1 for c in cells if c.get("exit_class") == "INFRA")
    tot = {"connect": 0, "dns": 0, "by_thread": {}}
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
            "payload_tokens_before": ev.get("tokens_before") if ev else None,
            "payload_tokens_after": ev.get("tokens_after") if ev else None,
            "commit_fence_in_flight_at_fire": ev.get("fence_in_flight") if ev else None,
            "lease_held_at_fire": (ev.get("lease_holder_old_sid") is not None) if ev else None,
            "state_db_rows_after": r["rows_after"], "messages_in": n_in,
            "compacted_transcript_committed": committed,
            "compressor_aborted": r["aborted"], "commit_site_refused_would_grow": r["refused_would_grow"],
            "output_identical_with_raising_and_directive_subscribers": r["output_identical"],
            "raised": r["raised"],
        }
    return out


def f05():
    s1 = json.loads((RAW / "f05-r5" / "summary.json").read_text())
    s2 = json.loads((RAW / "f05-r5s" / "summary.json").read_text())
    arms, cells_all = {}, []
    for summary, run in ((s1, "f05-r5"), (s2, "f05-r5s")):
        for arm, rec in summary["arms"].items():
            for c in rec["cells"]:
                c["egress"] = runner_egress(c["egress"])
            a = {"run": run, "commit": rec["commit"], "tree": rec["tree"],
                 "hook_subscribed": rec["hook"] or "on_compression_complete",
                 "contract_as_committed": reps(rec["cells"], "contract"),
                 "contract_adapted_to_carrier_hook": reps(rec["cells"], "adapted")}
            cells_all += rec["cells"]
            if "probe" in rec:
                peg = runner_egress(rec["probe"]["egress"])
                cells_all.append({"exit_class": rec["probe"]["exit_class"], "egress": peg})
                a["probe"] = {"passed": rec["probe"]["passed"], "failed": rec["probe"]["failed"],
                              "exit_class": rec["probe"]["exit_class"], "egress": peg,
                              "clauses": clauses(rec["probe"]["rows"])}
            if arm != "base":
                a["diff_vs_staging"] = git("diff", "--shortstat", STAGING, rec["commit"])
            arms[arm] = a
    merge = {"c53806-handport": "handported (compression commit e560abd758: conversation_compression.py + plugins.py hunks; "
                                "the pre_context_compression call sits in _run_summary_phase, where main moved the summarizer "
                                "call, and task_id is passed in so its payload is the carrier's)",
             "c53806-handport-pre": "handported (same arm, start-side hook subscribed)",
             "foldin": "handported carrier start-side hook + fold-in (sibling module, post-fence delivery, bounded)",
             "foldin-ref": "fold-in without the carrier's start-side hook",
             "r4-offer": "the round-2 combined diff (observer inside the commit fence), re-applied 3-way clean",
             "foldin-x127058": "fold-in merged with #127058 head f306319fe7; 1 conflict (both deliveries appended after "
                               "finish_commit), resolved by keeping both",
             "c93391-code": "conflict in 3 website docs files only; code + tests apply 3-way clean",
             "c118847-handport": "handported (1 conflicting hunk in agent/context_compressor.py)",
             "c125881-merge": "clean (merge-tree result)"}
    for arm, m in merge.items():
        if arm in arms:
            arms[arm]["merge"] = m
    infra = s16(cells_all)
    base = arms["base"]["contract_as_committed"]
    sab = []
    for arm in sorted(arms):
        if arm.startswith(("sab-", "neg-")):
            c = arms[arm]["contract_as_committed"]
            sab.append({"arm": arm, "per_rep": c["per_rep"], "red_again": not c["all_green"], "reps_agree": c["reps_agree"],
                        "failing": c["failing"]})
    fb = arms["foldin"]["probe"]["clauses"]["fallback_committed"]
    receipt = {
        "schema": "xf.receipt.v1", "id": "F05/f05-r5", "label": "OBSERVED",
        "spec": SPEC_F05,
        "runner_revision": {"runner": tool("chs_ab_runner_r5.py"), "probe": tool("chs_clause_probe_r5.py"),
                            "arm_builder": tool("chs_build_arms_r5.py"), "egress_guard": tool("chs_egress_guard_r4.py"),
                            "chain": tool("chs_run_all_r5.sh")},
        "issue": None, "issue_note": "no fork campaign thread exists for this item (OD-9)",
        "origin_refs": ORIGIN_REFS, "staging": "compaction-hook-salvage",
        "base_revision": MAIN, "head_revision": STAGING,
        "changed_files": [CONTRACT],
        "contract_test_blob": git("rev-parse", f"{STAGING}:{CONTRACT}"),
        "inputs_pinned": {"carrier_heads": CARRIER_HEADS},
        "arms": arms,
        "fallback_commit_probe": {
            "arm": "foldin", "scenario": "fallback_committed",
            "setup": "default compression.abort_on_summary_failure=false, summary call returns None, 61 messages in "
                     "(30 user/assistant pairs of ~600 words + system)",
            "fires": fb["fires"], "timing": fb["timing"], "tokens_before": fb["payload_tokens_before"],
            "tokens_after": fb["payload_tokens_after"], "state_db_rows_after": fb["state_db_rows_after"],
            "compressor_aborted": fb["compressor_aborted"], "commit_site_refused_would_grow": fb["commit_site_refused_would_grow"],
            "note": "probe-only; not a case in the committed contract test",
        },
        "policy_revision": POLICY, "env": ENV,
        "command": "python3 tools/chs_ab_runner_r5.py --worktree $WORKTREE --run-id f05-r5 --arms \"$(cat raw/f05-r5.arms)\" "
                   "--reps 3 --testhome $TESTHOME --python $PY; then the same with --run-id f05-r5s --arms \"$(cat raw/f05-r5s.arms)\" "
                   "--skip-probe (both inside tools/chs_run_all_r5.sh)",
        "gates": {
            "validity": "PASS" if not infra["experiment_infra"] and infra["infra_cells"] == 0 else "INFRA",
            "red": {"arm": "base", "result": "PASS" if (not base["all_green"] and base["reps_agree"]) else "FAIL",
                    "observed": base["per_rep"][0], "assertion": base["assertions"][0] if base["assertions"] else None,
                    "seam_covered": True, "reps_agree": f'{len(base["per_rep"])}/{len(base["per_rep"])}' if base["reps_agree"] else "no"},
            "green": [{"arm": a, "result": "PASS" if arms[a]["contract_as_committed"]["all_green"] else "FAIL",
                       "reps_agree": "3/3" if arms[a]["contract_as_committed"]["reps_agree"] else "no"}
                      for a in ("foldin", "foldin-ref", "foldin-x127058") if a in arms],
            "previous_offer": {"arm": "r4-offer", "per_rep": arms["r4-offer"]["contract_as_committed"]["per_rep"],
                               "failing": arms["r4-offer"]["contract_as_committed"]["failing"],
                               "assertions": arms["r4-offer"]["contract_as_committed"]["assertions"],
                               "reading": "the round-2 offer ran the observer inside the commit fence with the lease held"},
            "sabotage": {"per_hunk": sab,
                         "unpinned_hunks": [s["arm"] for s in sab if not s["red_again"]]},
            "adjacent": "see E12/e12-r5", "guards": "see E12/e12-r5",
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
                   "s16": f'{infra["infra_cells"]} of {infra["cells"]} cells INFRA (blocked connect or DNS, from any thread); '
                          f'experiment INFRA: {infra["experiment_infra"]}. The r4 guard (unchanged, used for r5) suppresses nothing: the contract test and '
                          'the probe stub agent init\'s model-metadata lookups themselves (pinned context window; '
                          'agent.agent_init.fetch_model_metadata stubbed, so the openrouter-prewarm thread runs the stub).'},
        "evidence_class": EVIDENCE_CLASS,
        "harness_abi": {"harness": "hermes", "seam": "hermes_cli.lifecycle.has_hook/invoke_hook -> PluginManager.invoke_hook, "
                        "called from agent/conversation_compression_observer.py; staged in compress_context after "
                        "_finish_compaction_boundary and run in its finally after lease.release() and finish_commit()"},
        "not_tested": ["native and Codex app-server compaction (no local commit)", "session_db=None agents",
                       "per-host manual /compress handlers (deferral driven through compress_context + finalize only)",
                       "real summarizer (fixed text)", "shell hooks", "hung subscriber (the plugins.hook_callback_timeout bound is "
                       "not exercised; sab-h6 shows the contract does not pin it)", "an actual interrupt issued while the observer "
                       "runs (the contract asserts the fence has no commit in flight, which is what hard_interrupt waits on)",
                       "fallback-summary commit as a contract case (probe only, see fallback_commit_probe)",
                       "#53806's start-side pre_context_compression beyond the A/B row (no contract case); its own tests: see OWN/own-r5"],
        "limitations": ["agent-written oracle; per-hunk sabotage listed", "competitor hand-ports are ours, not the authors'",
                        "probe 'committed' = 0 < state.db rows < messages handed in (rotation failures re-flush the full transcript)"],
        "resource_usage": {"wall_s": round(sum(c.get("wall_s", 0) for c in cells_all), 1), "cpu_core_s": None,
                           "gpu_s": 0, "energy_j": None, "api_cost_usd": 0.0},
        "verdict": "KEEP" if infra["infra_cells"] == 0 else "INFRA",
        "carrier_choice": {"winner": "foldin",
                           "why": "#53806 is the only carrier whose post-commit hook fires after the durable commit and stays silent "
                                  "on uncommitted attempts; with the fold-in it passes every case, including the r5 fence/lease clause. "
                                  "#93391 and #53806's own pre hook are start-side, #118847 fires before the commit, #125881 is a "
                                  "fail-closed admission gate; #4123 and #7150 were not run (see STAGING.md)"},
        "learning": {"hypothesis": "one observer contract separates the carriers, and the observer can run outside the commit fence",
                     "result": "KEEP",
                     "reusable_lesson": "check new hook sites against open hazard reports on the same seam (#118120 / #127058) "
                                        "before choosing the delivery point",
                     "roadmap_effect": "salvage-support"},
        "provenance": "self", "frozen": None, "z0evals_study": None, "ai_assistance": AI, "privacy": PRIVACY,
        "artifacts": [{"uri": "raw/f05-r5/", "public": False}, {"uri": "raw/f05-r5s/", "public": False},
                      {"uri": "raw/f05-r5/summary.json", "sha256": sha256(RAW / "f05-r5" / "summary.json"), "public": False},
                      {"uri": "raw/f05-r5s/summary.json", "sha256": sha256(RAW / "f05-r5s" / "summary.json"), "public": False}],
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
                "failing": sorted(set(re.findall(r"^FAILED (\S+)", txt, flags=re.M)))}
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


def attribution(stack_files):
    import contextlib
    import io

    import chs_dns_attribution_r4 as att

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        att.main([str(p) for p in stack_files])
    return json.loads(buf.getvalue())


PREWARM_CHECK_FILES = ("old-test-on-main", "new-test-on-main")


def prewarm_check():
    out = {}
    for name in PREWARM_CHECK_FILES:
        eg = egress_counts(RAW / "prewarm-r4" / f"{name}.egress.log")
        out[name] = {"egress": eg, "result": pytest_summary(RAW / "prewarm-r4" / f"{name}.log")}
    return {
        "what": "the contract test alone on main under the r4 guard (-j 2): the round-1 file (blob 95d731de93, staging commit "
                "de819a7d06) versus the round-2 file (blob 6e8fca00bb, this staging commit)",
        "old_test": out["old-test-on-main"], "new_test": out["new-test-on-main"],
        "reading": "the round-1 test triggered one blocked getaddrinfo('openrouter.ai') per pytest worker, from the "
                   "openrouter-prewarm thread that AIAgent init starts for an OpenRouter base_url; the round-2 test stubs "
                   "agent.agent_init.fetch_model_metadata during init and triggers none",
        "logs_private": [f"raw/prewarm-r4/{n}.log" for n in PREWARM_CHECK_FILES],
    }


def s16_exception(f05r):
    pc = prewarm_check()
    return {
        "status": "recorded exception, NOT accepted: the owner has to accept or reject it (FACTORY S16 defines none). Until then "
                  "the affected cells are INFRA and P5 stays PENDING",
        "scope": "upstream test and eval code this item does not change: sibling compression and plugin test files in the "
                 "adjacent set, evals/compaction/test_region_scoping.py, tests/agent/test_compression_rotation_state.py (OWN), "
                 "and #53806's own tests ported into OWN (they do not pin the context window either)",
        "what": "best-effort DNS lookups for openrouter.ai from three upstream paths: the model-metadata GET at AIAgent init "
                "(agent_init._enforce_minimum_context -> model_metadata.get_model_context_length -> fetch_model_metadata), the "
                "openrouter-prewarm thread AIAgent init starts once per process for an OpenRouter base_url (fetch_model_metadata), "
                "and the video-catalog GET while tool definitions are built (plugins/video_gen/openrouter._catalog)",
        "why_results_stand": ["the guard refused every lookup at DNS; 0 connects",
                              "each path catches the failure and falls back (the 256K default window; an empty prewarm cache; "
                              "the bundled catalog snapshot)",
                              "the same counts occur on base and on the fold-in arms (see per_cell and dns_attribution)",
                              "pass/fail is identical apart from the new contract test",
                              f'the new contract test itself makes 0 lookups under the r4 guard, which suppresses nothing: F05 r5 '
                              f'{f05r["denominators"]["cells"]} cells, {f05r["egress"]["dns"]} dns, {f05r["egress"]["connect"]} connect; '
                              f'alone on main the round-1 file made {pc["old_test"]["egress"]["dns"]} lookups (openrouter-prewarm) and '
                              f'the round-2 file {pc["new_test"]["egress"]["dns"]}'],
        "correction": "r3 stated the same last bullet from F05 r3, but the r3 guard refused to start the openrouter-prewarm thread, "
                      "so the contract test's own lookup was hidden. r4 fixed the test (prewarm stubbed) and the guard (no suppression); "
                      "the alone-on-main prewarm figures are the r4 measurement (raw/prewarm-r4/), the r5 test keeps the same stubs",
        "without_exception": "the affected cells are INFRA, and an experiment with more than 10% INFRA cells is INFRA",
    }


ADJ_FILES = ["tests/agent/test_compaction_observer_hook_contract.py", "tests/agent/test_compression_boundary_hook.py",
             "tests/hermes_cli/test_cli_manual_compress.py", "tests/hermes_cli/test_shared_metrics_engagement.py",
             "tests/agent/test_compression_attempt_telemetry.py", "tests/agent/test_auxiliary_hooks.py",
             "tests/agent/test_shell_hooks.py", "tests/gateway/test_gateway_platform_event_hook.py",
             "tests/hermes_cli/test_hooks_cli.py", "tests/hermes_cli/test_plugins.py",
             "tests/hermes_cli/test_kanban_lifecycle_hooks.py", "tests/agent/test_conversation_compression_manual.py",
             "tests/agent/test_compression_rotation_state.py", "tests/agent/test_compression_persistence.py",
             "tests/agent/test_compression_commit_fence_race.py", "tests/agent/test_compression_attempt_lifecycle.py",
             "tests/agent/test_pre_compress_memory_context_handoff.py", "tests/agent/test_memory_session_switch.py",
             "tests/agent/test_memory_boundary_commit.py", "tests/agent/test_compression_concurrent_fork.py"]


def e12(f05r):
    raw = RAW / "e12-r5"
    arms, cells = {}, []
    stacks = []
    for line in (raw / "arms.txt").read_text().splitlines():
        arm, commit, tree = line.split()
        a = {"commit": commit, "tree": tree}
        for h in ("replay_gates", "ab_checkpoint_preflight", "test_region_scoping", "adjacent"):
            eg = egress_counts(raw / f"{arm}-{h}.egress.log")
            stacks.append(raw / f"{arm}-{h}.egress.stacks")
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
            cell["log_private"] = f"raw/e12-r5/{arm}-{h}.log"
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
            "adjacent_failing_outside_new_test": sorted(f for f in (a["adjacent"]["summary"] or {}).get("failing", [])
                                                        if not f.startswith(CONTRACT)) ==
                                                 sorted(f for f in (base["adjacent"]["summary"] or {}).get("failing", [])
                                                        if not f.startswith(CONTRACT)),
        }
    infra = s16(cells)
    att = attribution(stacks)
    (raw / "dns-attribution").mkdir(exist_ok=True)
    (raw / "dns-attribution" / "summary.json").write_text(json.dumps(att, indent=1))
    clean_ok = all(all(v for v in a["equal_to_base"].values()) for k, a in arms.items() if k != "base")
    strict = "INFRA" if infra["experiment_infra"] else ("PASS" if clean_ok else "FAIL")
    receipt = {
        "schema": "xf.receipt.v1", "id": "E12/e12-r5", "label": "OBSERVED",
        "spec": {"path": None, "factory_row": "FACTORY.md §13 row 9 (E12)", "rev": 5, "sha256": None, "prereg_commit": None,
                 "decision_rule": "replay_gates and ab_checkpoint_preflight verdict maps equal to base; test_region_scoping ALL PASS on "
                                  "every arm; adjacent files identical to base apart from the new contract test. These three "
                                  "harnesses are a subset of the F14 standing set; F14 itself was not run",
                 "f14": "NOT RUN: the guards here are 3 of F14's harnesses, so 'F14 guards equal' (P5) is not established"},
        "runner_revision": {"script": tool("chs_guards_r5.sh"), "wrapper": tool("chs_guard_wrap_r4.py"),
                            "egress_guard": tool("chs_egress_guard_r4.py"), "attribution": tool("chs_dns_attribution_r4.py")},
        "issue": None, "origin_refs": ORIGIN_REFS, "staging": "compaction-hook-salvage",
        "base_revision": MAIN, "head_revision": STAGING, "changed_files": [CONTRACT],
        "harness": {"replay_gates": "evals/token_accounting/replay_gates.py",
                    "ab_checkpoint_preflight": "evals/native_compaction/ab_checkpoint_preflight.py",
                    "test_region_scoping": "evals/compaction/test_region_scoping.py",
                    "adjacent_files": ADJ_FILES},
        "arms": arms, "policy_revision": POLICY, "env": ENV,
        "command": "bash tools/chs_guards_r5.sh <arm> <commit> e12-r5 $WORKTREE $TESTHOME $PY, for base, foldin, foldin-x127058 "
                   "(inside tools/chs_run_all_r5.sh)",
        "gates": {"validity": "PASS" if infra["infra_cells"] == 0 else
                  f'INFRA under strict S16 ({infra["infra_cells"]} of {infra["cells"]} cells); PASS only if the owner accepts the '
                  'recorded S16 exception (not accepted)',
                  "guards": {a: arms[a].get("equal_to_base") for a in arms if a != "base"},
                  "adjacent": {a: arms[a]["adjacent"]["summary"] for a in arms},
                  "flaky": False, "route_scope": "local-compressor"},
        "measurements": [],
        "denominators": {"cells": infra["cells"], "errored_scored_zero": 0, "infra_excluded": 0, "infra": infra["infra_cells"], "completeness": 1.0},
        "egress": {**infra["egress_totals"],
                   "per_cell": {f"{a}/{h}": arms[a][h]["egress"] for a in arms for h in ("replay_gates", "ab_checkpoint_preflight", "test_region_scoping", "adjacent")},
                   "s16": f'{infra["infra_cells"]} of {infra["cells"]} harness cells had blocked DNS lookups '
                          f'({infra["egress_totals"]["connect"]} connects). Strict S16: those cells are INFRA and the experiment is '
                          f'{"INFRA" if infra["experiment_infra"] else "not INFRA"}.',
                   "s16_exception": s16_exception(f05r), "dns_attribution": att},
        "evidence_class": EVIDENCE_CLASS,
        "structural_note": "observer fires are 0 in replay_gates/ab_checkpoint_preflight by construction (no SessionDB in their "
                           "real-compression scenarios; the preflight stubs _compress_context), so 0 is not a native-route measurement",
        "not_tested": ["native compaction on a real provider turn"], "limitations": ["one run per arm per harness"],
        "resource_usage": {"wall_s": None, "cpu_core_s": None, "gpu_s": 0, "energy_j": None, "api_cost_usd": 0.0},
        "verdict": strict,
        "verdict_if_s16_exception_accepted": "PASS" if clean_ok else "FAIL",
        "provenance": "self", "frozen": None, "z0evals_study": None, "ai_assistance": AI, "privacy": PRIVACY,
        "artifacts": [{"uri": "raw/e12-r5/", "public": False}],
    }
    return receipt


C53806_REASONS = {
    "test_plugin_on_session_start_called_on_agent_init":
        "needs the carrier's agent/agent_init.py hunk (plugin on_session_start at agent init), which the hand-port leaves out "
        "with the resume-hook commit",
    "test_pre_context_compression_plugin_hook_fires_before_compress":
        "verbatim: current main hands the hook the transcript with the session store's row metadata attached "
        "(_db_persisted, _row_id, message_uid, timestamp, _db_row_snapshot), so `conversation_history == messages` fails; "
        "session_id, task_id and approx_tokens match. Same result with the call placed in compress_context instead",
    "test_plugin_on_session_start_called_with_compression_boundary":
        "verbatim: on current main a one-message compaction no longer commits, so no post-commit boundary call happens; with "
        "10 messages (main's own sibling test) it fires on the hand-port. On the fold-in it fails by design: the fold-in "
        "replaces this on_session_start(boundary_reason='compression') call with on_compression_complete",
}
C53806_R5_NOTE = {
    "test_pre_context_compression_plugin_hook_fires_before_compress":
        "r5: the fold-in routes the call through hermes_cli.lifecycle.invoke_hook (first-party observers, then plugins) from "
        "agent/conversation_compression_observer.py; the carrier's test patches hermes_cli.plugins.invoke_hook, which "
        "lifecycle still calls, so the adapted test reads the same seam",
}


def own(e12r):
    raw = RAW / "own-r5"
    cells = []
    stacks = []
    for line in (raw / "cells.txt").read_text().splitlines():
        label, commit, path, src = line.split()
        eg = egress_counts(raw / f"{label}.egress.log")
        stacks.append(raw / f"{label}.egress.stacks")
        s = pytest_summary(raw / f"{label}.log")
        cell = {"cell": label, "commit": commit, "file": path,
                "file_source": "carrier's own file on its arm" if src == "carrier-file" else f"factory port: tools/{src}",
                "summary": s, "egress": eg, "exit_class": "INFRA" if (eg["connect"] or eg["dns"]) else "ok",
                "log_private": f"raw/own-r5/{label}.log"}
        if ("c53806" in label or label.startswith("foldin-own")) and s and not s.get("unparsed"):
            failing = {f.rsplit("::", 1)[-1] for f in s["failing"]}
            cell["per_test"] = {t: ("FAIL" if t in failing else "PASS") for t in C53806_REASONS
                                if not (label.endswith("adapted") and t == "test_plugin_on_session_start_called_on_agent_init")}
        cells.append(cell)
    infra = s16(cells)
    att = attribution(stacks)
    return {
        "schema": "xf.receipt.v1", "id": "OWN/own-r5", "label": "OBSERVED",
        "spec": {"path": None, "rev": 5, "decision_rule": "fairness only: each carrier's own tests on its arm; #53806's tests are "
                                                          "ported from its compression commit, verbatim and with two marked drift adaptations"},
        "runner_revision": {"script": tool("chs_own_r5.sh"), "egress_guard": tool("chs_egress_guard_r4.py"),
                            "c53806_port_verbatim": tool("chs_c53806_own_tests.py"),
                            "c53806_port_adapted": tool("chs_c53806_own_tests_adapted.py")},
        "issue": None, "origin_refs": ORIGIN_REFS, "staging": "compaction-hook-salvage",
        "base_revision": MAIN, "head_revision": STAGING, "changed_files": [],
        "purpose": "fairness check: each carrier proves its own, different contract with its own tests",
        "cells": cells,
        "c53806_reading": C53806_REASONS, "c53806_r5_note": C53806_R5_NOTE,
        "policy_revision": POLICY, "env": ENV,
        "command": "bash tools/chs_own_r5.sh $WORKTREE $TESTHOME $PY (inside tools/chs_run_all_r5.sh)",
        "gates": {"validity": "PASS" if infra["infra_cells"] == 0 else
                  f'INFRA under strict S16 ({infra["infra_cells"]} of {infra["cells"]} cells had blocked DNS lookups from the '
                  'carriers\' own or upstream test code); fairness reading only under the recorded S16 exception (not accepted)'},
        "denominators": {"cells": infra["cells"], "errored_scored_zero": 0, "infra_excluded": 0, "infra": infra["infra_cells"], "completeness": 1.0},
        "egress": {**infra["egress_totals"], "dns_attribution": att,
                   "s16_exception": "see E12/e12-r5 egress.s16_exception" if infra["infra_cells"] else None},
        "evidence_class": EVIDENCE_CLASS,
        "reruns": [],
        "limitations": ["#118847's own tests mock hermes_cli.lifecycle.invoke_hook, the seam itself",
                        "#53806's tests are a factory port (its test hunk no longer applies to main's moved file)"],
        "verdict": "N_A (fairness)", "provenance": "self", "frozen": None, "ai_assistance": AI, "privacy": PRIVACY,
    }


def proof(f05r, e12r):
    arms = f05r["arms"]
    return {
        "schema": "xf.receipt.v1", "id": "PROOF/r5", "label": "OBSERVED",
        "spec": {"path": None, "rev": 5, "decision_rule": "aggregation of F05/f05-r5, E12/e12-r5 and MRG/mrg-r5; computes nothing new"},
        "staging": "compaction-hook-salvage", "base_revision": MAIN, "head_revision": STAGING,
        "issue": None, "origin_refs": ORIGIN_REFS, "changed_files": [CONTRACT],
        "contract_test": {"path": CONTRACT, "blob": f05r["contract_test_blob"],
                          "tests": ["test_observer_fires_once_after_the_durable_commit[rotated|in_place|manual_deferred] "
                                    "(r5: also asserts the commit fence has no commit in flight and the session's compression "
                                    "lease is free when the observer runs)",
                                    "test_observer_is_silent_when_nothing_commits[summary_aborted|would_grow_refused|commit_failed|manual_discarded]"]},
        "production_seam": {"fire_site": "agent/conversation_compression.py::compress_context: staged after "
                                         "_finish_compaction_boundary, run in the finally after lease.release() and finish_commit()",
                            "dispatch": "agent/conversation_compression_observer.py -> hermes_cli.lifecycle.has_hook/invoke_hook -> "
                                        "PluginManager.invoke_hook (on_compression_complete is in _HOOK_TIMEOUT_BOUNDED_HOOKS)",
                            "deferral": "chained onto the pending context-engine notification; fires from "
                                        "finalize_context_engine_compression_notification(committed=True)"},
        "gates": {**f05r["gates"], "adjacent": e12r["gates"]["adjacent"], "guards": e12r["gates"]["guards"],
                  "validity": f'F05: {f05r["gates"]["validity"]}; E12: {e12r["gates"]["validity"]}',
                  "f14": "NOT RUN (E12 ran 3 of F14's harnesses); P5 requires F14 guards equal, so P5 cannot be PASS from this "
                         "aggregation"},
        "columns": {a: {"contract": arms[a]["contract_as_committed"]["per_rep"],
                        "adapted": (arms[a]["contract_adapted_to_carrier_hook"] or {}).get("per_rep")} for a in arms},
        "sources": {"F05/f05-r5": "receipts/F05-f05-r5.json", "E12/e12-r5": "receipts/E12-e12-r5.json",
                    "MRG/mrg-r5": "receipts/MRG-mrg-r5.json"},
        "denominators": {"cells": f05r["denominators"]["cells"] + e12r["denominators"]["cells"], "errored_scored_zero": 0,
                         "infra_excluded": 0, "infra": f05r["denominators"]["infra"] + e12r["denominators"]["infra"], "completeness": 1.0},
        "policy_revision": POLICY, "env": ENV, "evidence_class": EVIDENCE_CLASS,
        "verdict": ("PASS" if f05r["verdict"] == "KEEP" and e12r["verdict"] == "PASS" else
                    "INFRA" if f05r["verdict"] == "KEEP" and e12r["verdict"] == "INFRA" else "FAIL"),
        "verdict_if_s16_exception_accepted": ("PASS" if f05r["verdict"] == "KEEP" and e12r["verdict_if_s16_exception_accepted"] == "PASS"
                                              else "FAIL"),
        "verdict_note": "see F05 r5 / E12 r5 validity. Under strict S16 a cell with a blocked upstream DNS lookup is INFRA; this "
                        "aggregation reads PASS only if those cells are clean or the owner accepts the recorded S16 exception. "
                        "F14 was not run, so P5 stays PENDING either way",
        "provenance": "self", "frozen": None, "ai_assistance": AI, "privacy": PRIVACY,
    }


def mrg():
    raw = RAW / "mrg-r5"
    cells = []
    for line in (raw / "cells.txt").read_text().splitlines():
        label, commit, *paths = line.split()
        eg = egress_counts(raw / f"{label}.egress.log")
        cells.append({"cell": label, "commit": commit, "files": paths, "summary": pytest_summary(raw / f"{label}.log"),
                      "egress": eg, "exit_class": "INFRA" if (eg["connect"] or eg["dns"]) else "ok",
                      "log_private": f"raw/mrg-r5/{label}.log"})
    infra = s16(cells)
    by = {c["cell"]: c for c in cells}
    ok = (by["x127058-contract"]["summary"].get("failed") == 0 and by["x127058-118120"]["summary"].get("failed") == 0
          and by["x127058-neighbours"]["summary"].get("failed") == by["s5x127058-neighbours"]["summary"].get("failed"))
    merge_tree = git("merge-tree", "--write-tree", "--name-only", REF + "foldin-r5", "refs/xf/pr/127058", check_ok=True)
    return {
        "schema": "xf.receipt.v1", "id": "MRG/mrg-r5", "label": "OBSERVED",
        "spec": {"path": None, "rev": 5, "decision_rule": "the fold-in and NousResearch/hermes-agent#127058 compose: after resolving "
                 "the textual conflict, the contract test and #127058's own test both pass, and #127058's named neighbours fail no "
                 "more than on the staging commit merged with #127058 alone"},
        "runner_revision": {"script": tool("chs_merge127058_r5.sh"), "arm_builder": tool("chs_build_arms_r5.py"),
                            "egress_guard": tool("chs_egress_guard_r4.py")},
        "issue": None, "origin_refs": ORIGIN_REFS, "staging": "compaction-hook-salvage",
        "base_revision": MAIN, "head_revision": STAGING, "changed_files": [],
        "inputs_pinned": {"pr_127058_head": CARRIER_HEADS["127058"], "foldin": git("rev-parse", REF + "foldin-r5"),
                          "foldin_x127058": git("rev-parse", REF + "foldin-x127058-r5"),
                          "s5x127058": git("rev-parse", REF + "s5x127058-r5")},
        "merge_tree": {"command": "git merge-tree --write-tree --name-only foldin-r5 refs/xf/pr/127058",
                       "output": merge_tree.splitlines()[1:] if merge_tree else None,
                       "staging_commit_vs_127058": "clean (the staging commit adds only a test file)",
                       "resolution": "one conflict region in agent/conversation_compression.py: both diffs append a post-fence "
                                     "delivery after commit_fence.finish_commit() in compress_context's finally. Kept both, "
                                     "#127058's memory on_session_switch first, then on_compression_complete "
                                     "(patches/foldin-x127058-delta.patch). Every other hunk of the two diffs merges cleanly"},
        "cells": cells, "policy_revision": POLICY, "env": ENV,
        "command": "bash tools/chs_merge127058_r5.sh $WORKTREE $TESTHOME $PY (inside tools/chs_run_all_r5.sh)",
        "gates": {"validity": "PASS" if infra["infra_cells"] == 0 else
                  f'INFRA under strict S16 ({infra["infra_cells"]} of {infra["cells"]} cells had blocked DNS lookups)'},
        "denominators": {"cells": infra["cells"], "errored_scored_zero": 0, "infra_excluded": 0, "infra": infra["infra_cells"],
                         "completeness": 1.0},
        "egress": infra["egress_totals"], "evidence_class": EVIDENCE_CLASS,
        "verdict": ("PASS" if ok and infra["infra_cells"] == 0 else ("INFRA" if ok else "FAIL")),
        "verdict_if_s16_exception_accepted": "PASS" if ok else "FAIL",
        "limitations": ["one run per cell", "#127058 is an open PR; its head may change"],
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
    e = e12(f)
    m = mrg()
    write("F05-f05-r5.json", f)
    write("E12-e12-r5.json", e)
    write("OWN-own-r5.json", own(e))
    write("MRG-mrg-r5.json", m)
    write("PROOF-r5.json", proof(f, e))
