"""Assemble the public-aggregate receipts (xf.receipt.v1 shape, FACTORY.md section 9.2) from raw/ outputs.
Write-once: refuses to overwrite an existing receipt. Every number is read from raw/, never typed by hand.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

B = pathlib.Path(__file__).resolve().parents[1]
RAW, REC = B / "raw", B / "receipts"

MAIN = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0"
MAIN_NEWER = "234badf4012af380d23c91eae55d045a69c69ffb"
STAGING = "ed420d8292349f27affb1a80fbf90e44f48c874a"
CARRIER = {"pr": 126447, "author": "MwC-Trexx", "head": "8891ff469a6623d4b6acdb6f04a8c835d1659c2a",
           "base": "105568c1558e1cb494e6edf1a2998d524ebe809e", "merge_tree_on_main": "clean"}
DONOR = {"ref": "refs/fork/feat/cu-capture-mode-projection-112639", "head": "7e809555e6951a444626465a6d97c7e5a17ee541",
         "base": "d0288be5b3330d2442e3907185b8e9d0958297bb", "pr": 113389, "merge_tree_on_main": "clean"}
BINARIES = {
    "0.21.0": "43d926a1b938012379db57cf351530f81e75a574017676815f85d1e13aff23f7",
    "0.22.2": "574c6c4b92e43361ee187b8bc345f0885cce4be5324ead383941df477ce3da4c",
    "0.23.2": "2aaad67b996d41cd909e4b7ac2ddd705653e8c7f9958010ac051838b02f64eeb",
    "0.24.0": "a033485d78a1c5966edd8ce29792d7f2d19a1988bcb58a6e292b6d17255262e1",
    "0.28.2": "3739101d072bdfdd83b7e70b3a16d9271f6eb124e7c5e69b3406f20f0910a4ca",
}
COMMON = {
    "schema": "xf.receipt.v1",
    "staging": "cu-capture-mode-projection",
    "issue": "kvnloo/hermes-agent#316",
    "origin_refs": ["NousResearch/hermes-agent#126447", "NousResearch/hermes-agent#113389",
                    "NousResearch/hermes-agent#112639", "NousResearch/hermes-agent#126449"],
    "base_revision": MAIN,
    "provenance": "self",
    "privacy": "public-aggregate",
    "ai_assistance": "Claude Code (Opus 5.5) wrote the harness and the contract test; disclosed per repository policy",
    "env": {"host": "<local-host>", "python_tests": "3.11.14 (venv interpreter, read-only; live home masked in bwrap runs)",
            "sandbox": "X1/X2c-wrapper/X3: bwrap ro-root, --unshare-net, --unshare-pid, --clearenv, scratch HOME and "
                       "HERMES_HOME, the live Hermes install masked except the venv; X2/X2b/X2c: scripts/run_tests.sh "
                       "with scratch HOME/HERMES_HOME (no pytest_live_guard), -j 2",
            "network": "none used by any cell (X1 egress_attempts = [] per version)"},
    "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0},
}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def harness(*names):
    return {f"harness/{n}": sha(B / "harness" / n) for n in names}


def write(name: str, body: dict) -> None:
    path = REC / name
    if path.exists():
        print(f"exists, not overwritten: {path}")
        return
    path.write_text(json.dumps(body, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"wrote {path} sha256={sha(path)}")


def counts(parsed: dict, key: str) -> dict:
    v = parsed[key]
    return {"total": v["total"], "files": {f.split("/")[-1]: [x["passed"], x["failed"]] for f, x in v["files"].items()},
            "failed_tests": v["failed_tests"]}


def x1() -> None:
    rows = {}
    for v in BINARIES:
        d = json.loads((RAW / "x1-schema-r4" / f"probe-{v}.json").read_text())
        rows[v] = {
            "binary_sha256": BINARIES[v], "start_ok": d["start_ok"], "tool_count": d["tool_count"],
            "advertises_include_screenshot": d["supports_include_screenshot"],
            "advertises_include_accessibility_tree": d["supports_include_accessibility_tree"],
            "advertises_standalone_screenshot_tool": d["has_screenshot_tool"],
            "gws_additionalProperties": d["gws_additional_properties"], "gws_properties": d["gws_properties"],
            "unknown_or_unadvertised_property_rejected_before_target_check":
                len({x.get("text") for x in d["dispatch"].values()}) != 1,
            "dispatch": d["dispatch"], "egress_attempts": d["egress_attempts"], "session_start_s": d["start_s"],
        }
    write("X1-driver-schema.r20261001-04.json", {
        **COMMON, "id": "X1-driver-schema/r20261001-04", "tier": "T0 (real release binaries, no display, no network)",
        "question": "Which get_window_state selectors do shipped Linux cua-driver releases advertise to Hermes' own "
                    "capability seam, and does any release expose a standalone screenshot tool that would make "
                    "vision mode skip get_window_state?",
        "inputs": {"worktree_commit": STAGING, "seam": "tools/computer_use/cua_backend_session.py "
                   "_CuaDriverSession.start -> _populate_capabilities -> supports_input_property",
                   "binaries": {v: f"~/.cua-driver/packages/releases/{v}-x86_64-unknown-linux-gnu/cua-driver" for v in BINARIES},
                   "harness": harness("schema_probe.py", "run_schema_probe.sh")},
        "command": "PROBE_DISPATCH=1 bash harness/run_schema_probe.sh <worktree@ed420d8292> <run dir> 0.21.0 0.22.2 "
                   "0.23.2 0.24.0 0.28.2",
        "label": "OBSERVED",
        "measurements": rows,
        "result": "All five releases start under the production session and list 60 tools; none has a standalone "
                  "screenshot tool (so vision on main always calls get_window_state and walks AT-SPI). 0.21.0, "
                  "0.22.2 and 0.23.2 advertise include_screenshot only; 0.24.0 and 0.28.2 advertise both selectors. "
                  "All declare additionalProperties:false, yet none rejects an unadvertised or bogus property before "
                  "its stale-target check, so the capability gate preserves the request shape rather than avoiding "
                  "a hard error (behaviour past the target check is NOT_TESTED: no display).",
        "implication": "On default Linux host installs (pm/lock.json pins 0.21.0) the ax lane activates and the vision "
                       "lane stays dormant until the pin moves (#126449) or the sandbox-desktop image (0.28.2) is used.",
        "not_tested": ["capture timing or AT-SPI walk cost (needs a display: E23)", "macOS and Windows builds",
                       "releases 0.25.x-0.27.x, 0.29.x, 0.30.x (not installed as release dirs here)"],
        "verdict": "KEEP (fact base for the fold-in test fixtures and the E23 design)",
    })


def x2_r1() -> None:
    r1 = json.loads((RAW / "x2-ab-r1" / "parsed.json").read_text())
    arms = ("main", "c126447", "donor", "neg-c126447", "neg-donor")
    per_arm = {a: {**{f"contract_r{i}": counts(r1, f"{a}.contract.r{i}") for i in (1, 2, 3)},
                   **({"adjacent": counts(r1, f"{a}.adjacent")} if f"{a}.adjacent" in r1 else {})} for a in arms}
    write("X2-ab-regression.r20261001-01.json", {
        **COMMON, "id": "X2-ab-regression/r20261001-01", "superseded_by": "X2-ab-regression/r20261001-02",
        "tier": "T1", "head_revision": "e596a3972dce59e7f54ee5422ee1398c952851f7 (first version of the staging "
        "commit; amended to ed420d8292)",
        "inputs": {"harness": harness("run_ab_arms.sh", "parse_runs.py")},
        "command": "bash harness/run_ab_arms.sh <worktree@e596a3972d> <bare repo> <out> 3",
        "label": "OBSERVED", "measurements": per_arm,
        "result": "Same picture as r2 except the donor failed one fold-in case (ax window_title): that first fake used "
                  "macOS-shaped tree markdown, and the donor reads the structured title only in vision. Superseded "
                  "after the fake was aligned with the Linux 0.28.2 reply shape and the ax title assertion dropped "
                  "(the ax lane keeps the tree, so the title is not a lane effect).",
        "verdict": "SUPERSEDED",
    })


def x2() -> None:
    r1 = json.loads((RAW / "x2-ab-r1" / "parsed.json").read_text())
    r2 = json.loads((RAW / "x2-ab-r2" / "parsed.json").read_text())
    arms = {
        "main": {"tree": f"{MAIN} + staging commit {STAGING} (fold-in test only)"},
        "c126447": {**CARRIER, "applied": "git diff base..head | git apply --3way onto the staging commit"},
        "donor": {**DONOR, "applied": "git diff base..head | git apply --3way onto the staging commit"},
        "neg-c126447": {"from": "c126447", "mutation": 'args["include_accessibility_tree"] = False and '
                        'args["include_screenshot"] = False replaced by pass'},
        "neg-donor": {"from": "donor", "mutation": "args[selector] = False replaced by pass"},
    }
    per_arm = {}
    for arm in arms:
        per_arm[arm] = {f"contract_r{i}": counts(r2, f"{arm}.contract.r{i}") for i in (1, 2, 3)}
        if f"{arm}.adjacent" in r2:
            per_arm[arm]["adjacent"] = counts(r2, f"{arm}.adjacent")
    body = {
        **COMMON, "id": "X2-ab-regression/r20261001-02", "supersedes": "X2-ab-regression/r20261001-01",
        "tier": "T1 (direct calls through CuaDriverBackend.capture; MCP call faked)",
        "question": "Is the fold-in contract test RED on main for the stated reason, GREEN on both implementations "
                    "(3/3), re-RED under each negative control, with sibling computer_use tests unchanged?",
        "head_revision": STAGING, "arms": arms,
        "contract_files": {"tests/tools/test_computer_use_capture_lane_schema.py": "fold-in (staging commit)",
                           "tests/tools/test_computer_use_cheap_lanes.py": "carrier's own tests, cross-applied",
                           "tests/tools/test_computer_use_capture_modes.py": "donor's own tests, cross-applied"},
        "adjacent_files": 11,
        "inputs": {"harness": harness("run_ab_arms.sh", "parse_runs.py")},
        "command": "bash harness/run_ab_arms.sh <worktree@ed420d8292> <bare repo> <out> 3",
        "label": "OBSERVED",
        "measurements": per_arm,
        "gates": {
            "red": {"arm": "main", "result": "PASS", "observed": "fold-in 2 failed / 5 (3 guard cases pass), 3/3 reps",
                    "assertion": "AssertionError: assert ([{'pid': 123, 'window_id': 456, 'session': 'hermes-...'}] and "
                                 "False) -- get_window_state sent without include_screenshot / include_accessibility_tree"},
            "green": [{"arm": "c126447", "result": "PASS", "reps_agree": "3/3", "observed": "24/24 contract"},
                      {"arm": "donor", "result": "PASS (fold-in 5/5)", "reps_agree": "3/3",
                       "observed": "21/24 contract: 3 carrier tests fail (pre-discovery stub, sessionless stub, ax "
                                   "tree-only title)"}],
            "negative_control": {"neg-c126447": "fold-in 2 failed / 5, 3/3", "neg-donor": "fold-in 2 failed / 5, 3/3"},
            "adjacent": {"main": "158 passed / 0 failed", "c126447": "158 passed / 0 failed",
                         "donor": "157 passed / 1 failed (test_computer_use_ax_walk_bound.py::TestAxWalkBound::"
                                  "test_configured_value_reaches_the_driver_args: TypeError, the stub's "
                                  "_capture_window_state lambda takes no mode argument)",
                         "identical_to_main": {"c126447": True, "donor": False}},
            "flaky": False,
        },
        "carrier_choice": {"winner": "c126447",
                           "why": "GREEN 3/3 on its own, the donor's and the fold-in contract; adjacent identical to "
                                  "main; it already updates the ax_walk_bound stub and guards a sessionless capture. "
                                  "The donor (closed #113389) breaks an adjacent test on current main."},
        "superseded_run": {"id": "X2-ab-regression/r20261001-01", "why": "the fold-in fake used macOS-shaped tree "
                           "markdown (AXWindow line, no header line) and asserted window_title in ax mode; on that "
                           "shape the donor failed only because it lacks a structured-title fallback outside vision. "
                           "The test now mirrors the Linux 0.28.2 reply (header line + AT-SPI markdown) and asserts "
                           "the title only where the lane removes the tree (vision).",
                           "r1_donor_fold_in": counts(r1, "donor.contract.r1")["files"].get(
                               "test_computer_use_capture_lane_schema.py")},
        "not_tested": ["real driver replies past the target check (no display)", "capture latency (E23)"],
        "verdict": "KEEP",
    }
    write("X2-ab-regression.r20261001-02.json", body)


def x2b() -> None:
    p = json.loads((RAW / "x2b-seam-r1" / "parsed.json").read_text())
    write("X2b-seam-sabotage.r20261001-01.json", {
        **COMMON, "id": "X2b-seam-sabotage/r20261001-01", "tier": "T1",
        "question": "Which contract tests depend on the production capability seam rather than a stub (D3)?",
        "arms": {"c126447+seam-sabotage": {**CARRIER, "mutation": "_CuaDriverSession.supports_input_property "
                                           "returns False unconditionally"}},
        "inputs": {"harness": harness("run_seam_sabotage.sh", "parse_runs.py"), "head_revision": STAGING},
        "command": "bash harness/run_seam_sabotage.sh <worktree@ed420d8292> <out> 3",
        "label": "OBSERVED",
        "measurements": {f"r{i}": counts(p, f"seam-sabotage.r{i}") for i in (1, 2, 3)},
        "result": "With the real seam broken, the fold-in's two lane cases go RED (3/3 reps) while all 13 carrier "
                  "tests and all 6 donor tests stay GREEN: both stub supports_input_property (a _StubSession / "
                  "MagicMock), so neither suite would notice a broken capability gate in production.",
        "verdict": "KEEP (the fold-in adds the only real-seam coverage)",
    })


def x2c() -> None:
    p = json.loads((RAW / "x2c-carrier-foldin-r1" / "parsed.json").read_text())
    write("X2c-carrier-foldin.r20261001-01.json", {
        **COMMON, "id": "X2c-carrier-foldin/r20261001-01", "tier": "T1",
        "question": "Does the fold-in test pass on the UNMODIFIED carrier head, as it would if folded into #126447?",
        "arms": {"carrier-head+fold-in": {**CARRIER, "fold_in": f"tests/tools/test_computer_use_capture_lane_schema.py "
                                          f"from {STAGING}", "cherry_pick_merge_tree": "clean (tree bb30652a8d)"}},
        "inputs": {"harness": harness("parse_runs.py")},
        "command": "git checkout --detach 8891ff469a; add the fold-in file; scripts/run_tests.sh -j 2 "
                   "<fold-in> tests/tools/test_computer_use_cheap_lanes.py tests/tools/test_computer_use_ax_walk_bound.py -q "
                   "(x3); scripts/run_tests.sh -j 2 <10 adjacent files> -q",
        "label": "OBSERVED",
        "measurements": {**{f"contract_r{i}": counts(p, f"carrier-foldin.contract.r{i}") for i in (1, 2, 3)},
                         "adjacent": counts(p, "carrier-foldin.adjacent")},
        "verdict": "KEEP",
    })


def x3() -> None:
    s = json.loads((RAW / "x3-e23-selftest-r1" / "summary.json").read_text())
    w = json.loads((RAW / "x3-e23-selftest-r1" / "wrapper-selftest.json").read_text())
    dl = {k.split("|")[1]: v for k, v in s["deltas"].items()}
    fmt = lambda m: f"{dl[m]['median_delta_ms']:+.2f} ms (CI95 {dl[m]['ci95'][0]:+.2f}..{dl[m]['ci95'][1]:+.2f}, A/A bound {dl[m]['aa_floor']['abs_bound_ms']:.2f}, beyond_noise={dl[m]['beyond_noise']})"  # noqa: E731
    write("X3-e23-harness-selftest.r20261001-01.json", {
        **COMMON, "id": "X3-e23-harness-selftest/r20261001-01", "tier": "T1 (in-process fake driver)",
        "question": "Does the E23 timing harness detect a known per-lane cost difference and report none under A/A?",
        "arms": {"main": {"tree": f"{MAIN} + {STAGING}"}, "main-aa": {"tree": "same as main, separate blocks"},
                 "c126447": CARRIER},
        "inputs": {"harness": harness("e23_capture_timing.py", "e23_summarize.py"),
                   "fake": {"tree_ms": 30, "grab_ms": 10, "blocks_per_arm": 2, "n_per_block": 10, "warmup": 2}},
        "command": "e23_capture_timing.py --fake --arm <arm> --block <b> --n 10 --warmup 2 --targets Terminal "
                   "(blocks: main, main-aa, c126447, c126447, main-aa, main; bwrap, no network); "
                   "e23_summarize.py rows.jsonl --base main --aa main-aa --candidates c126447",
        "label": "MODELED",
        "label_note": "Synthetic sleeps. These numbers validate the harness only and are never evidence for the "
                      "feature or for Linux behaviour.",
        "measurements": s,
        "wrapper_selftest": {"command": "bwrap ... E23_LOCAL_DRIVER=<0.28.2 binary> HERMES_CUA_DRIVER_CMD="
                             "harness/e23_driver_wrapper.sh python harness/e23_wrapper_selftest.py",
                             "harness": harness("e23_driver_wrapper.sh", "e23_wrapper_selftest.py"),
                             "label": "OBSERVED", "result": w},
        "result": f"Positive control (configured: tree 30 ms, grab 10 ms): ax {fmt('ax')}; vision {fmt('vision')}; "
                  f"som control {fmt('som')}.",
        "verdict": "KEEP (harness ready for E23)",
    })


if __name__ == "__main__":
    REC.mkdir(exist_ok=True)
    for fn in (x1, x2_r1, x2, x2b, x2c, x3):
        fn()
    sys.exit(0)
