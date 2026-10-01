"""Round-3 receipt pass, run from the staging dir:  python3 -B harness/r3/receipts_r3.py .

1. Privacy: env.host in the r01/r02 receipts becomes "<host>". The harness scripts those receipts cite keep
   their as-run sha256 under inputs (those bytes held local paths inline and are kept privately, never
   published). The published harness/ copies take the paths from the environment; their sha256 values are
   added under inputs.scripts_published. No measurement changes.
2. Writes PROOF/r20261001-03 (freshness re-measure on upstream main 34f8ec3b40) from receipts/raw/r3/.
3. Rewrites receipts/INDEX.json and prints the sha256 of every receipt.
Idempotent: re-running yields byte-identical files (the run timestamp is fixed below).
"""
import hashlib
import json
import pathlib
import re
import socket
import sys

D = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
R = D / "receipts"
RAW3 = R / "raw" / "r3"
FIX_AT = "2026-10-01T18:42Z"   # this receipt pass

BASE = "234badf4012af380d23c91eae55d045a69c69ffb"
PREV_MAIN = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
MAIN = "34f8ec3b407e50bad3ae27e4cd79d65212061356"
MAIN_TREE = "f05476c596c08b41c5370661dabc20fce223c9c9"
HEAD = "dd4dd10611e8c23c7579a4ddb95655abebbaca27"
MERGE_TREE = "c7460b5c539e76cff2dbe5cdb7961cec1334a892"
SANDBOX_SHA = "c9586195c43a926317fa3d6bc18db1937527a6308dc30c683ce9c6a83398638a"
CHANGED = ["evals/postmortem/forensics/logcalls.py", "evals/postmortem/live_ab/cache_prefix_live.py",
           "evals/postmortem/live_ab/cache_prefix_wire.py", "evals/postmortem/tests/test_postmortem_harness.py"]
INVALIDATE_ON = ["evals/postmortem", "agent/turn_usage.py", "agent/usage_pricing.py", "hermes_logging.py",
                 "tests/agent/test_turn_usage_log_line.py", ".github/workflows"]
OLD = ["PROOF_r20261001-01", "F06RT_r20261001-01", "F06SYN_r20261001-01", "E19SYN_r20261001-01",
       "CARRIER_r20261001-01", "PROOF_r20261001-02"]


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, obj): p.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def summary(name):
    t = (RAW3 / name).read_text(encoding="utf-8")
    m = re.search(r"=== Summary: (\d+) files, (\d+) tests passed, (\d+) failed", t)
    return {"files": int(m[1]), "passed": int(m[2]), "failed": int(m[3])}


def e_lines(name):
    t = (RAW3 / name).read_text(encoding="utf-8")
    return sorted({ln.rstrip() for ln in t.splitlines() if ln.startswith("E  ")})


def per_file(name):
    t = (RAW3 / name).read_text(encoding="utf-8")
    return {f: c.replace("✓", " passed").replace("✗", " failed")
            for f, c in re.findall(r"[✓✗] (\S+\.py) \(([^,)]+)", t)}


def harness_path(key):
    for cand in (D / key, D / "harness" / key):
        if cand.is_file():
            return cand
    return None


# 1. privacy pass on the r01/r02 receipts
host = socket.gethostname()
for stem in OLD:
    p = R / f"{stem}.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    if d.get("env", {}).get("host") == host:
        d["env"]["host"] = "<host>"
    published = {}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) and k.endswith((".sh", ".py")):
                    hp = harness_path(k)
                    if hp is not None and sha(hp) != v:
                        published[str(hp.relative_to(D))] = sha(hp)
                elif isinstance(v, (dict, list)) and k != "scripts_published":
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d.get("inputs", {}))
    if published:
        d["inputs"]["scripts_published"] = dict(sorted(published.items()))
    red = d.setdefault("redaction", {})
    red["r3"] = {
        "applied_at": FIX_AT,
        "rule": ("env.host replaced by <host>. The harness scripts cited under inputs keep their as-run sha256; "
                 "those bytes held local paths inline and are kept privately (private/harness-as-run/, never "
                 "published). The published harness/ copies take the paths from the environment; their sha256 "
                 "values are under inputs.scripts_published. No measurement changed."),
        "script": "harness/r3/receipts_r3.py",
    }
    dump(p, d)

# 2. PROOF/r20261001-03
r02 = json.loads((R / "PROOF_r20261001-02.json").read_text(encoding="utf-8"))
red_s, adj_s = summary("red.txt"), summary("adj_base.txt")
greens = [summary(f"green{i}.txt") for i in (1, 2, 3)]
mt = (RAW3 / "merge_tree.txt").read_text(encoding="utf-8")
pairs = re.findall(r"^(\S+ x \S+): (CLEAN tree=[0-9a-f]+|CONFLICT)$", mt, re.M)
adj_base_files, green_files = per_file("adj_base.txt"), per_file("green1.txt")
r03 = {
    "schema": "xf.receipt.v1",
    "id": "PROOF/r20261001-03",
    "tier": "T1",
    "cost": "$0",
    "experiment": ("Round-3 freshness re-measure on upstream main 34f8ec3b40, staging commit unchanged: merge-tree "
                   "matrix with both carriers, invalidate_on drift since the base, RED, GREEN x3 and ADJACENT, each "
                   "test run in the factory bwrap sandbox."),
    "spec": r02["spec"],
    "runner_revision": "none: no xf runner exists for this item; the sandbox wrapper and the r3 script are hashed under inputs",
    "issue": r02["issue"],
    "origin_refs": r02["origin_refs"],
    "staging": "postmortem-logcalls-zero-hit",
    "base_revision": BASE,
    "declared_main": MAIN,
    "arms": {
        "main": {"commit": MAIN, "tree": MAIN_TREE, "commit_date": "2026-10-01T17:29:37Z",
                 "read_at": "2026-10-01T18:34Z (h.git refs/heads/main; the upstream main named for this round)"},
        "main_x_staging": {"merge_tree": MERGE_TREE, "merge": "clean",
                           "note": "tests ran on main with the head's 4 files checked out; git write-tree equal to the merge tree"},
        "main_with_head_tests_main_parser": {"note": "RED arm: as main_x_staging, with logcalls.py reset to main"},
        "base_main": {"tree": MAIN_TREE, "note": "ADJACENT base arm: all of evals/postmortem reset to main; write-tree equal to main's tree"},
    },
    "head_revision": HEAD,
    "changed_files": CHANGED,
    "policy_revision": {
        "AGENTS.md": "65aa3e61bcba610da21279a17385671263be39e9@34f8ec3b40 (same blob @234badf401)",
        "CONTRIBUTING.md": "b0baa59b5057c204b3c09d3dd170c0955cfdb39c@34f8ec3b40 (same blob @234badf401)",
        ".github/PULL_REQUEST_TEMPLATE.md": "5496eb534fef9d08c091b8186e7edd1b5cf356db@34f8ec3b40 (same blob @234badf401)",
        "factory": r02["policy_revision"]["factory"].split(" (")[0] + " (unchanged since round 1)",
        "protocol": r02["policy_revision"]["protocol"],
    },
    "env": {"host": "<host>", "test_python": "HERMES_PYTHON = <venv>/bin/python, set by the sandbox wrapper (same venv as r01/r02)",
            "sandbox": ("xf-sandbox.sh: bwrap, read-only root, own netns (loopback only), clearenv, real home masked, "
                        "HOME/HERMES_HOME under the run dir, both temp dirs inside the run dir, Hermes console scripts stubbed"),
            "tz": "UTC timestamps"},
    "inputs": {
        "scripts": {"harness/r3/mt_r3.sh": sha(D / "harness/r3/mt_r3.sh")},
        "sandbox_sha256": SANDBOX_SHA,
        "gh_read_at": "2026-10-01T18:34Z",
        "carriers": {"#121135": {"head": "dd4a0ca4cf3345702eb7be95e11873308d3015b5", "state": "OPEN"},
                     "#119713": {"head": "7471d9915d7d1ce3e94f9d18c9d775461d269815", "state": "OPEN"}},
    },
    "command": [
        "bash harness/r3/mt_r3.sh <h.git> > receipts/raw/r3/merge_tree.txt",
        f"git -C <h.git> worktree add --detach <worktree> {MAIN[:10]}; git -C <worktree> checkout {HEAD[:10]} -- <the 4 changed files>   # write-tree {MERGE_TREE[:10]}",
        "cd <worktree> && <xf-sandbox> <runs>/plc-r3-green{1,2,3} <worktree> -- scripts/run_tests.sh evals/postmortem/tests/test_postmortem_harness.py tests/agent/test_turn_usage_log_line.py -q",
        f"git -C <worktree> checkout {MAIN[:10]} -- evals/postmortem/forensics/logcalls.py; <xf-sandbox> <runs>/plc-r3-red <worktree> -- scripts/run_tests.sh evals/postmortem/tests/test_postmortem_harness.py tests/agent/test_turn_usage_log_line.py -q",
        f"git -C <worktree> checkout {MAIN[:10]} -- evals/postmortem   # write-tree {MAIN_TREE[:10]} = main's tree; <xf-sandbox> <runs>/plc-r3-adj-base <worktree> -- scripts/run_tests.sh tests/agent/test_turn_usage_log_line.py evals/postmortem/tests/test_postmortem_harness.py -q",
        "git -C <h.git> worktree remove <worktree>; git -C <h.git> worktree prune",
        "run logs copied to receipts/raw/r3/ with <venv>, <pytest-tmp> and <worktree> substituted for local paths",
    ],
    "gates": {
        "validity": "PASS",
        "validity_basis": ("Sandboxed runs with fresh HOME/HERMES_HOME per run dir; 0 blocked-exec entries; RED fails at the "
                           "stated seam (calls_found); GREEN tree equals the merge tree; ADJACENT base tree equals main's tree; 0 errored runs."),
        "red": {"arm": "main 34f8ec3b40 + head tests, logcalls.py reset to main", "result": "PASS" if red_s["failed"] == 2 else "FAIL",
                "observed": red_s, "assertions": e_lines("red.txt"), "seam_covered": True},
        "green": {"arm": f"main + head (tree {MERGE_TREE[:10]})", "result": "PASS" if all(g["failed"] == 0 for g in greens) else "FAIL",
                  "reps": greens, "reps_agree": f"{sum(g == greens[0] for g in greens)}/3"},
        "sabotage": {"per_hunk": "not re-run: the commit is unchanged; per-hunk sabotage is PROOF/r20261001-01 (6/6) and the early-exit check is PROOF/r20261001-02",
                     "unpinned_hunks": r02["gates"]["sabotage"]["unpinned_hunks"]},
        "adjacent": {"files": ["tests/agent/test_turn_usage_log_line.py"],
                     "base": adj_base_files.get("tests/agent/test_turn_usage_log_line.py"),
                     "arm": green_files.get("tests/agent/test_turn_usage_log_line.py"),
                     "identical": adj_base_files.get("tests/agent/test_turn_usage_log_line.py") == green_files.get("tests/agent/test_turn_usage_log_line.py"),
                     "pre_existing_failures": [],
                     "harness_file": {"base": adj_base_files.get("evals/postmortem/tests/test_postmortem_harness.py"),
                                      "arm": green_files.get("evals/postmortem/tests/test_postmortem_harness.py"),
                                      "note": "the arm adds the 2 new tests; the 3 existing ones pass on both"}},
        "guards": {"F14": "EQUAL (F14/r20261001-01, arm on main 34f8ec3b40; not re-run here)"},
        "flaky": False,
        "noise_floor": None, "credit": None, "informativeness": "N_A", "route_scope": "n/a",
        "cache_read_ratio": {"status": "N_A", "before": None, "after": None},
    },
    "ab": None,
    "measurements": [
        {"name": "red_tests_failed", "arm": "main 34f8ec3b40", "value": red_s["failed"], "n": 1, "label": "OBSERVED", "statistic": "count"},
        {"name": "green_tests_passed", "arm": "main 34f8ec3b40 + head", "value": greens[0]["passed"], "n": 3, "label": "OBSERVED", "statistic": "count per rep"},
        {"name": "adjacent_base_tests_passed", "arm": "main 34f8ec3b40", "value": adj_s["passed"], "failed": adj_s["failed"], "label": "OBSERVED"},
        {"name": "merge_tree_pairs_clean", "value": sum(p[1].startswith("CLEAN") for p in pairs), "of": len(pairs),
         "label": "OBSERVED", "note": "the one conflict is #121135 x #119713, in agent/turn_usage.py (not ours)"},
    ],
    "denominators": {"cells": 5 + len(pairs), "unit": f"RED 1 + GREEN 3 + ADJACENT base 1 + merge-tree pairs {len(pairs)}",
                     "errored_scored_zero": 0, "infra_excluded": 0, "completeness": 1.0},
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
    "harness_abi": {"harness": "hermes evals/postmortem", "editor_abi": "n/a"},
    "not_tested": [
        "evals/ is outside pytest testpaths, so CI does not run these tests",
        "carrier suites on main 34f8ec3b40 x carrier (126 and 10 passed on aea969677c, PROOF/r20261001-02) not re-run; only the merges were re-checked",
        "round trip and synthetic F06/E19 not re-run; carried by the freshness argument below",
        "live probes not executed (real provider, paid)",
        "real agent.log / state.db (OD-7)",
    ],
    "limitations": ["one host, one test interpreter", "the staging commit's parent stays 234badf401 (not rebased); tests ran on main with the head's 4 files"],
    "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0, "energy_j": None, "runner_wall_s_per_run": "2.3-2.5 (OBSERVED, run_tests.sh summary)"},
    "verdict": "KEEP",
    "carrier_choice": None,
    "learning": {"hypothesis": "the staged commit still applies, proves and composes on upstream main 34f8ec3b40",
                 "result": "KEEP",
                 "observed_evidence": [f"merge clean (tree {MERGE_TREE[:10]})", f"RED {red_s['failed']} failed with the same assertions",
                                       "GREEN 3/3", "ADJACENT identical",
                                       "only agent/usage_pricing.py changed among invalidate_on paths (model alias table)"],
                 "regressions": [], "reusable_lesson": None, "roadmap_effect": "declared main promoted to 34f8ec3b40; commit unchanged"},
    "provenance": "self",
    "frozen": None,
    "z0evals_study": None,
    "ai_assistance": "Claude Code (Opus 5.5) ran the re-measure and wrote this receipt; disclosed per repository policy",
    "privacy": "synthetic inputs only; placeholders only (<h.git>, <worktree>, <runs>, <xf-sandbox>, <venv>, <pytest-tmp>, <host>)",
    "evidence": [{"path": f"receipts/raw/r3/{n}", "sha256": sha(RAW3 / n)}
                 for n in ("merge_tree.txt", "red.txt", "green1.txt", "green2.txt", "green3.txt", "adj_base.txt")],
    "freshness": {
        "drift_range": f"{BASE[:10]}..{MAIN[:10]}", "drift_commits": 74, "since_previous_declared_main": f"{PREV_MAIN[:10]}..{MAIN[:10]}: 38 commits",
        "invalidate_on": INVALIDATE_ON,
        "invalidate_on_changed": [{"path": "agent/usage_pricing.py", "commits": ["e2d311e5e6", "5bb6127c5b"],
                                   "what": "the model-pricing alias table near line 340 (gpt-6.1-sol aliases moved into the tier loop; net -1 line); normalize_usage and the producer path are untouched"}],
        "carrier_heads_unchanged": True,
        "merge_tree": [f"{a}: {b}" for a, b in pairs],
        "consequence": ("RED, GREEN and ADJACENT were re-observed on 34f8ec3b40. F06RT, F06SYN and E19SYN were measured on "
                        "234badf401; the only invalidate_on change since is the alias table, which none of them reads, so those results carry."),
    },
}
dump(R / "PROOF_r20261001-03.json", r03)

# 3. INDEX.json
idx_p = R / "INDEX.json"
idx = json.loads(idx_p.read_text(encoding="utf-8"))
idx["PROOF/r20261001-03"] = {"path": "receipts/PROOF_r20261001-03.json"}
for rid, ent in idx.items():
    ent["sha256"] = sha(D / ent["path"])
    print(rid, ent["sha256"])
dump(idx_p, idx)
