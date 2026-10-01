"""Aggregate the per-spec gate receipts into F11 and E30-lite experiment receipts (T1, $0, OBSERVED).

    python summarize.py <runner commit> <pass label>

Round 1 (verifier findings): adds the pre-registered gate-level match, a discrimination note per negative and the
caveats on the calibration claim; the per-spec receipts are pass 3 on the amended runner, specs unchanged since pass 2.
Round 2: pass 4 on runner 2a4253258b (docstring and commit message only vs pass 3's c430541d16; guard code byte-identical),
the F11-N2 note corrected (the graded change is the first 8 of NousResearch/hermes-agent#123635's 9 commits), no local paths.
Round 3: pass 5 on runner 732919ad7d (re-applied onto main 44a1ce9724). The Relay pin cell now counts in the receipt (its
blocked attempts taint the run; one more cell per run past the canary) and resolves only the arm's own agent/relay_runtime.py.
"""
import hashlib, json, sys, tomllib
from datetime import datetime, timezone
from pathlib import Path

STAGE = Path(__file__).resolve().parents[1]
R, SPECS = STAGE / "receipts", STAGE / "specs"
RUNNER, PASS = sys.argv[1], sys.argv[2]
REFUSED = lambda r: r["verdict"] not in ("KEEP", "PARTIAL")  # noqa: E731
FOUR = ("red", "green", "sabotage", "adjacent")


def row(name, spec_file):
    path = R / f"{name}.json"
    r = json.loads(path.read_text())
    spec = tomllib.loads((SPECS / spec_file).read_text())
    gates = {g: r["gates"].get(g, {}).get("result") for g in ("validity", *FOUR, "ownership")}
    under = {g: r["gates"][g]["underlying"]["result"] for g in FOUR if "underlying" in r["gates"].get(g, {})}
    return {"spec": r["spec"]["id"], "rev": r["spec"]["rev"], "receipt": f"receipts/{path.name}",
            "receipt_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "base": r["base_revision"][:10],
            "head": r["head_revision"][:10], "pre_registered": spec.get("expected"), "verdict": r["verdict"],
            "refused": REFUSED(r), "four_columns_pass": all(gates[g] == "PASS" for g in FOUR), "gates": gates,
            "underlying_when_infra": under, "cells": r["denominators"]["cells"], "infra_cells": r["denominators"]["infra"],
            "egress_blocked": r["safety"]["egress_blocked"], "wall_s": r["resource_usage"]["wall_s"]}


now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
common = {"schema": "xf.experiment.v1", "tier": "T1", "cost_usd": 0, "label": "OBSERVED",
          "runner_commit": RUNNER, "pass": PASS, "specs_base_main": "572e4f4fad32bbdcfc948fb2ec833177ed5734c0 (the specs' pin; not current main)",
          "command": "W=<runner-wt> XF_REPO=<repo.git> XF_PYTHON=<venv-python> HOME=<test-home> specs/run_all.sh <spec ids>  "
                     "(python -m evals._factory.gate_runner run --work-order specs/<id>.wo.json --repo <repo.git> "
                     "--scratch <scratch> --python <venv-python> --out receipts/<id>.json)"}

pos = [row("F11-P1-fork50", "F11-P1-fork50.toml"), row("F11-P2-fork112-r2", "F11-P2-fork112.r2.toml"),
       row("F11-P3-fork47v2", "F11-P3-fork47v2.toml")]
neg = [row("F11-N1-noop-revert", "F11-N1-noop-revert.toml"), row("F11-N2-review-fix", "F11-N2-review-fix.toml"),
       row("F11-N3-fork111-conflict", "F11-N3-fork111-conflict.toml")]
EXPECT_GATE = {"F11-N1-noop-revert": ("red", "FAIL", "no_repro_on_base"), "F11-N2-review-fix": ("green", "FAIL", "not_fixed"),
               "F11-N3-fork111-conflict": ("validity", "FAIL", "conflicting")}
DISCRIMINATION = {
    "F11-N1-noop-revert": "none: refused only as INFRA (every cell's test resolves openrouter.ai, see FINDING); the pre-registered refusal was RED no_repro_on_base, which the guard-tainted cells cannot certify",
    "F11-N2-review-fix": "trivial: base a7c2df3846 (the commit NousResearch/hermes-agent#123635 landed on) to head ac0b07597d is the first 8 of the PR's 9 commits, ending in write-path hardening; they never attempted the read-path defect that the 9th commit 8ded06be29's tests pin, so any red/green check refuses them; it does exercise tests_from injection into head",
    "F11-N3-fork111-conflict": "pre-gate: refused at materialization by a merge-tree conflict; no gate ran",
}
for n in neg:
    gate, result, reason = EXPECT_GATE[n["spec"]]
    r = json.loads((STAGE / n["receipt"]).read_text())
    g = r["gates"].get(gate, {})
    n["pre_registered_gate_match"] = g.get("result") == result and g.get("reason") == reason
    n["discrimination"] = DISCRIMINATION[n["spec"]]
for p in pos:
    p["pre_registered_gate_match"] = p["verdict"] == "KEEP" and p["four_columns_pass"]
f11 = {**common, "id": f"F11/r{now}", "question": "Does the runner reproduce RED/GREEN/negative/adjacent on 3 READY branches re-based on main 572e4f4fad, and refuse 3 known-bad candidates?",
       "results": {"known_good_four_columns_pass": f"{sum(p['four_columns_pass'] for p in pos)}/3",
                   "known_good_keep": f"{sum(p['verdict'] == 'KEEP' for p in pos)}/3",
                   "known_bad_refused": f"{sum(n['refused'] for n in neg)}/3",
                   "false_ready": sum(not n["refused"] for n in neg),
                   "classifications_matching_keep_vs_refused": f"{sum(p['verdict'] == 'KEEP' for p in pos) + sum(n['refused'] for n in neg)}/6",
                   "classifications_matching_pre_registered_gate": f"{sum(x['pre_registered_gate_match'] for x in pos + neg)}/6",
                   "known_bad_with_non_trivial_gate_discrimination": "0/3"},
       "positives": pos, "negatives": neg,
       "history": {"pass1": {"receipts": "receipts/pass1/", "runner_commit": "b01d6dcb8b",
                             "findings": ["F11-N2 falsely accepted (PARTIAL): tests from inject.tests_from were applied to base only, so head was graded on its own weaker test -> runner fixed after pass 1 (head gets them too) and pinned by the unit test",
                                          "F11-P2 rev 1 refused a known-good item: its marker quoted the untruncated repr but pytest -q prints ('killed', 'p...ss.kill', -15) -> spec rev 2 written after pass 1 (04:25 vs 04:17)",
                                          "E30-N1 BLOCKED by the exec denylist on a docstring mentioning execvp -> denylist now matches call syntax only",
                                          "Relay pin probe crashed on an installed-but-incompatible nemo_relay -> recorded as an error field"]},
                   "pass2": {"receipts": "receipts/pass2/ (F11-N1 and E30-N1 kept local only: their Relay error carried an absolute run-directory path)",
                             "runner_commit": "be292fd2ba"},
                   "pass3": {"receipts": "receipts/pass3/", "runner_commit": "c430541d16",
                             "change": "amended runner (shell-text exec guard, PATH shim, Relay pin path scrub, absolute-path validator rule, spec-relative sabotage patch); specs unchanged since pass 2"},
                   "pass4": {"receipts": "receipts/pass4/", "runner_commit": "2a4253258b", "change": "round 2: docstring and commit message only (the exec guard's word-match limits stated); guard code byte-identical to pass 3; re-applied onto main e8c97320ac; specs unchanged since pass 2"},
                   "pass5": {"runner_commit": RUNNER, "change": "round 3: the Relay pin cell is folded into the receipt (its blocked attempts count in the safety counters and denominators, and any INFRA cell makes the run INFRA), and the pin resolves only the head arm's own agent/relay_runtime.py; re-applied onto main 44a1ce9724; specs unchanged since pass 2"}},
       "verdict": "6/6 at the KEEP/refused level, false-READY 0; WEAK as calibration (see caveats)",
       "caveats": ["no known-bad candidate shows non-trivial gate discrimination: N1 refused only as INFRA, N2 trivially, N3 before any gate ran",
                   "pre-registered gate-level match is 5/6: F11-N1 was pre-registered 'refused at RED (no_repro_on_base)' and observed INFRA (underlying RED FAIL no_repro_on_base, but from guard-tainted cells)",
                   "the specs are not all pre-registered before pass 1: F11-P2 rev 2 (its RED marker) was rewritten after pass 1 refused rev 1",
                   "the runner was changed after pass 1 so that N2 would be refused (tests_from injected into head)",
                   "no held-out set: every calibration item was seen while the runner was being fixed",
                   "ownership verdicts were recorded inputs from the 2026-09-30 readiness verdicts, not re-searched by the runner"]}
(R / "F11-runner-calibration.json").write_text(json.dumps(f11, indent=1) + "\n")

e_pos = [row("E30-P1-8ded06be29", "E30-P1-8ded06be29.toml")]
e_neg = [row("E30-N1-79dbb1450e", "E30-N1-79dbb1450e.toml"), neg[0]]
e30 = {**common, "id": f"E30-lite/r{now}", "question": "Do the red/green/sabotage/adjacent gates separate a merged upstream fix from later-reverted human patches?",
       "results": {"positives_four_columns_pass": f"{sum(p['four_columns_pass'] for p in e_pos)}/{len(e_pos)}",
                   "negatives_refused": f"{sum(n['refused'] for n in e_neg)}/{len(e_neg)}",
                   "false_credit_on_negatives": f"{sum(not n['refused'] for n in e_neg)}/{len(e_neg)}",
                   "n": len(e_pos) + len(e_neg)},
       "positives": e_pos, "negatives": e_neg,
       "pass": PASS,
       "reading": "79dbb1450e (NousResearch/hermes-agent#124792) passes all four columns: its own tests pin the new PATH order, and the reason it was reverted (a later PATH entry shadowing earlier ones for the child's other lookups) has no test. Red/green gates certify the claim a patch tests, not the invariants it breaks elsewhere.",
       "verdict": "UNINFORMATIVE for the kill switch (n=3 < pre-registered minimum); one concrete false credit recorded",
       "not_tested": ["evolver.calibrate (20eb166106) synthetic-negative harness", "a reverted-PR battery of >= 10 negatives"]}
(R / "E30-gate-calibration-lite.json").write_text(json.dumps(e30, indent=1) + "\n")
print(json.dumps(f11["results"]), "\n", json.dumps(e30["results"]))
