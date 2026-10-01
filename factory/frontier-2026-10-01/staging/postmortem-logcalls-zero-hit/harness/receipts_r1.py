"""Round-1 receipt fix (phase-3 verifier findings), run from the staging dir:  python3 harness/receipts_r1.py .

1. Redacts absolute local paths in receipts/*.json and receipts/raw/** (text files only; binary files are
   checked, never rewritten). Upstream source copies (raw/base_probes/*.py, raw/logcalls.main@*.py) contain
   no absolute paths and stay byte-identical to their upstream blobs.
2. Recomputes every evidence sha256 after redaction.
3. Fills the xf.receipt.v1 fields (FACTORY.md section 9.2) the r20261001-01 receipts lacked: spec,
   runner_revision, arms, policy_revision, gates.validity (+ the other gate keys), ab, denominators,
   limitations, carrier_choice, learning.
4. Writes PROOF/r20261001-02 (re-measure on the declared main) from receipts/raw/r1/.
5. Rewrites receipts/INDEX.json and prints the sha256 of every receipt.
Deterministic and idempotent: re-running yields byte-identical files.
"""
import hashlib, json, pathlib, re, sys

D = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
R = D / "receipts"
FIX_AT = "2026-10-01T11:15Z"

BASE = "234badf4012af380d23c91eae55d045a69c69ffb"
MAIN = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
HEAD = "dd4dd10611e8c23c7579a4ddb95655abebbaca27"

REDACT = [  # (pattern, placeholder); order matters
    (r"/tmp/claude-\d+/[^/\s\"']+/[0-9a-f-]{36}/scratchpad", "$S"),
    (r"$ARTIFACTS/frontier-2026-10-01/staging/postmortem-logcalls-zero-hit/", ""),
    (r"$ARTIFACTS/promotion-readiness-2026-10-01/wt/(?:staging|stfix)/postmortem-logcalls-zero-hit", "$W"),
    (r"$ARTIFACTS/factory/xf", "$X"),
    (r"(?:/var)?/tmp/hermes-pytest-\d+/r-[^/\s\"']+/pytest-of-[^/\s\"']+/pytest-\d+", "<pytest-tmp>"),
    (r"<hermes-home>/hermes-agent/venv/bin/python", "$HERMES_PYTHON"),
]
ABS = re.compile(r"(/mnt/|/tmp/|/var/|/home/|/workspace/|/root/|/Users/)")


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def redact_tree():
    changed = []
    for p in sorted(R.rglob("*")):
        if not p.is_file(): continue
        b = p.read_bytes()
        try:
            t = b.decode("utf-8")
        except UnicodeDecodeError:
            if ABS.search(b.decode("latin-1")): sys.exit(f"absolute path inside binary {p}")
            continue
        n = t
        for pat, rep in REDACT: n = re.sub(pat, lambda m, rep=rep: rep, n)
        if ABS.search(n): sys.exit(f"unredacted absolute path left in {p.relative_to(D)}: {ABS.search(n).group(0)}")
        if n != t:
            p.write_text(n, encoding="utf-8"); changed.append(str(p.relative_to(D)))
    return changed


REDACTION = {
    "applied_at": FIX_AT,
    "rule": "Absolute local paths in receipts/ and receipts/raw/ text replaced by placeholders: $S = scratch dir, "
            "$W = build worktree, $X = factory dir, <pytest-tmp> = pytest tmp root, $HERMES_PYTHON = test interpreter; "
            "the staging-dir prefix is dropped, so harness/... and receipts/... are relative to the staging dir. "
            "No other byte changed. Evidence sha256 values were recomputed after redaction.",
    "script": "harness/receipts_r1.py",
}

SPEC = {
    "path": None, "rev": None, "sha256": None, "prereg_commit": None, "decision_rule_sha": None,
    "status": "NOT_PREREGISTERED",
    "why": "Built before factory Wave 0: no factory/xf/specs/*.toml and no claude/ledger commit exist yet, so there is "
           "no spec file and no pre-registration commit. The decision rule applied is the selection entry's "
           "acceptance_gates. Its file hash below was taken at round-1 fix time; the file's mtime "
           "(2026-10-01T08:48Z) falls inside the build window, so it is not a pre-registration.",
    "selection": {"file": "frontier-2026-10-01/selection.json", "entry": "staging_set[4] id=postmortem-logcalls-zero-hit",
                  "sha256": "207190d3fe1a7dcdd29ceafd84ff092d289079b93dff97ff5b6f1ea0586d55e3"},
}
RUNNER = "none: no xf runner exists before Wave 0; the scripts that ran are hashed under inputs (harness/)"
POLICY = {
    "AGENTS.md": f"65aa3e61bcba610da21279a17385671263be39e9@{BASE[:10]} (same blob @{MAIN[:10]})",
    "CONTRIBUTING.md": f"b0baa59b5057c204b3c09d3dd170c0955cfdb39c@{BASE[:10]} (same blob @{MAIN[:10]})",
    ".github/PULL_REQUEST_TEMPLATE.md": f"5496eb534fef9d08c091b8186e7edd1b5cf356db@{BASE[:10]} (same blob @{MAIN[:10]})",
    "factory": "FACTORY.md sha256:7726ba18b43a9367f91d7f70c3aaefb96a9863761ddf71225c61c26a30d688d4 "
               "(no ledger commit exists; hashed at round-1 fix time, mtime 2026-10-01T08:48Z)",
    "protocol": "promotion-readiness PROTOCOL.md sha256:182e3fbae771d7219497833b3f9d6f7ed385d70abace8736559026e4e60b90d4",
}
NA_GATES = {"guards": {"F14": "NOT_RUN (factory Wave 0 standing set not built)"}, "flaky": False, "noise_floor": None,
            "credit": None, "informativeness": "N_A", "route_scope": "n/a",
            "cache_read_ratio": {"status": "N_A", "before": None, "after": None}}
PARSERS = {"main_parser": {"path": "evals/postmortem/forensics/logcalls.py", "blob": f"fa5be57125c9c69103df9b5392f6045d67a5d760@{BASE[:10]}",
                           "copy": "receipts/raw/logcalls.main@234badf401.py"},
           "patched_parser": {"path": "evals/postmortem/forensics/logcalls.py", "blob": f"23badda96ba98123c34cdc65203fb21960bb1cf2@{HEAD[:10]}"}}
REF_HARNESS_PR = "NousResearch/hermes-agent#103756"

PER = {
    "PROOF/r20261001-01": {
        "arms": {"base": {"commit": BASE, "tree": "7c5bdaf2cca26699a961b711f9efebba37e93cf7"},
                 "head": {"commit": HEAD, "tree": "9f262517dd06acc2f09fbadb401a0d70dc3e5936"},
                 "red_arm": "head tree with evals/postmortem/forensics/logcalls.py reset to main's blob fa5be57125"},
        "validity": ("PASS", "Fresh scratch HOME/HERMES_HOME per run; RED fails at the stated seam (coverage.calls_found "
                              "loses the miss / cold_write / no_field lines), not in setup; 0 errored or infra runs."),
        "denominators": {"cells": 10, "unit": "test-runner invocations: RED 1 + GREEN 3 + per-hunk sabotage 6",
                         "errored_scored_zero": 0, "infra_excluded": 0, "completeness": 1.0},
        "limitations": ["evals/ is outside pytest testpaths, so there is no CI evidence",
                        "one host, one test interpreter (Python 3.11.14)",
                        "the sabotage set pins 6 logcalls hunks; the early-exit guard, the coverage print line and the "
                        "docstring are not pinned by any test (gates.sabotage.unpinned_hunks; see PROOF/r20261001-02)",
                        "no bwrap sandbox; isolation came from scratch HOME/HERMES_HOME"],
        "learning": {"hypothesis": "main's _LINE regex drops every API-call line without cache= and every usage=unavailable line",
                     "result": "KEEP",
                     "observed_evidence": ["RED: calls_found 2 vs 3 and 2 vs 4", "GREEN 3/3 (8 passed)", "6/6 sabotaged hunks red again"],
                     "regressions": [],
                     "reusable_lesson": "a per-hunk sabotage list must name the hunks it does not pin, and the PR body "
                                        "must not claim more coverage than that list",
                     "roadmap_effect": "stage as a fold-in on NousResearch/hermes-agent#121135"},
    },
    "F06RT/r20261001-01": {
        "validity": ("PASS", "Real record_response_usage through the real agent.log formatter, isolated HOME, loopback-only "
                              "socket guard: 0 egress attempts; the live probes were never imported (regex literals via ast)."),
        "denominators": {"cells": 18, "unit": "line-match cells (3 arms x 2 parsers, 5 producer lines each) + probe "
                         "replays (3 arms x 2 probes x 2 regex sides)", "errored_scored_zero": 0, "infra_excluded": 0,
                         "completeness": 1.0},
        "limitations": ["OpenAI-style prompt_tokens_details usage shape only",
                        "live probes replayed by regex literal, never executed",
                        "producer exercised offline with fixture usage objects; no provider call"],
        "learning": {"hypothesis": "on main and on both carrier arms, the real producer's miss / cold_write / no_field / "
                                   "usage-less lines are all dropped by the old regex and all read by the new one",
                     "result": "KEEP",
                     "observed_evidence": ["old parser 1/5, new 5/5 on every arm", "probe regexes: old 1/4 rows, new 4/4"],
                     "regressions": [],
                     "reusable_lesson": "on a legacy line (no cache_state=), a real miss and a route that reports no cache "
                                        "counter are byte-identical apart from the call number and id (raw/rt_main.json "
                                        "lines #2 and #4), so the patched parser reads both as zero-hit; only #121135's "
                                        "cache_state= can separate them",
                     "roadmap_effect": "disclose the legacy-line ambiguity in the PR body"},
    },
    "F06SYN/r20261001-01": {
        "arms": PARSERS,
        "validity": ("PASS", "Seeded synthetic corpora with known ground truth; both parsers ran on byte-identical inputs "
                              "(sha256 under inputs.corpora_sha256); isolated HOME/HERMES_HOME."),
        "denominators": {"cells": 4, "unit": "parser runs: 2 corpora x 2 parsers", "calls_per_corpus": 420,
                         "errored_scored_zero": 0, "infra_excluded": 0, "completeness": 1.0},
        "limitations": ["synthetic corpora: magnitudes are MODELED and depend on the injected miss rate",
                        "no real agent.log / state.db (needs OD-7)",
                        "the corpora contain no route without a cache counter, so the legacy-line ambiguity "
                        "(such a route reads as zero-hit) is not modeled here"],
        "learning": {"hypothesis": "dropping zero-hit calls biases coverage down and the hit ratio up; the fix recovers "
                                   "the corpus truth and leaves an all-hit corpus unchanged",
                     "result": "KEEP",
                     "observed_evidence": ["24 dropped calls = 24 zero-hit calls", "patched hit ratio = truth 0.9308",
                                           "all-hit observed/modeled blocks identical"],
                     "regressions": [],
                     "reusable_lesson": "synthetic magnitudes only; the real-run bias stays NOT_MEASURED until OD-7",
                     "roadmap_effect": "queue F06 on real copies (owner)"},
    },
    "E19SYN/r20261001-01": {
        "arms": PARSERS,
        "validity": ("PASS", "Same seeded e19_shaped corpus for both parsers; isolated HOME/HERMES_HOME."),
        "denominators": {"cells": 2, "unit": "e19_switch.py runs: main parser, patched parser (1 switch, k=5)",
                         "errored_scored_zero": 0, "infra_excluded": 0, "completeness": 1.0},
        "limitations": ["one synthetic model switch, k=5", "magnitudes MODELED", "no real E19 baseline (needs OD-7)"],
        "learning": {"hypothesis": "the old parser hides the cache loss at a model switch because it drops the miss",
                     "result": "KEEP",
                     "observed_evidence": ["old parser first sees call #62, patched sees #61 (the true switch call)"],
                     "regressions": [],
                     "reusable_lesson": None,
                     "roadmap_effect": "queue E19 on real copies after F06 (owner)"},
    },
    "CARRIER/r20261001-01": {
        "validity": ("PASS", "merge-tree on exact heads read from gh; carrier suites ran with fresh scratch HOME/HERMES_HOME; "
                              "0 errored runs."),
        "denominators": {"cells": 8, "unit": "6 merge-tree pairs + 2 carrier test arms", "errored_scored_zero": 0,
                         "infra_excluded": 0, "completeness": 1.0},
        "limitations": ["no three-way arm: #121135 and #119713 conflict with each other in agent/turn_usage.py",
                        "carrier suites and the harness only; the full test suite was not run"],
        "carrier_choice": {"winner": "NousResearch/hermes-agent#121135 (fold-in target)",
                           "why": "the only open PR that changes the per-call line's cache semantics (adds cache_state=); "
                                  "its automated review (issuecomment-5854199241) flags that no parser reads the new "
                                  "states; merge-tree clean with this commit; its own suite plus the harness: 126 passed "
                                  "on the merged arm. #119713 is a line-shape dependency, not a carrier."},
        "learning": {"hypothesis": "the commit composes with both line-format PRs",
                     "result": "KEEP",
                     "observed_evidence": ["clean merges with each carrier", "126 and 10 passed on the arms"],
                     "regressions": [],
                     "reusable_lesson": "#121135 and #119713 conflict with each other; the combined line shape is "
                                        "covered only by the harness fixture",
                     "roadmap_effect": "offer as a fold-in on #121135"},
    },
}

ORDER = ["schema", "id", "tier", "cost", "experiment", "spec", "runner_revision", "issue", "origin_refs", "staging",
         "base_revision", "declared_main", "arms", "head_revision", "changed_files", "policy_revision", "env", "inputs",
         "command", "gates", "ab", "measurements", "denominators", "evidence_class", "harness_abi", "not_tested",
         "limitations", "resource_usage", "verdict", "carrier_choice", "learning", "provenance", "frozen",
         "z0evals_study", "ai_assistance", "privacy", "redaction", "evidence"]


def ordered(d):
    out = {k: d[k] for k in ORDER if k in d}
    out.update({k: v for k, v in d.items() if k not in out})
    return out


def complete(d):
    p = PER[d["id"]]
    d["spec"], d["runner_revision"], d["policy_revision"] = SPEC, RUNNER, POLICY
    if "arms" in p: d["arms"] = p["arms"]
    if REF_HARNESS_PR not in d["origin_refs"]: d["origin_refs"].append(REF_HARNESS_PR)
    g = d.get("gates") or {"red": None, "green": None, "sabotage": None, "adjacent": None,
                           "note": "not a RED/GREEN receipt; see PROOF/r20261001-01"}
    v, why = p["validity"]
    g = {"validity": v, "validity_basis": why, **{k: x for k, x in g.items() if k not in ("validity", "validity_basis")}}
    for k, x in NA_GATES.items(): g.setdefault(k, x)
    d["gates"] = g
    d["ab"] = None
    d["denominators"], d["limitations"], d["learning"] = p["denominators"], p["limitations"], p["learning"]
    d["carrier_choice"] = p.get("carrier_choice")
    d["redaction"] = REDACTION
    return d


def rehash(d):
    for e in d.get("evidence", []): e["sha256"] = sha(D / e["path"])
    return d


def tests_summary(path):
    m = re.search(r"Summary: (\d+) files?, (\d+) tests passed, (\d+) failed", (D / path).read_text(encoding="utf-8"))
    return {"files": int(m.group(1)), "passed": int(m.group(2)), "failed": int(m.group(3))}


def r02():
    raw = "receipts/raw/r1"
    red_txt = (D / raw / "red.txt").read_text(encoding="utf-8")
    assertions = sorted(set(re.findall(r"^E\s+assert .*$", red_txt, re.M)))
    mt = (D / raw / "merge_tree.txt").read_text(encoding="utf-8").splitlines()
    files = ["green1.txt", "green2.txt", "green3.txt", "red.txt", "neg_U1_early_exit.diff", "neg_U1_early_exit.txt",
             "only_no_field_patched.txt", "only_no_field_sabotaged.txt", "merge_tree.txt", "arms.txt",
             "tests_a1_pr121135.txt", "tests_a2_pr119713.txt", "workflow_push.txt", "source_facts.txt"]
    scripts = {f"harness/r1/{s}": sha(D / "harness" / "r1" / s) for s in ("mt_r1.sh", "arms_r1.sh", "wf_push.py", "only_nofield.py")}
    green = [tests_summary(f"{raw}/green{i}.txt") for i in (1, 2, 3)]
    d = {
        "schema": "xf.receipt.v1", "id": "PROOF/r20261001-02", "tier": "T1", "cost": "$0",
        "experiment": "Round-1 re-measure for the phase-3 verifier findings, staging commit unchanged: freshness against "
                      "the declared main, RED, GREEN x3, carrier suites on main x carrier, the unpinned early-exit guard, "
                      "push triggers for the fork branch name staged/<id>, and the source lines behind the PR body's "
                      "legacy-line disclosure.",
        "spec": SPEC, "runner_revision": RUNNER,
        "issue": "kvnloo/hermes-agent (no campaign thread yet; OD-9). Queue board kvnloo/hermes-agent#404 has no row for this id.",
        "origin_refs": ["NousResearch/hermes-agent#121135", "NousResearch/hermes-agent#84460", "NousResearch/hermes-agent#119713",
                        "NousResearch/hermes-agent#103563", REF_HARNESS_PR],
        "staging": "postmortem-logcalls-zero-hit",
        "base_revision": BASE, "declared_main": MAIN, "head_revision": HEAD,
        "arms": {
            "main": {"commit": MAIN, "tree": "aefff2f5884831d530ce341b3dcff968856d0be6",
                     "fetched_at": "2026-10-01T11:04Z", "commit_date": "2026-10-01T10:56:05Z"},
            "main_x_staging": {"merge_tree": "f388caeb37c573dcd1dfb1211526f32b0c7abdc6", "merge": "clean",
                               "note": "tests ran on this tree (main + `git cherry-pick -n` of the head; write-tree equal)"},
            "a1_pr121135": {"merge_tree": "798e76b64df1e1c17a3360e121b26ff8d0d042a7", "carrier_head": "dd4a0ca4cf3345702eb7be95e11873308d3015b5",
                            "merge": "clean", "overlay": ["agent/turn_usage.py", "agent/usage_pricing.py",
                                                          "tests/agent/test_cache_log_states.py", "tests/agent/test_turn_usage_log_line.py"]},
            "a2_pr119713": {"merge_tree": "1f2049ee49cd66d7e65729fda05277a1ee3a6964", "carrier_head": "7471d9915d7d1ce3e94f9d18c9d775461d269815",
                            "merge": "clean", "overlay": ["agent/turn_response_check.py", "agent/turn_usage.py",
                                                          "tests/agent/test_turn_usage_log_line.py"]},
        },
        "changed_files": ["evals/postmortem/forensics/logcalls.py", "evals/postmortem/live_ab/cache_prefix_live.py",
                          "evals/postmortem/live_ab/cache_prefix_wire.py", "evals/postmortem/tests/test_postmortem_harness.py"],
        "policy_revision": POLICY,
        "env": {"host": "groot", "test_python": "3.11.14 (HERMES_PYTHON, not activated)", "host_python": "3.14.7",
                "sandbox": "no bwrap (xf executor not built); HOME/HERMES_HOME = fresh scratch dirs", "tz": "UTC timestamps"},
        "inputs": {"scripts": scripts, "gh_read_at": "2026-10-01T11:05Z",
                   "carriers": {"#121135": {"head": "dd4a0ca4cf3345702eb7be95e11873308d3015b5", "state": "OPEN"},
                                "#119713": {"head": "7471d9915d7d1ce3e94f9d18c9d775461d269815", "state": "OPEN"}}},
        "command": ["bash harness/r1/mt_r1.sh $S/h.git > receipts/raw/r1/merge_tree.txt",
                    "env -u __HERMES_ACTIVATED HOME=$S/testhome-sf-postmortem-logcalls-zero-hit HERMES_HOME=$HOME/.hermes "
                    "HERMES_PYTHON=$HERMES_PYTHON bash scripts/run_tests.sh -j 2 evals/postmortem/tests/test_postmortem_harness.py "
                    "tests/agent/test_turn_usage_log_line.py -q   # in $W at main + head; RED with logcalls.py reset to main",
                    "bash harness/r1/arms_r1.sh $S $W receipts/raw/r1",
                    "$HERMES_PYTHON harness/r1/only_nofield.py   # in $W, committed vs sabotaged logcalls.py",
                    "$HERMES_PYTHON harness/r1/wf_push.py $S/h.git " + HEAD + " staged/postmortem-logcalls-zero-hit"],
        "freshness": {"drift_commits": 36, "drift_range": f"{BASE[:10]}..{MAIN[:10]}",
                      "drift_touching": {"paths": ["evals/postmortem", "agent/turn_usage.py", "agent/usage_pricing.py",
                                                   "hermes_logging.py", "tests/agent/test_turn_usage_log_line.py"], "commits": 0},
                      "drift_touching_workflows": 0, "carrier_heads_unchanged": True,
                      "merge_tree": [l for l in mt if " x " in l],
                      "consequence": "F06RT, F06SYN and E19SYN were measured on 234badf401; no drift commit touches the "
                                     "producer, the parser or their tests, so those results carry to the declared main."},
        "gates": {
            "validity": "PASS",
            "validity_basis": "Fresh scratch HOME/HERMES_HOME; RED fails at the stated seam; carrier suites ran on "
                              "main x carrier trees re-merged on the declared main; 0 errored runs.",
            "red": {"arm": "main + head, logcalls.py reset to main", "result": "PASS", "observed": tests_summary(f"{raw}/red.txt"),
                    "assertions": assertions, "seam_covered": True},
            "green": {"arm": "main + head (tree f388caeb37)", "result": "PASS", "reps": green,
                      "reps_agree": f"{sum(1 for g in green if g['failed'] == 0 and g['passed'] == 8)}/3"},
            "sabotage": {"per_hunk": {"U1_early_exit": {"hunk": "logcalls main(): `if not scored:` reverted to `if not calls:`",
                                                        "result": tests_summary(f"{raw}/neg_U1_early_exit.txt"), "red_again": False}},
                         "unpinned_hunks": [
                             "logcalls early-exit guard (`if not scored`): reverting it to `if not calls` passes every test. "
                             "With only cache_state=no_field calls, the reverted code raises ZeroDivisionError at "
                             "hit_total / in_total; the committed code prints a message and returns 1 "
                             "(raw/r1/only_no_field_*.txt). Behaviour is correct as committed, but no test pins it.",
                             "logcalls coverage print line", "logcalls docstring"]},
            "adjacent": {"files": ["tests/agent/test_turn_usage_log_line.py"], "base": "3 passed", "arm": "3 passed",
                         "identical": True, "pre_existing_failures": []},
            **NA_GATES,
        },
        "ab": None,
        "measurements": [
            {"name": "red_tests_failed", "arm": "main", "value": tests_summary(f"{raw}/red.txt")["failed"], "n": 1, "label": "OBSERVED", "statistic": "count"},
            {"name": "green_tests_passed", "arm": "main+head", "value": 8, "n": 3, "label": "OBSERVED", "statistic": "count per rep"},
            {"name": "tests_on_arm", "arm": "a1_pr121135", **tests_summary(f"{raw}/tests_a1_pr121135.txt"), "label": "OBSERVED"},
            {"name": "tests_on_arm", "arm": "a2_pr119713", **tests_summary(f"{raw}/tests_a2_pr119713.txt"), "label": "OBSERVED"},
            {"name": "early_exit_sabotage_caught", "value": False, "label": "OBSERVED"},
            {"name": "only_no_field_input", "committed": "rc 1 with message", "sabotaged": "ZeroDivisionError", "label": "OBSERVED"},
            {"name": "push_trigger_matches", "branch": "staged/postmortem-logcalls-zero-hit", "value": 0, "label": "OBSERVED",
             "note": "workflow files at the head commit; GitHub reads push workflows from the pushed commit"},
        ],
        "source_facts": {
            "file": "receipts/raw/r1/source_facts.txt", "at": MAIN,
            "facts": ["agent/turn_usage.py:192-193 writes cache= only when cache_read_tokens is non-zero; :96 is the usage=unavailable line",
                      "agent/usage_pricing.py:625-627 reads each usage field with _first_nonzero, so a field the provider omits becomes 0",
                      "agent/bedrock_adapter.py:863-869 and agent/gemini_native_adapter.py:587-591 write absent cache counters as an explicit 0 "
                      "(the same sites #121135's automated review lists under Blocker 2)",
                      "so on a legacy line a route with no cache counter has no cache= and the patched parser counts it as zero-hit",
                      "the dd4dd10611 docstring states the rule (no cache= is a zero-hit call; cache_state=no_field stays out of the "
                      "ratio) but does not say that legacy lines cannot separate a miss from a route with no cache counter"]},
        "denominators": {"cells": 15, "unit": "RED 1 + GREEN 3 + early-exit sabotage 1 + only-no_field probe 2 + carrier arms 2 + merge-tree pairs 6",
                         "errored_scored_zero": 0, "infra_excluded": 0, "completeness": 1.0},
        "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
        "harness_abi": {"harness": "hermes evals/postmortem", "editor_abi": "n/a"},
        "not_tested": ["evals/ is outside pytest testpaths, so CI does not run these tests",
                       "live probes not executed (real provider, paid)", "real agent.log / state.db (OD-7)",
                       "fork push itself (no push made; trigger match computed from workflow files)"],
        "limitations": ["one host, one test interpreter", "round trip and synthetic F06/E19 not re-run; carried by the "
                        "path-unchanged argument under freshness"],
        "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0, "energy_j": None},
        "verdict": "KEEP", "carrier_choice": None,
        "learning": {"hypothesis": "the staged commit still applies, proves and composes on the declared main, and the "
                                   "verifier's unpinned-hunk and disclosure findings are accurate",
                     "result": "KEEP",
                     "observed_evidence": ["merge clean, 0 relevant drift", "RED 2 failed / GREEN 3/3",
                                           "early-exit sabotage not caught", "126 and 10 passed on the arms"],
                     "regressions": [],
                     "reusable_lesson": "re-measure on the declared main before restating any SHA or count",
                     "roadmap_effect": "text fixes only; commit unchanged"},
        "provenance": "self", "frozen": None, "z0evals_study": None,
        "ai_assistance": "Claude Code (Opus 5.5) ran the re-measure and wrote this receipt; disclosed per repository policy",
        "privacy": "synthetic inputs only; no real state.db or agent.log was read",
        "redaction": REDACTION,
        "evidence": [{"path": f"{raw}/{f}", "sha256": None} for f in files],
    }
    return d


def dump(p, d): p.write_text(json.dumps(ordered(d), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


changed = redact_tree()
index = {}
for rid, fn in [("PROOF/r20261001-01", "PROOF_r20261001-01.json"), ("F06RT/r20261001-01", "F06RT_r20261001-01.json"),
                ("F06SYN/r20261001-01", "F06SYN_r20261001-01.json"), ("E19SYN/r20261001-01", "E19SYN_r20261001-01.json"),
                ("CARRIER/r20261001-01", "CARRIER_r20261001-01.json")]:
    p = R / fn
    dump(p, rehash(complete(json.loads(p.read_text(encoding="utf-8")))))
    index[rid] = {"path": f"receipts/{fn}", "sha256": sha(p)}
p = R / "PROOF_r20261001-02.json"
dump(p, rehash(r02()))
index["PROOF/r20261001-02"] = {"path": "receipts/PROOF_r20261001-02.json", "sha256": sha(p)}
(R / "INDEX.json").write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
for p in sorted(R.rglob("*")):
    if p.is_file() and ABS.search(p.read_bytes().decode("latin-1")): sys.exit(f"absolute path left in {p}")
print("redacted:", len(changed), "files")
for k, v in index.items(): print(f"{k}  {v['sha256']}")
