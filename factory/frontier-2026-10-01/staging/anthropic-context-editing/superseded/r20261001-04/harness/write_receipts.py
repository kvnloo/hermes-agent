"""Derive the public xf.receipt.v1 receipts for staging/anthropic-context-editing run r20261001-04
from raw/ (no re-run). Every path written is artifact-relative or repo-relative; local paths
appear only as the placeholders <worktree>, <testhome>, <venv-python>."""
import hashlib
import json
import re
import tomllib
from pathlib import Path

A = Path(__file__).resolve().parents[1]
RAW, OUT, SPECS = A / "raw", A / "receipts", A / "specs"
RUN = "r20261001-04"
BASE = "44a1ce9724502b9c692faaef00af3054bf11f1a6"
HEAD = "05d6dbc172d24db4b237f8ef130fb4dc2e8651df"
BASE_TREE = "6a18f0eebdb6f90887fa6588781c20ec50fc6e1d"
HEAD_TREE = "2c45d3cd5381cbff8fdf95807af5b026d3b02f2c"
CHANGED_FILES = [
    "agent/agent_init.py", "agent/anthropic_adapter.py", "agent/anthropic_context_editing.py",
    "agent/chat_completion_helpers.py", "agent/transports/anthropic.py", "agent/turn_recovery.py",
    "cli-config.yaml.example", "gateway/run.py", "hermes_cli/config_defaults.py",
    "tests/agent/test_anthropic_context_editing.py", "tui_gateway/session_compression.py",
    "website/docs/developer-guide/context-compression-and-caching.md",
    "website/docs/user-guide/features/computer-use.md",
]
ENV = {"host": "<local-host>", "host_note": "name withheld, as F09 strips host facts from system prompts", "os": "Linux x86_64", "python": "3.11.14 (test venv, passed as HERMES_PYTHON)",
       "anthropic_sdk": "0.87.0", "httpx": "0.28.1", "pydantic": "2.13.4", "venv_lock_sha256": None,
       "sandbox": "no bwrap; loopback-only connect guard in the F09 probe; isolated HOME/HERMES_HOME for every run",
       "network": "loopback only"}
SUPERSEDES = {"P-redgreen": "P-redgreen/r20261001-03", "F09": "F09/r20261001-03", "G-guards": "G-guards/r20261001-03 (ran 2 F14 scripts only)"}  # kept under superseded/r20261001-03/
F14_HASH_NOTES = {  # probe id -> why its normalised output differs between arms (from the private base/head diffs)
    "token_accounting/worktree_prompt_prefix": "only prompt_sha256 differs (all char counts, offsets and stable_sha256 equal): the hashed prompt embeds the per-arm probe directory and the SHA of the fixture commit the probe creates at run time",
    "provider_fallback/probe_104120": "temp HOME name (mkdtemp suffix) and monotonic-clock deadline values",
    "provider_fallback/probe_104260": "temp HOME name (mkdtemp suffix) and remaining-seconds values",
    "postmortem/context_cap_probe": "temp HERMES_HOME name in the IDENTITY line",
    "postmortem/deadline_probe": "elapsed times and a message timestamp",
    "postmortem/goal_scope_probe": "the probe's own pid and a wall-clock wait-until timestamp",
}
# A/A check: an earlier base-only trial of the same probes (before pre-registration, same commit) differed from
# this run's base arm on the same 6 probes plus replay_gates' token counts, which depend on the length of the
# private directory path; here both arms use equal-length paths (<private>/base, <private>/head).
PREREG = json.loads((SPECS / "PREREG.json").read_text(encoding="utf-8"))
META = json.loads((RAW / "run_meta.json").read_text(encoding="utf-8"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def raw_ref(name):
    return {"path": f"raw/{name}", "sha256": sha(RAW / name)}


def cells(d):
    return {c["cell"]: c for c in d["cells"]}


def usage(prefixes):
    steps = [m for m in META["steps"] if m["step"].startswith(tuple(prefixes))]
    return {"wall_s": round(sum(m["wall_s"] for m in steps), 1), "cpu_core_s": round(sum(m["cpu_core_s"] for m in steps), 1),
            "gpu_s": 0, "energy_j": None, "tokens": 0, "api_cost_usd": 0.0,
            "steps": {m["step"]: {"wall_s": m["wall_s"], "cpu_core_s": m["cpu_core_s"]} for m in steps}}


def spec_block(sid):
    s = PREREG["specs"][sid]
    toml = tomllib.loads((A / s["path"]).read_text(encoding="utf-8"))
    assert sha(A / s["path"]) == s["sha256"], f"spec {sid} changed after pre-registration"
    return {"path": s["path"], "rev": s["rev"], "sha256": s["sha256"], "prereg_commit": None,
            "prereg_recorded_at": PREREG["recorded_at"], "decision_rule_sha": s["decision_rule_sha256"],
            "decision_rule": toml["oracle"]["decision_rule"],
            "prereg_note": "spec written and hashed before the run started (specs/PREREG.json); not committed to claude/ledger because xf is not built yet"}


def common(sid, *, cells_n, kind="mechanism", resource_prefixes=()):
    return {
        "schema": "xf.receipt.v1", "id": f"{sid}/{RUN}", "tier": "T1", "label_default": "OBSERVED",
        "spec": spec_block(sid),
        "runner_revision": {"driver": {"path": "harness/run_proofs.py", "sha256": sha(A / "harness/run_proofs.py")},
                            "test_runner": f"scripts/run_tests.sh blob 8fcc4294f4@{BASE[:10]}",
                            "receipt_writer": {"path": "harness/write_receipts.py", "sha256": sha(A / "harness/write_receipts.py")}},
        "issue": "kvnloo/hermes-agent#322",
        "origin_refs": ["NousResearch/hermes-agent#526", "NousResearch/hermes-agent#1147", "NousResearch/hermes-agent#528"],
        "staging": "anthropic-context-editing",
        "base_revision": BASE,
        "arms": {"base": {"commit": BASE, "tree": BASE_TREE},
                 "head": {"commit": HEAD, "tree": HEAD_TREE, "parent": BASE, "merge": "clean (one commit on base)"}},
        "head_revision": HEAD,
        "changed_files": CHANGED_FILES,
        "policy_revision": {"AGENTS.md": f"65aa3e61bcba610da21279a17385671263be39e9@{BASE[:10]}",
                            "CONTRIBUTING.md": f"b0baa59b5057c204b3c09d3dd170c0955cfdb39c@{BASE[:10]}",
                            ".github/PULL_REQUEST_TEMPLATE.md": f"5496eb534fef9d08c091b8186e7edd1b5cf356db@{BASE[:10]}",
                            "factory": "FACTORY.md sha256 7726ba18b43a9367f91d7f70c3aaefb96a9863761ddf71225c61c26a30d688d4 (frontier-2026-10-01)",
                            "protocol": "PROTOCOL.md sha256 182e3fbae771d7219497833b3f9d6f7ed385d70abace8736559026e4e60b90d4 (promotion-readiness-2026-10-01)"},
        "env": ENV,
        "denominators": {"cells": cells_n, "errored_scored_zero": 0, "infra_excluded": 0, "completeness": 1.0},
        "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": kind},
        "harness_abi": {"harness": "hermes", "editor_abi": "n/a",
                        "surface": "AIAgent.run_conversation; vendor HTTP boundary replaced by the in-repo SDK-oracle fake"},
        "resource_usage": usage(resource_prefixes),
        "carrier_choice": {"winner": "head (own leaf)", "why": "no open or merged implementation and no carrier; #528 was closed as superseded by #1147, which only changed beta-header/OAuth plumbing; no code reused",
                           "related_open": "NousResearch/hermes-agent#71302 (TrueNix, OPEN, CONFLICTING): on OAuth requests with thinking it sets extra_body.context_management to clear_thinking_20251015 keep all, and adds the context-management beta to _OAUTH_ONLY_BETAS; related (OAuth fingerprint parity), not an owner; see MERGE/" + RUN},
        "provenance": "self",
        "frozen": {"bundle_sha": None, "cells": cells_n, "supersedes": SUPERSEDES[sid],
                   "status": "NOT_FROZEN (P8 pending: no write-once bundle, not frozen to z0evals)"},
        "z0evals_study": {"repo": "kvnloo/z0evals", "branch": "study/hermes-anthropic-context-editing", "commit": None},
        "ai_assistance": "Claude Code (Claude Opus 5.5) wrote the change, tests and probes",
        "privacy": "public-aggregate",
    }


def write(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2) + "\n"
    for bad in [f"/{d}/" for d in ("tmp", "home", "workspace", "mnt", "Users")]:
        assert bad not in text, f"{name}: absolute path {bad!r} in receipt"
    (OUT / name).write_text(text, encoding="utf-8")


PYTEST = "HOME=<testhome> HERMES_HOME=<testhome>/.hermes HERMES_PYTHON=<venv-python> bash scripts/run_tests.sh -j 2 {files} -q"
DRIVER = (f"HERMES_PYTHON=<venv-python> XF_TESTHOME=<testhome> XF_PRIVATE=<private> python3 -B harness/run_proofs.py --worktree <worktree> "
          f"--base {BASE} --head {HEAD} --raw raw")

# ---- RED/GREEN/NEG/ADJ proof ------------------------------------------------------------------
sab = load("sabotage.json")
red_txt = (RAW / "red_base.txt").read_text(encoding="utf-8")
green = [ln for ln in (RAW / "green3.txt").read_text(encoding="utf-8").splitlines() if ln]
adj_b = (RAW / "adjacent_base.txt").read_text(encoding="utf-8").strip()
adj_h = (RAW / "adjacent_head.txt").read_text(encoding="utf-8").strip()
CASES = 7
GATE_REMOVALS = ["gate-flag", "gate-compression-enabled", "gate-checkpoint-required", "gate-claude-model", "gate-third-party-endpoint"]
red_m = re.search(r"Summary: \d+ files, (\d+) tests passed, (\d+) failed", red_txt)
red_passed, red_failed = int(red_m.group(1)), int(red_m.group(2))
markers = ["assert 'context-management-2025-06-27' in ['interleaved-thinking-2025-05-14', 'fine-grained-tool-streaming-2025-05-14']",
           "assert [False, False] == [True, False, False]"]
markers_found = [m for m in markers if m in red_txt]
green_ok = len(green) == 3 and all(re.search(rf"{CASES} tests passed, 0 failed", g) for g in green)
strip_t = lambda s: re.sub(r" in [0-9.]+s.*", "", s)  # noqa: E731
adj_identical = strip_t(adj_b) == strip_t(adj_h)
contract_rows = [s for s in sab if s["kind"] != "adjacent"]
adjacent_rows = [s for s in sab if s["kind"] == "adjacent"]
pinned = [s for s in contract_rows if s.get("re_red")]
gate_removals_red = all(next(s for s in sab if s["id"] == g)["re_red"] for g in GATE_REMOVALS)
adjacent_files = ["tests/agent/test_anthropic_adapter.py", "tests/hermes_cli/test_fast_command.py", "tests/agent/test_fast_mode_auto.py",
                  "tests/agent/test_native_compaction.py", "tests/agent/test_nous_portal_anthropic_wire.py", "tests/gateway/test_agent_cache.py",
                  "tests/tui_gateway/test_compression_config_hot_reload.py", "tests/hermes_cli/test_config_edit_seed.py",
                  "tests/hermes_cli/test_config_unversioned_migration.py", "tests/agent/test_413_compression.py",
                  "tests/agent/transports/test_transport.py", "tests/agent/test_anthropic_stream_fallbacks.py",
                  "tests/agent/test_codex_token_expired_replay_recovery.py", "tests/agent/test_error_classifier.py",
                  "tests/e2e/core/providers/test_anthropic_oracle.py"]
proof_keep = (red_failed == 2 and red_passed == CASES - 2 and len(markers_found) == 2 and green_ok and pinned and gate_removals_red and adj_identical)
proof = {
    **common("P-redgreen", cells_n=1 + 3 + len(sab) + 2, resource_prefixes=("red_base", "green_rep", "adjacent_", "sabotage_")),
    "contract_test": {"path": "tests/agent/test_anthropic_context_editing.py", "blob": "fc48d77dbb85fd2a34c7e73acbf29df25c07e94c",
                      "tests": 2, "cases": CASES,
                      "case_ids": ["off", "on", "compression-disabled", "checkpoint-required", "non-claude-model", "third-party-endpoint", "structured-rejection"]},
    "commands": {"driver": DRIVER,
                 "red": PYTEST.format(files="tests/agent/test_anthropic_context_editing.py") + "  # base checkout + the head's test file",
                 "green": PYTEST.format(files="tests/agent/test_anthropic_context_editing.py") + "  # head checkout, 3 reps",
                 "sabotage": "HERMES_PYTHON=<venv-python> XF_TESTHOME=<testhome> <venv-python> harness/sabotage.py --worktree <worktree> --out raw/sabotage.json",
                 "adjacent": PYTEST.format(files=" ".join(adjacent_files))},
    "gates": {
        "validity": "PASS",
        "red": {"arm": "base", "result": "PASS" if red_failed == 2 and len(markers_found) == 2 else "FAIL",
                "observed": f"{red_failed} failed / {red_passed + red_failed} (the 5 cases that expect no field pass on both arms by design)",
                "assertion": markers_found, "seam_covered": True, "reps_agree": "1/1", "raw": raw_ref("red_base.txt")},
        "green": [{"arm": "head", "result": "PASS" if green_ok else "FAIL", "reps_agree": f"{sum(1 for g in green if f'{CASES} tests passed, 0 failed' in g)}/3",
                   "observed": green, "raw": raw_ref("green3.txt")}],
        "sabotage": {"mode": "one hunk at a time; kind revert = an added line or condition deleted or undone, mutation = a value changed (where deleting would only crash), adjacent = a refactored pre-existing path broken and its existing owning test run",
                     "harness": {"path": "harness/sabotage.py", "sha256": sha(A / "harness/sabotage.py")},
                     "per_hunk": [{"arm": "head", "hunk": s["id"], "kind": s["kind"], "file": s["file"], "test": s["test"], "red_again": s["re_red"],
                                   "failed": s["failed"], "passed": s["passed"]} for s in contract_rows],
                     "gate_condition_removals": {g: next(s for s in sab if s["id"] == g)["re_red"] for g in GATE_REMOVALS},
                     "adjacent_rows": [{"arm": "head", "hunk": s["id"], "file": s["file"], "test": s["test"], "red_again": s["re_red"],
                                        "failed": s["failed"], "passed": s["passed"]} for s in adjacent_rows],
                     "pinned": len(pinned), "total": len(contract_rows),
                     "unpinned_hunks": [s["id"] for s in contract_rows if not s["re_red"]],
                     "unpinned_note": "sibling config propagation (TUI hot reload, gateway agent-cache key), as for codex_responses_native; not reached by the two contract tests",
                     "not_mutated": ["config_defaults default entry", "cli-config.yaml.example", "website docs (2 pages)",
                                     "adapter beta constant, signature and docstring",
                                     "CLEAR_AT_LEAST_FRACTION value (the test only checks 0 < clear_at_least < trigger)",
                                     "recovery display name and log text"],
                     "raw": raw_ref("sabotage.json")},
        "adjacent": {"files": adjacent_files, "base": adj_b, "arm": adj_h, "identical": adj_identical,
                     "pre_existing_failures": [], "raw": {"base": raw_ref("adjacent_base.txt"), "head": raw_ref("adjacent_head.txt")}},
        "guards": {"G-guards": f"see G-guards/{RUN}"},
        "flaky": not green_ok,
        "noise_floor": None, "credit": None, "informativeness": "N_A",
        "route_scope": "native Anthropic API, Claude models",
        "cache_read_ratio": {"status": "NOT_MEASURED", "before": None, "after": None, "needs": "F10 (paid, OD-3)"},
    },
    "ab": None,
    "measurements": [
        {"name": "cases_failed", "arm": "base", "value": red_failed, "n": CASES, "label": "OBSERVED", "statistic": "count"},
        {"name": "cases_passed", "arm": "head", "value": CASES if green_ok else None, "n": CASES, "reps": 3, "label": "OBSERVED", "statistic": "count per rep"},
        {"name": "sabotage_hunks_re_red", "arm": "head", "value": len(pinned), "n": len(contract_rows), "label": "OBSERVED", "statistic": "count"},
        {"name": "adjacent_refactor_rows_re_red", "arm": "head", "value": sum(1 for s in adjacent_rows if s["re_red"]), "n": len(adjacent_rows), "label": "OBSERVED", "statistic": "count"},
    ],
    "not_tested": ["full test suite (targeted files only, per protocol)", "real Anthropic API"],
    "limitations": ["the 2 sibling config hunks (TUI hot reload, gateway cache key) are not pinned by the contract tests",
                    "the codex_responses row of the generalised recovery table is not pinned: removing it fails nothing in test_native_compaction, which only covers the rejection classifier, and git grep finds no test that reaches that recovery step on main",
                    "agent-written contract tests support the invariant only (S14); they carry no value claim"],
    "verdict": "KEEP" if proof_keep else "DISCARD",
    "learning": {"hypothesis": "main ignores compression.anthropic_context_editing on the native Anthropic route",
                 "result": "KEEP" if proof_keep else "DISCARD", "observed_evidence": markers_found, "regressions": [],
                 "reusable_lesson": None, "roadmap_effect": "hold at LIMITED until F10"},
}
write(f"P-redgreen-{RUN}.json", proof)

# ---- F09 gate probe -------------------------------------------------------------------------
fb, fh = load("f09_base.json"), load("f09_head.json")
cb, ch = cells(fb), cells(fh)
wb, wh = cb["flag_absent_wire"], ch["flag_absent_wire"]
same_len = len(wb["requests"]) == len(wh["requests"])
body_same = same_len and all(x["body_minus_system_sha256"] == y["body_minus_system_sha256"] for x, y in zip(wb["requests"], wh["requests"]))
hdr_same = same_len and all(x["headers_sha256"] == y["headers_sha256"] for x, y in zip(wb["requests"], wh["requests"]))
sys_same = wb["system_normalised_sha256"] == wh["system_normalised_sha256"]
gate_names = ["native_claude_flag_false", "native_claude_flag_true", "native_claude_flag_true_compression_disabled",
              "native_claude_flag_true_checkpoint_required", "native_non_claude_flag_true", "third_party_endpoint_flag_true"]
s400 = "structured_400_disable_and_retry_once"
f09_keep = (all(ch[n]["pass"] for n in gate_names) and ch[s400]["pass"] and ch["over_threshold_local_fallback_on"]["pass"]
            and body_same and hdr_same and sys_same and not any(any(cb[n]["payload_sent"]) for n in gate_names))
f09 = {
    **common("F09", cells_n=2 * len(fh["cells"]), resource_prefixes=("f09_",)),
    "inputs": {"harness": {"path": "harness/f09_gate_probe.py", "sha256": sha(A / "harness/f09_gate_probe.py")},
               "fake_server": {"path": "tests/fakes/providers/anthropic_messages.py", "blob": "e46bb9b43945210f8b7521bc10d05cdb8da57e4c", "same_on_both_arms": True}},
    "commands": [f"<venv-python> harness/f09_gate_probe.py --repo <worktree> --arm {a} --out raw/f09_{a}.json  # <worktree> at {c[:10]}"
                 for a, c in (("base", BASE), ("head", HEAD))],
    "raw": {"base": raw_ref("f09_base.json"), "head": raw_ref("f09_head.json")},
    "gate_matrix": {n: {"base_payload_sent": cb[n]["payload_sent"], "head_payload_sent": ch[n]["payload_sent"],
                        "head_beta_present": ch[n]["beta_present"], "expect_payload_on_head": ch[n]["expect_payload"],
                        "head_pass": ch[n]["pass"]} for n in gate_names},
    "head_payload_example": {"local_threshold_tokens": ch["native_claude_flag_true"]["local_threshold_tokens"],
                             "payload": ch["native_claude_flag_true"]["payload"]},
    "structured_400": {"base": cb[s400]["payload_sent_per_request"], "head": ch[s400]["payload_sent_per_request"],
                       "head_flag_after": ch[s400]["flag_after"],
                       "rejection_text": "context_management: Extra inputs are not permitted (scripted; real API wording NOT_MEASURED)"},
    "local_compressor_over_threshold": {
        arm: {"flag_on": {k: c["over_threshold_local_fallback_on"][k] for k in (
                  "local_threshold_tokens", "turn1_real_input_tokens", "local_compress_calls_turn2",
                  "payload_sent_per_request", "trigger_sent")},
              "flag_off": {k: c["over_threshold_local_fallback_off"][k] for k in (
                  "local_compress_calls_turn2", "payload_sent_per_request")}}
        for arm, c in (("base", cb), ("head", ch))},
    "flag_absent_wire": {"requests_per_arm": len(wh["requests"]), "body_minus_system_identical": body_same,
                         "headers_identical": hdr_same, "anthropic_beta_header": wh["requests"][0]["beta_header"],
                         "system_identical_after_host_normalisation": sys_same,
                         "host_normalisation": [s["placeholder"] for s in wh["system_host_substitutions"]],
                         "verdict": "IDENTICAL" if body_same and hdr_same and sys_same else "DIFFERENT"},
    "sdk_schema_errors": {"base": fb["sdk_schema_errors_total"], "head": fh["sdk_schema_errors_total"]},
    "egress_blocked": {"base": fb["egress_blocked"], "head": fh["egress_blocked"]},
    "gates": {"validity": "PASS", "cache_read_ratio": {"status": "NOT_MEASURED", "before": None, "after": None, "needs": "F10 (paid, OD-3)"},
              "route_scope": "native Anthropic API, Claude models; local compressor unchanged"},
    "ab": None,
    "measurements": [
        {"name": "gate_cells_with_payload_head", "arm": "head", "value": sum(1 for n in gate_names if any(ch[n]["payload_sent"])), "n": len(gate_names), "label": "OBSERVED", "statistic": "count"},
        {"name": "ineligible_cells_with_payload_head", "arm": "head", "value": sum(1 for n in gate_names if not ch[n]["expect_payload"] and any(ch[n]["payload_sent"])), "n": 5, "label": "OBSERVED", "statistic": "count"},
        {"name": "gate_cells_with_payload_base", "arm": "base", "value": sum(1 for n in gate_names if any(cb[n]["payload_sent"])), "n": len(gate_names), "label": "OBSERVED", "statistic": "count"},
        {"name": "cache_read_before_after_clear", "value": None, "label": "NOT_MEASURED", "note": "needs F10 (paid, OD-3)"},
    ],
    "not_tested": ["real Anthropic acceptance of the payload and the real rejection wording",
                   "cache_read/cache_creation after a server-side clear (F10)",
                   "OAuth (Claude subscription) route acceptance of the beta",
                   "whether the server re-clears on every request once over trigger (client resends full history)",
                   "local fallback after a real server-side clear: local compression decides on the provider-reported prompt size, which after a clear is the post-clear size, so the fallback is deferred while the resent transcript keeps growing; the fake reports 60K whether or not the payload is sent, so this regime is not exercised",
                   "compaction-exam recall with clears (F10-exam harness not written)"],
    "limitations": ["one rep per cell (deterministic fake)", "the over-threshold cells count _compress_context calls via a wrapper",
                    "the over-threshold cells show the local trigger still fires when reported usage is high; they do not model usage after a real clear"],
    "verdict": "KEEP" if f09_keep else "DISCARD",
    "learning": {"hypothesis": "payload only when opted in and eligible; 400 disables and retries once; local fallback intact; flag-absent wire unchanged",
                 "result": "KEEP" if f09_keep else "DISCARD", "observed_evidence": [], "regressions": [],
                 "reusable_lesson": "system prompts embed host facts (temp HOME, kernel, python); compare host-normalised hashes, never store the text",
                 "roadmap_effect": "hold at LIMITED until F10"},
}
write(f"F09-{RUN}.json", f09)

# ---- Guards (F14 standing set) ------------------------------------------------------------------
gb, gh = load("f14_base.json"), load("f14_head.json")
pb, ph = {r["id"]: r for r in gb["probes"]}, {r["id"]: r for r in gh["probes"]}
assert list(pb) == list(ph), "probe lists differ between arms"
assert gb["commit"] == BASE and gh["commit"] == HEAD, "F14 summaries are for other commits"
F14_ITEMS = 24  # FACTORY section 13 row 2: token_accounting 3, native_compaction 1, provider_fallback 3, goal_command_parity 1,
                # compaction/test_region_scoping 1, postmortem 9 non-live + 5 hand-run, readtool fixtures 1
runner = "postmortem/run_non_live"
items_run = (len(pb) - 1) + ph[runner]["key"]["n"]
rows = []
for pid in pb:
    b, h = pb[pid], ph[pid]
    same_verdict = (b["verdict"], b["rc"], b["marker_found"]) == (h["verdict"], h["rc"], h["marker_found"])
    if pid == runner:
        same_verdict = same_verdict and b["key"]["probes"] == h["key"]["probes"]
    if pid == "token_accounting/replay_gates":
        same_verdict = same_verdict and b["key"]["verdict"] == h["key"]["verdict"]
    rows.append({"probe": pid, "base": b["verdict"], "head": h["verdict"], "rc": [b["rc"], h["rc"]],
                 "marker": b["marker"], "marker_found": [b["marker_found"], h["marker_found"]], "verdict_equal": same_verdict,
                 "stdout_normalised_equal": b["stdout_normalised_sha256"] == h["stdout_normalised_sha256"],
                 "file_normalised_equal": None if b["file_normalised_sha256"] is None else b["file_normalised_sha256"] == h["file_normalised_sha256"],
                 "pytest_summary": [b["pytest_summary"], h["pytest_summary"]] if b["pytest_summary"] else None,
                 "pre_existing_fail_on_base": b["verdict"] != "PASS",
                 "command": h["command"]})
rg_b, rg_h = pb["token_accounting/replay_gates"]["key"]["verdict"], ph["token_accounting/replay_gates"]["key"]["verdict"]
rg_pass = all(v == "PASS" for v in rg_h.values())
all_equal = all(r["verdict_equal"] for r in rows)
hash_diffs = [r["probe"] for r in rows if not r["stdout_normalised_equal"] or r["file_normalised_equal"] is False]
guards = {
    **common("G-guards", cells_n=2 * len(rows), kind="regression", resource_prefixes=("f14_",)),
    "inputs": {"harness": {"path": "harness/f14_guards.py", "sha256": sha(A / "harness/f14_guards.py")}},
    "commands": [f"HERMES_PYTHON=<venv-python> <venv-python> -B harness/f14_guards.py --worktree <worktree> --arm {a} --raw raw --private <private>  # <worktree> at {c[:10]}"
                 for a, c in (("base", BASE), ("head", HEAD))],
    "probe_env": gh["env"],
    "raw": {"base": raw_ref("f14_base.json"), "head": raw_ref("f14_head.json")},
    "coverage": {"f14_items": F14_ITEMS, "run": items_run, "not_run": gh["not_run"],
                 "note": f"{items_run} of {F14_ITEMS} F14 items run on both arms (the postmortem runner counts as its {ph[runner]['key']['n']} probes)"},
    "guards": {"per_probe": rows,
               "replay_gates": {"base_verdict": rg_b, "head_verdict": rg_h, "equal": rg_b == rg_h, "all_pass_head": rg_pass},
               "postmortem_runner": {"base": pb[runner]["key"]["probes"], "head": ph[runner]["key"]["probes"]},
               "ab_checkpoint_preflight": {"base": pb["native_compaction/ab_checkpoint_preflight"]["key"], "head": ph["native_compaction/ab_checkpoint_preflight"]["key"]}},
    "normalised_output_differences": {"probes": hash_diffs, "explained": F14_HASH_NOTES,
                                      "unexplained": [d for d in hash_diffs if d not in F14_HASH_NOTES],
                                      "aa_note": "a base-only trial run before pre-registration differed from this base arm on the same 6 probes (run-specific temp names, timings, pids, timestamps), plus replay_gates token counts that track the private path length; the two arms here use equal-length paths"},
    "gates": {"validity": "PASS", "guards": {"F14": "equal" if all_equal and rg_pass else "different",
                                              "F14_coverage": f"partial ({items_run} of {F14_ITEMS})"}},
    "ab": None,
    "measurements": [{"name": "f14_probe_verdicts_equal", "value": sum(r["verdict_equal"] for r in rows), "n": len(rows), "label": "OBSERVED", "statistic": "count"},
                     {"name": "f14_items_run", "value": items_run, "n": F14_ITEMS, "label": "OBSERVED", "statistic": "count"},
                     {"name": "replay_gates_pass_head", "arm": "head", "value": sum(v == "PASS" for v in rg_h.values()), "n": len(rg_h), "label": "OBSERVED", "statistic": "count"},
                     {"name": "probes_failing_on_base_too", "value": sum(r["pre_existing_fail_on_base"] for r in rows), "n": len(rows), "label": "OBSERVED", "statistic": "count",
                      "note": "pre-existing on main; equal on both arms"}],
    "not_tested": ["the Anthropic payload (F09 covers it)"] + [n["id"] for n in gh["not_run"]],
    "limitations": ["no F14 probe reaches the anthropic_messages structured-400 recovery step; the contract test and F09 cover it",
                    "one rep per probe on each arm",
                    "FACTORY lists compaction/test_region_scoping as a run_tests.sh call, which collects 0 tests; it was run as the script it is"],
    "verdict": "EQUAL" if all_equal and rg_pass else "DIFFERENT",
    "learning": {"hypothesis": "no regression across the F14 standing set", "result": "EQUAL" if all_equal and rg_pass else "DIFFERENT",
                 "observed_evidence": [], "regressions": [] if all_equal else [r["probe"] for r in rows if not r["verdict_equal"]],
                 "reusable_lesson": "3 postmortem runner probes fail on current main itself (drifted probe scripts); compare arms, never absolute PASS",
                 "roadmap_effect": "P5 stays PARTIAL until goal_repaste (synthetic state.db) and the readtool fixtures have runnable F14 commands"},
}
write(f"G-guards-{RUN}.json", guards)

print(json.dumps({"P-redgreen": proof["verdict"], "red": proof["gates"]["red"]["observed"], "green": proof["gates"]["green"][0]["reps_agree"],
                  "sabotage": f"{len(pinned)}/{len(contract_rows)}", "gate_removals_red": gate_removals_red, "unpinned": proof["gates"]["sabotage"]["unpinned_hunks"],
                  "adjacent_rows": {s["id"]: s["re_red"] for s in adjacent_rows},
                  "adjacent": [adj_b, adj_h, adj_identical], "F09": f09["verdict"], "wire": f09["flag_absent_wire"]["verdict"],
                  "guards": guards["verdict"], "f14": guards["coverage"]["note"], "hash_diffs": hash_diffs, "wall_s_total": META["wall_s_total"], "cpu_core_s_total": META["cpu_core_s_total"]}, indent=1))
