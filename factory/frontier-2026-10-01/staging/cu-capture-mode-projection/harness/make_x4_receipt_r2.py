"""Build the X4 r2 receipt (staging fix round 2) from a run_stfix_r2.sh output directory (stdlib only).

Usage: make_x4_receipt_r2.py <run dir> <receipt path> <run id>
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

FILE_LINE = re.compile(r"[✓✗] (tests/\S+\.py) \(([^)]*)\)")
SUMMARY = re.compile(r"=== Summary: (\d+) files?, (\d+) tests passed, (\d+) failed(?:, (\d+) skipped)?")
FAILED = re.compile(r"^FAILED (tests/\S+)")
HERE = pathlib.Path(__file__).resolve().parent
GUARD = "test_som_and_drivers_without_the_selector_keep_the_full_request"

MUTANTS = {
    "mut-title": "_tree_and_title: structuredContent.window_title fallback disabled",
    "mut-guard": "_gws_args: capabilities_discovered guard removed",
    "mut-gate-vision": "_gws_args: vision branch no longer sets include_accessibility_tree=False",
    "mut-gate-ax": "_gws_args: ax branch no longer sets include_screenshot=False",
    "mut-vision-mcp": "_capture_vision: MCP get_window_state call sends _gws_args() instead of _gws_args('vision')",
    "mut-vision-cli": "_capture_vision: CLI re-fetch sends _gws_args() instead of _gws_args('vision')",
    "mut-ws-mode": "_capture_window_state: _fetch_or_refetch sends _gws_args() instead of _gws_args(mode)",
    "mut-capture-mode": "capture(): calls _capture_window_state() without the mode",
}
GUARD_MUTANTS = {
    "guard-schema-blind": "_gws_args: both supports_input_property(...) calls replaced by True (gate ignores the schema)",
    "guard-som-selector": "_gws_args: the ax branch also fires for som (som sends include_screenshot=False)",
}
SUITES = {
    "tests/tools/test_computer_use_capture_lane_schema.py": "fold-in",
    "tests/tools/test_computer_use_cheap_lanes.py": "carrier",
    "tests/tools/test_computer_use_ax_walk_bound.py": "ax_walk_bound",
}


def parse(log: pathlib.Path) -> dict:
    text = log.read_text(encoding="utf-8", errors="replace")
    files = {}
    for m in FILE_LINE.finditer(text):
        detail = m.group(2)  # e.g. "10✓ 3✗, 5.4s" or "8s, 0.6s" (8 skipped; the duration always has a decimal)
        counts = [int(x.group(1)) if (x := re.search(rx, detail)) else 0
                  for rx in (r"(\d+)✓", r"(\d+)✗", r"(?<![\d.])(\d+)s(?![\d.])")]
        files[pathlib.Path(m.group(1)).name] = counts  # [passed, failed, skipped]
    s = SUMMARY.search(text)
    assert s, f"no summary line in {log}"
    total = {"files": int(s.group(1)), "passed": int(s.group(2)), "failed": int(s.group(3)),
             "skipped": int(s.group(4) or 0)}
    failed = sorted({m.group(1) for line in text.splitlines() if (m := FAILED.match(line.strip()))})
    return {"total": total, "files": files, "failed_tests": failed}


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    run, receipt, run_id = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
    logs = {p.stem: parse(p) for p in sorted(run.glob("*.log"))}
    foldin, main_sha, carrier, donor, prev = (run / "revisions").read_text().split()

    def reps(prefix: str) -> list:
        return [logs[k] for k in sorted(logs) if k.startswith(prefix + ".contract.r")]

    def caught_by(entry: dict) -> list:
        return sorted({SUITES.get(t.split("::")[0], t.split("::")[0]) for t in entry["failed_tests"]})

    def guard_failures(entry: dict) -> list:
        return [t.split("::")[1] for t in entry["failed_tests"] if GUARD in t]

    def summary(entry: dict) -> dict:
        return {"total": entry["total"], "failed_tests": entry["failed_tests"],
                "guard_cases_failed": guard_failures(entry)}

    sabotage = {}
    for name, what in MUTANTS.items():
        entry = logs[f"{name}.contract.r1"]
        sabotage[name] = {"mutation": what, "caught_by": caught_by(entry), "failed_tests": entry["failed_tests"],
                          "total": entry["total"]}
    unpinned = [n for n, v in sabotage.items() if "fold-in" not in v["caught_by"]]
    guard_mutants = {name: {"mutation": what, "caught_by": caught_by(logs[f"{name}.contract.r1"]),
                            **summary(logs[f"{name}.contract.r1"])} for name, what in GUARD_MUTANTS.items()}
    adjacent_files = (run / "adjacent.files").read_text().split()

    body = {
        "schema": "xf.receipt.v1",
        "staging": "cu-capture-mode-projection",
        "issue": "kvnloo/hermes-agent#316",
        "origin_refs": ["NousResearch/hermes-agent#126447", "NousResearch/hermes-agent#113389",
                        "NousResearch/hermes-agent#112639", "NousResearch/hermes-agent#126449"],
        "base_revision": main_sha,
        "head_revision": foldin,
        "supersedes": f"X4-stfix-reproof/r20261001-01 (head {prev}) for the current head",
        "provenance": "self",
        "privacy": "public-aggregate",
        "ai_assistance": "Claude Code (Opus 5.5) wrote the harness and the contract test; disclosed per repository policy",
        "env": {"host": "<local-host>", "python_tests": "3.11.14 (venv interpreter, read-only)",
                "sandbox": "scripts/run_tests.sh -j 2 with scratch HOME and HERMES_HOME; no live or integration tests",
                "network": "none used by any test cell"},
        "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0},
        "id": run_id,
        "tier": "T1",
        "question": ("After the guard test stopped comparing the request with a hard-coded dict (it now asserts that "
                     "no request carries either selector), does the fold-in still go RED on current main and GREEN "
                     "with the carrier, does the guard ignore unrelated growth of the base request, does it still "
                     "catch a gate that sends a selector it should not, which carrier hunks does each suite pin, "
                     "and do all tests/tools/test_computer_use*.py files pass the same with the carrier as on main?"),
        "arms": {
            "main": {"tree": f"{main_sha} + fold-in {foldin}"},
            "c126447": {"pr": 126447, "author": "MwC-Trexx", "head": carrier,
                        "applied": "git diff 105568c155..8891ff469a as a working-tree change on the fold-in commit"},
            "neg": "c126447 with both selector assignments replaced by pass",
            "seam": "c126447 with _CuaDriverSession.supports_input_property returning False",
            "mut-*": "c126447 with exactly one production hunk reverted (see sabotage)",
            "xarg": "c126447 with args['max_depth'] = 64 added to _gws_args (unrelated base-request growth)",
            "xarg-main": "main with the same unrelated argument",
            "xarg-prevtest": f"xarg, run with the previous fold-in's test file from {prev}",
            "guard-*": "c126447 whose gate sends a selector it should not (see guard_mutants)",
            "donor": {"head": donor, "note": "closed NousResearch/hermes-agent#113389; only ax_walk_bound run"},
            "carrier-head": f"unmodified {carrier} checked out, fold-in file from {foldin} added",
        },
        "inputs": {"harness": {f"harness/{n}": sha(HERE / n) for n in
                               ("run_stfix_r2.sh", "make_x4_receipt_r2.py", "sanitize_raw.py")}},
        "command": ("TESTHOME=<scratch home> HERMES_PYTHON=<venv python> harness/run_stfix_r2.sh <worktree at the "
                    "fold-in commit> raw/<run dir> 3; harness/sanitize_raw.py raw/<run dir>; "
                    "python3 -B harness/make_x4_receipt_r2.py raw/<run dir> <receipt> <run id>"),
        "label": "OBSERVED",
        "raw_dir": f"raw/{run.name}",
        "measurements": {
            "red_main": [r["total"] for r in reps("main")],
            "red_main_failed_tests": reps("main")[0]["failed_tests"],
            "green_c126447": [r["files"] for r in reps("c126447")],
            "green_carrier_head": [r["files"] for r in reps("carrier-head")],
            "negative_control": [{"files": r["files"], "failed_tests": r["failed_tests"]} for r in reps("neg")],
            "seam_sabotage": [{"files": r["files"], "failed_tests": r["failed_tests"]} for r in reps("seam")],
            "guard_unrelated_arg": {
                "c126447": [summary(r) for r in reps("xarg")],
                "main": summary(logs["xarg-main.contract.r1"]),
                "previous_fold_in_test": summary(logs["xarg-prevtest.contract.r1"]),
            },
            "donor_ax_walk_bound": logs["donor.ax_walk_bound"],
            "adjacent": {"files_run": adjacent_files, "main": logs["main.adjacent"],
                         "c126447": logs["c126447.adjacent"]},
        },
        "sabotage": sabotage,
        "unpinned_by_fold_in": unpinned,
        "guard_mutants": guard_mutants,
        "not_tested": ["F14 standing regression set (factory Wave 0 not built)", "full test suite",
                       "real driver replies past the target check (no display)", "tests/computer_use/ package"],
    }
    receipt.write_text(json.dumps(body, indent=2, sort_keys=False, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"unpinned_by_fold_in": unpinned,
                      "caught": {n: v["caught_by"] for n, v in sabotage.items()},
                      "guard_mutants": {n: v["guard_cases_failed"] for n, v in guard_mutants.items()},
                      "guard_unrelated_arg": {k: (v["guard_cases_failed"] if isinstance(v, dict)
                                                  else [x["guard_cases_failed"] for x in v])
                                              for k, v in body["measurements"]["guard_unrelated_arg"].items()}},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
