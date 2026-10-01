"""Build the plugin-catalog-entries receipts from raw outputs (every cited raw file is sha256-pinned).

Host locations are not stored in this file (round-2 privacy fix). The staging directory is the
parent of tools/; the others come from the environment and default to the placeholders the
published receipts use:
  XF_WORKTREE  the disposable hermes worktree the slice ran in   (default <worktree>)
  XF_VENV      the hermes venv prefix                            (default <venv>)
  XF_TESTHOME  the isolated HOME for catalog commands and tests  (default <testhome>)
Run tools/scrub_receipts.py afterwards (same env) to replace the staging path and any env paths.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

R = Path(__file__).resolve().parent.parent
RAW, OUT, TOOLS = R / "raw", R / "receipts", R / "tools"
W = os.environ.get("XF_WORKTREE", "<worktree>")
RUN = str(R / "run")
PY = os.environ.get("XF_VENV", "<venv>") + "/bin/python"
TH = os.environ.get("XF_TESTHOME", "<testhome>")
MAIN_NOW = "234badf4012af380d23c91eae55d045a69c69ffb"
MAIN_MEASURED = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0"
COMMIT = "98c305b3ec8d03693f4dc94bade69035cb15ff7d"
COMMIT_V0 = "2b05ac2bb8423c987ba8051f6cc22939104b4da7"
PLUGIN = {"repo": "https://github.com/kvnloo/pii", "sha": "d891ebdd3a3dab27a3451923eb56f955253a2782",
          "subdir": "integrations/hermes", "parent_repo": "programasweights/pii",
          "parent_main": "454b8df4e35b207d84afa2ce1761079ea2975346", "ahead_of_parent": 1,
          "pinned_commit_author": "GitHub login kvnloo (author and committer); committer display name lesseradmin"}
INVALIDATE_ON = ["plugin-catalog/", "hermes_cli/plugin_validate.py", "hermes_cli/plugin_validate_desktop.py",
                 "hermes_cli/plugin_catalog.py", "hermes_cli/middleware.py", "hermes_cli/plugins.py",
                 "hermes_cli/plugins_dispatch.py", "hermes_cli/plugins_loader.py", "scripts/validate_plugin_catalog.py",
                 "website/scripts/extract-plugins.py", "tools/plugin_guard.py", "tools/skills_guard.py",
                 "hermes_cli/plugins_cmd_git.py", "hermes_cli/plugins_cmd_install.py", "hermes_cli/plugins_cmd_catalog.py",
                 ".github/workflows/", "tests/hermes_cli/test_plugin_catalog.py", "pm/plugin_declarations.py"]
BLOBS_AT_COMMIT = {
    "plugin-catalog/paw-pii.yaml": "845dc6cce78e67a8989e267debcc5b4a4dcf473c",
    "hermes_cli/plugin_validate.py": "2f31a9a4b1d66bd0c89a676f7f57f2f541605d33",
    "hermes_cli/middleware.py": "c0940d26bbd4d31fd307aa54f3f8d21e0108f2a6",
    "scripts/validate_plugin_catalog.py": "c5da7f113b2d1c794b4650ba3bbf36348ef45bd5",
    "website/scripts/extract-plugins.py": "a751462f9e802ea5d87e61ae62138ed89cabb779",
    "tools/plugin_guard.py": "41de8272156177ad7b4b1e0e6f6c7dca676f9530",
    "hermes_cli/plugins_cmd_git.py": "75d0180d0966ce272e92d80327bed106e193e5fd",
    "hermes_cli/plugins_cmd_install.py": "58ac003270078e7fde9fbea9759a819e6d2d4aec",
    ".github/workflows/plugin-catalog-ci.yml": "0b4bc2adbd06a72b7d532e81a63a5187b090c480",
    "tests/hermes_cli/test_plugin_catalog.py": "e1a7f2ac2dbbd82bd8a94f73e454defbac751da0",
}
ENV = {"host": "<host>", "python_system": "3.14.7", "python_hermes_venv": "3.11.14 (live venv interpreter, read-only; "
       "main requires ==3.14.*, see pre-existing env errors)", "sandbox": "bwrap 0.12.0: ro-root, tmpfs over the user "
       "home and the live Hermes home (venv re-bound ro), unshare-net, unshare-pid, clearenv, writable $RUN on the "
       "artifact volume only",
       "in_process_guard": "t1 probes: loopback-only socket.connect + exec audit hook (read-only git allowlisted)"}
COMMON = {"schema": "xf.receipt.v1", "staging": "plugin-catalog-entries", "provenance": "self",
          "origin_refs": ["NousResearch/hermes-agent#102922", "NousResearch/hermes-agent#102924",
                          "NousResearch/hermes-agent#87495", "NousResearch/hermes-agent#98105"],
          "policy_revision": {"plugin-catalog/README.md": "rules 2,3,5,6,7,8,9 @ " + MAIN_NOW},
          "ai_assistance": "Claude Code (Opus 5.5) wrote the census, the probes and these receipts; disclosed per repository policy",
          "privacy": "local (synthetic canary text only; no state.db, logs or credentials read; commands carry host paths, so scrub paths before any public freeze)",
          "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0, "tokens": 0, "wall_s": None, "wall_s_label": "NOT_MEASURED"}}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name: str):
    return json.loads((RAW / name).read_text())


def artifacts(*names: str) -> list[dict]:
    return [{"path": str(RAW / n), "sha256": sha(RAW / n)} for n in names]


def tool(name: str) -> dict:
    return {"path": str(TOOLS / name), "sha256": sha(TOOLS / name)}


def write(name: str, data: dict) -> None:
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")


def f12() -> None:
    v = {k: load(f"f12_{k}.json") for k in ("as-pinned", "fixed-manifest", "sabotage")}
    nc2 = load("f12_nc2_catalog_no_middleware.json")
    a = v["as-pinned"]
    cmd = (f"RUN={RUN} VENV=1 CHDIR={W} {TOOLS}/sandbox.sh {PY} -I {TOOLS}/f12_census.py --clone {RUN}/src/pii "
           f"--repo {PLUGIN['repo']} --sha {PLUGIN['sha']} --subdir {PLUGIN['subdir']} "
           f"--catalog-entry {W}/plugin-catalog/paw-pii.yaml --hermes-tree {W} --variant <as-pinned|fixed-manifest|sabotage> "
           f"[--plugin-dir-override {RUN}/variants/<variant>] --context-methods-out {RUN}/context_methods.json")
    write("F12-r20261001-01.json", {**COMMON,
        "id": "F12/r20261001-01", "tier": "T0 (static: ast + hermes static check functions; plugin code never imported)",
        "question": "At its pinned SHA, does paw-pii register exactly what its manifest and the catalog entry declare, and is it free of internal-path imports, self-updaters and desktop-surface violations?",
        "base_revision": {"hermes_tree": f"{COMMIT_V0} (slice on {MAIN_MEASURED})",
                          "current_main": MAIN_NOW, "invalidate_on_changed_since": False, "invalidate_on": INVALIDATE_ON},
        "inputs": {"plugin": PLUGIN, "plugin_manifest_sha256": a["manifest"]["sha256"],
                   "catalog_entry_sha256": a["catalog_entry"]["sha256"], "census_script": tool("f12_census.py"),
                   "sandbox": tool("sandbox.sh"), "hermes_blobs": BLOBS_AT_COMMIT},
        "command": cmd, "env": ENV,
        "measurements": [
            {"name": "pin_head_matches_and_reachable", "value": a["pin"]["head_matches_pin"] and a["pin"]["reachable_from_default_branch"], "label": "OBSERVED"},
            {"name": "registered_tools", "value": a["registrations"]["summary"]["tools"], "label": "OBSERVED (ast)"},
            {"name": "registered_middleware", "value": a["registrations"]["summary"]["middleware"], "label": "OBSERVED (ast)"},
            {"name": "registered_hooks", "value": a["registrations"]["summary"]["hooks"], "label": "OBSERVED (ast)"},
            {"name": "capability_mismatch_plugin_manifest", "value": a["counts"]["capability_mismatch_manifest"], "unit": "count", "label": "OBSERVED (ast)", "detail": a["manifest_vs_registrations"]["middleware"]},
            {"name": "capability_mismatch_catalog_entry", "value": a["counts"]["capability_mismatch_catalog"], "unit": "count", "label": "OBSERVED (ast)"},
            {"name": "internal_path_imports", "value": a["counts"]["internal_path_imports"], "unit": "count", "label": "OBSERVED (ast)"},
            {"name": "syspath_mutations", "value": a["counts"]["syspath_mutations"], "unit": "count", "label": "OBSERVED (ast)", "detail": a["syspath_mutations"]},
            {"name": "imports_unresolvable_under_catalog_install_layout", "value": a["counts"]["unresolved_imports_catalog_layout"], "unit": "count", "label": "OBSERVED (ast + layout)", "detail": a["unresolved_under_catalog_install_layout"]},
            {"name": "out_of_subdir_package_third_party_imports", "value": a["out_of_subdir_package_third_party_imports"], "label": "OBSERVED (ast)"},
            {"name": "self_updater_signals", "value": a["counts"]["self_updater_signals"], "unit": "count", "label": "OBSERVED (ast + CI regex)"},
            {"name": "desktop_surface_bundles", "value": a["counts"]["desktop_surface_bundles"], "unit": "count", "label": "OBSERVED"},
            {"name": "declared_install_dependencies", "value": a["dependencies"]["declared_for_install"], "label": "OBSERVED"},
            {"name": "repo_root_deps_without_upper_bound", "value": len(a["dependencies"]["repo_root_without_upper_bound"]), "of": len(a["dependencies"]["repo_root_pyproject"]), "label": "OBSERVED", "detail": a["dependencies"]["repo_root_without_upper_bound"]},
            {"name": "hermes_static_subchecks_failed", "value": [c for c in a["hermes_static_validate_subchecks"]["checks"] if not c["ok"]], "label": "OBSERVED"},
            {"name": "security_scan_verdict", "value": a["hermes_static_validate_subchecks"]["security_scan"]["verdict"], "findings": len(a["hermes_static_validate_subchecks"]["security_scan"]["findings"]), "scanner": a["hermes_static_validate_subchecks"]["security_scan"]["scanner"], "label": "OBSERVED"},
            {"name": "builtin_tool_registry_size_and_collisions", "value": a["hermes_static_validate_subchecks"]["builtin_tool_registry"], "label": "OBSERVED"},
            {"name": "predicted_validate_capability_check", "value": a["predicted_validate_capability_check"]["result"], "reasons": a["predicted_validate_capability_check"]["reasons"], "label": "MODELED (confirmed OBSERVED by T1-capability-probe-r20261001-01)"},
        ],
        "calibration": {
            "fixed-manifest (plugin.yaml + provides_middleware)": {"predicted": v["fixed-manifest"]["predicted_validate_capability_check"]["result"], "counts": v["fixed-manifest"]["counts"]},
            "sabotage (undeclared hook + hermes_cli import + git-pull self-updater + desktop/plugin.js fetch+write+eval)": {"predicted": v["sabotage"]["predicted_validate_capability_check"]["result"], "counts": v["sabotage"]["counts"], "hermes_failed": [c for c in v["sabotage"]["hermes_static_validate_subchecks"]["checks"] if not c["ok"]], "scan": v["sabotage"]["hermes_static_validate_subchecks"]["security_scan"]["verdict"]},
            "nc2 (catalog entry with provides_middleware: [])": {"catalog_mismatch": nc2["counts"]["capability_mismatch_catalog"], "structural_validator": "OK (does not catch it)"},
            "result": "census discriminates: as-pinned FAIL, fixed-manifest PASS, every sabotage class flagged, catalog-side drift flagged",
        },
        "artifacts": artifacts("f12_as-pinned.json", "f12_fixed-manifest.json", "f12_sabotage.json", "f12_nc2_catalog_no_middleware.json"),
        "verdict": "KEEP (census) / gate result: FAIL at the pinned SHA",
        "learning": {"hypothesis": "paw-pii at d891ebdd passes catalog admission",
                     "result": "falsified: plugin.yaml omits provides_middleware (validate capability check fails); the subdir-only catalog install cannot import paw_pii (no declared deps, code lives outside the subdir)"},
        "not_tested": ["hermes plugins validate CLI itself (E52, operator approval)", "runtime with programasweights installed and the model downloaded (T2)"],
        "limitations": ["registrations reached through dynamic dispatch would be invisible to the ast census; the T1 probe covers register() at runtime",
                        "hermes static checks ran under the 3.11 venv interpreter while main requires 3.14"],
    })


def t1_capability() -> None:
    reps = {k: [load(f"t1_capability_{k}_rep{i}.json")["results"][0] for i in (1, 2, 3)] for k in ("as_pinned", "fixed_manifest")}
    cmd = (f"MP=$({PY} -c 'import yaml,json,sys; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))' <plugin_dir>/plugin.yaml); "
           f"RUN={RUN} VENV=1 CHDIR={W} {TOOLS}/sandbox.sh {PY} -I {TOOLS}/t1_probe.py capability --hermes-tree {W} "
           f"--plugin-dir <{RUN}/src/pii/integrations/hermes | {RUN}/variants/fixed-manifest> --manifest-json \"$MP\"  (x3 reps)")
    write("T1-capability-probe-r20261001-01.json", {**COMMON,
        "id": "T1-capability/r20261001-01",
        "tier": "T1 (direct call of hermes_cli.plugin_validate._run_capability_probe, the production probe, in the bwrap sandbox; NOT the hermes CLI; E52 stays queued)",
        "question": "Does the production capability probe record undeclared middleware for paw-pii at its pin, and does declaring it clear the check?",
        "base_revision": {"hermes_tree": f"{COMMIT_V0} (slice on {MAIN_MEASURED})", "current_main": MAIN_NOW, "invalidate_on_changed_since": False},
        "inputs": {"plugin": PLUGIN, "probe_script_sha256": reps["as_pinned"][0]["probe_script_sha256"],
                   "harness": tool("t1_probe.py"), "sandbox": tool("sandbox.sh"), "hermes_blobs": {k: BLOBS_AT_COMMIT[k] for k in ("hermes_cli/plugin_validate.py",)}},
        "command": cmd, "env": ENV,
        "arms": {"as-pinned": {"plugin_dir": "integrations/hermes @ d891ebdd"}, "fixed-manifest": {"plugin_dir": "as-pinned + provides_middleware: [llm_request, tool_execution] in plugin.yaml (synthetic)"}},
        "gates": {"red": {"arm": "as-pinned", "result": "FAIL", "reps_agree": f"{sum(r['result']=='FAIL' for r in reps['as_pinned'])}/3",
                          "observed": [c for c in reps["as_pinned"][0]["checks"] if not c["ok"]]},
                  "green": {"arm": "fixed-manifest", "result": "PASS", "reps_agree": f"{sum(r['result']=='PASS' for r in reps['fixed_manifest'])}/3"},
                  "infra": {"blocked_exec_or_connect": sum(len(r["guard_blocked"]) for k in reps for r in reps[k])}},
        "measurements": [{"name": "recorded_registrations", "arm": "as-pinned", "value": reps["as_pinned"][0]["recorded"], "label": "OBSERVED"},
                         {"name": "declared_middleware_check", "arm": "as-pinned", "value": "FAIL", "n": 3, "label": "OBSERVED"},
                         {"name": "declared_middleware_check", "arm": "fixed-manifest", "value": "PASS", "n": 3, "label": "OBSERVED"}],
        "artifacts": artifacts(*[f"t1_capability_{k}_rep{i}.json" for k in ("as_pinned", "fixed_manifest") for i in (1, 2, 3)]),
        "verdict": "KEEP: admission capability check FAILS at d891ebdd; a one-line plugin.yaml fix clears it",
        "not_tested": ["--install-deps and the CLI wrapper (E52)", "the probe child runs without the in-process guard; isolation there is the bwrap layer only"],
    })


def t1_failopen() -> None:
    reps = [load(f"t1_failopen_rep{i}.json")["results"] for i in (1, 2, 3)]
    by = {r["layout"]: r for r in reps[0]}

    def agree(layout, pred):
        return f"{sum(pred(next(r for r in rep if r['layout']==layout)) for rep in reps)}/3"

    fc, ci = by["full-clone"], by["catalog-install"]
    cmd = (f"RUN={RUN} VENV=1 CHDIR={W} {TOOLS}/sandbox.sh {PY} -I {TOOLS}/t1_probe.py failopen --hermes-tree {W} "
           f"--plugin-dir {RUN}/src/pii/integrations/hermes  (x3 reps; catalog-install layout = subdir copied to $HERMES_HOME/plugins/paw-pii)")
    write("T1-failopen-r20261001-01.json", {**COMMON,
        "id": "T1-failopen/r20261001-01",
        "tier": "T1 (plugin callbacks driven through the production hermes_cli.middleware chain; registry stubbed with a real PluginManager; no egress)",
        "question": "When the PAW runtime is not available, does paw-pii stop PII from reaching the provider request and tool results (the fail-closed claim in NousResearch/hermes-agent#102922)?",
        "base_revision": {"hermes_tree": f"{COMMIT_V0} (slice on {MAIN_MEASURED})", "current_main": MAIN_NOW, "invalidate_on_changed_since": False},
        "inputs": {"plugin": PLUGIN, "canary": load("t1_failopen_rep1.json")["canary"], "harness": tool("t1_probe.py"),
                   "sandbox": tool("sandbox.sh"), "hermes_blobs": {k: BLOBS_AT_COMMIT[k] for k in ("hermes_cli/middleware.py",)}},
        "command": cmd, "env": ENV,
        "arms": {"full-clone": "what admission CI validates (repo src/ on sys.path via the plugin's sys.path insert); programasweights absent",
                 "catalog-install": "what `hermes plugins install paw-pii` publishes (sparse subdir only, hermes_cli/plugins_cmd_git.py:_restrict_checkout_to_subdir); paw_pii absent"},
        "measurements": [
            {"name": "llm_request_payload_leaks_canary_markers", "arm": "full-clone", "value": len(fc["llm_request_chain"]["payload_leaks_canary"]), "of": 3, "reps_agree": agree("full-clone", lambda r: len(r["llm_request_chain"]["payload_leaks_canary"]) == 3), "label": "OBSERVED"},
            {"name": "llm_request_trace_claims_redaction", "arm": "full-clone", "value": fc["llm_request_chain"]["changed"], "trace": fc["llm_request_chain"]["trace"], "payload_equals_original": fc["llm_request_chain"]["payload_equals_original"], "label": "OBSERVED"},
            {"name": "tool_execution_result_leaks_canary_markers", "arm": "full-clone", "value": len(fc["tool_execution_chain"]["leaks_canary"]), "of": 3, "label": "OBSERVED"},
            {"name": "redact_pii_tool_returns_original_text", "arm": "full-clone", "value": fc["tool_redact_pii"].get("value") == load("t1_failopen_rep1.json")["canary"], "label": "OBSERVED"},
            {"name": "paw_pii_log_records", "arm": "full-clone", "value": len([l for l in fc["log_records"] if "paw" in l]), "label": "OBSERVED (silent)"},
            {"name": "llm_request_payload_leaks_canary_markers", "arm": "catalog-install", "value": len(ci["llm_request_chain"]["payload_leaks_canary"]), "of": 3, "reps_agree": agree("catalog-install", lambda r: len(r["llm_request_chain"]["payload_leaks_canary"]) == 3), "label": "OBSERVED"},
            {"name": "llm_request_trace_entries", "arm": "catalog-install", "value": len(ci["llm_request_chain"]["trace"]), "changed": ci["llm_request_chain"]["changed"], "label": "OBSERVED"},
            {"name": "tool_execution_result_leaks_canary_markers", "arm": "catalog-install", "value": len(ci["tool_execution_chain"]["leaks_canary"]), "of": 3, "label": "OBSERVED"},
            {"name": "detect_pii_and_redact_pii_tools", "arm": "catalog-install", "value": [ci["tool_detect_pii"].get("exception"), ci["tool_redact_pii"].get("exception")], "label": "OBSERVED"},
            {"name": "paw_pii_log_records", "arm": "catalog-install", "value": [l for l in ci["log_records"] if "paw" in l], "label": "OBSERVED (logged, not blocking)"},
            {"name": "plugin_exec_or_egress_attempts", "value": sum(len(r["guard_blocked"]) for rep in reps for r in rep), "label": "OBSERVED"},
        ],
        "artifacts": artifacts("t1_failopen_rep1.json", "t1_failopen_rep2.json", "t1_failopen_rep3.json"),
        "verdict": "KEEP: fails open in both layouts (3/3); in the full-clone layout the host middleware trace records a redaction that did not happen",
        "learning": {"hypothesis": "paw-pii fails closed on unexpected leakage (#102922 TL;DR)", "result": "falsified for the runtime-missing case; the catalog description now discloses fail-open, and a fail-closed mode is a standalone-repo fix"},
        "not_tested": ["redaction quality with programasweights installed and the program/base model downloaded (T2, local CPU/GPU)", "latency per turn with the runtime present (T2)"],
    })


def slice_proof() -> None:
    lb, lbr = load("loader_base_v234.json"), load("loader_branch_v234.json")
    entry = load("structural_branch_entry.json")
    wf = load("workflow_push_scan.json")
    write("SLICE-proof-r20261001-01.json", {**COMMON,
        "id": "SLICE/r20261001-01", "tier": "T0 (catalog loader, structural validator, docs extractor, targeted pytest)",
        "question": "Is plugin-catalog/paw-pii.yaml a well-formed, loadable, page-generating catalog entry on current main, and do the catalog gates reject a broken variant?",
        "base_revision": MAIN_NOW, "head_revision": COMMIT, "changed_files": ["plugin-catalog/paw-pii.yaml (+20)"],
        "inputs": {"entry_blob": BLOBS_AT_COMMIT["plugin-catalog/paw-pii.yaml"], "probe": tool("catalog_probe.py"), "hermes_blobs": BLOBS_AT_COMMIT},
        "env": ENV,
        "commands": {
            "structural": f"env -i PATH=/usr/bin:/bin HOME={TH} HERMES_HOME={TH}/.hermes {PY} scripts/validate_plugin_catalog.py plugin-catalog/",
            "loader": f"env -i PATH=/usr/bin:/bin HOME={TH} HERMES_HOME={TH}/.hermes {PY} {TOOLS}/catalog_probe.py paw-pii",
            "docs_extract": f"env -i PATH=/usr/bin:/bin HOME={TH} HERMES_HOME={TH}/.hermes {PY} website/scripts/extract-plugins.py --output-dir <scratch> --stars-file /nonexistent",
            "tests": f"HOME={TH} HERMES_HOME={TH}/.hermes HERMES_PYTHON={PY} bash scripts/run_tests.sh -j 2 tests/hermes_cli/test_plugin_catalog.py tests/scripts/test_validate_plugin_catalog.py tests/website/test_extract_plugins.py tests/hermes_cli/test_plugins_cmd_catalog.py tests/hermes_cli/test_plugin_catalog_known_issues.py tests/hermes_cli/test_web_plugins_catalog.py tests/hermes_cli/test_plugins_hub_perf_guard.py tests/hermes_cli/test_plugins_hub_live_catalog.py -q",
            "nc1": "sed -i 's/^sha: <pin>$/sha: main/' plugin-catalog/paw-pii.yaml; structural + tests/hermes_cli/test_plugin_catalog.py::test_shipped_catalog_entries_are_all_valid_and_pinned; git checkout -- plugin-catalog/paw-pii.yaml",
            "merge": f"git merge-tree --write-tree main staging/plugin-catalog-entries  (main={MAIN_NOW})",
        },
        "gates": {
            "need": {"result": "PASS", "observed": f"paw-pii absent on main: loader {lb['loaded']}/{lb['files']} entries, entry_present={lb['entry_present']}, no kill-list match, no name collision; upstream route hermes_cli/data/plugin_index.json removed by 46ab5aa365", "label": "OBSERVED"},
            "green": {"result": "PASS", "observed": f"structural OK 350 files (entry: errors={entry['files'][0]['errors']}, warnings={entry['files'][0]['warnings']}); loader {lbr['loaded']}/{lbr['files']} with entry capabilities {lbr['entry']['capabilities']}; extract-plugins emits the page entry (installCommand 'hermes plugins install paw-pii', readme off); test_shipped_catalog_entries_are_all_valid_and_pinned 3/3 on {MAIN_MEASURED} + 1/1 on {MAIN_NOW}", "label": "OBSERVED"},
            "negative_control": {"result": "PASS", "observed": "sha: main -> validator 'sha 'main' must be exactly 40 lowercase hex characters' rc=1; shipped-entries test 'AssertionError: assert 348 == 349'. Catalog provides_middleware: [] -> structural OK but F12 catalog mismatch 2 (reviewer-side rule 6)", "label": "OBSERVED"},
            "adjacent": {"result": "PASS", "base": "68 passed / 13 errors", "branch": "68 passed / 13 errors", "identical": True,
                         "pre_existing_failures": ["tests/hermes_cli/test_plugins_cmd_catalog.py: 13 setup errors, isolated_python fixture: 'The requested interpreter resolved to Python 3.11.14, which is incompatible with the project's Python requirement: ==3.14.*' (environment: mandated venv is 3.11)"], "label": "OBSERVED"},
            "merge_tree": {"result": "PASS", "tree": "3a915075078775928dd352fa2fe77bd200bdd714", "main": MAIN_NOW},
            "workflow_push_matches": {"result": "PASS", "value": wf["workflow_push_matches"], "push_workflows_scanned": len(wf["push_workflows"])},
            "docs_url": {"result": "PASS", "observed": "https://github.com/kvnloo/pii/blob/<pin>/README.md -> HTTP 200, anchor agent-harness-plugins present; subdir README -> 404, hence readme: false"},
            "upstream_dedupe": {"result": "PASS", "observed": "gh search prs 'pii plugin-catalog' -> none; 'paw-pii' -> only #102924 (kvnloo, closed by author 2026-09-30, obsolete plugin_index.json route); 'programasweights' -> none; issue #102922 (kvnloo) open"},
        },
        "artifacts": artifacts("structural_base.txt", "structural_branch.txt", "structural_branch_entry.json", "loader_base_v234.json",
                               "loader_branch_v234.json", "extract_branch.txt", "adjacent_base_v234.txt", "adjacent_branch_v234.txt",
                               "adjacent_base.txt", "adjacent_branch.txt", "nc1_structural.txt", "nc1_shipped_test.txt",
                               "green_shipped_test_rep1.txt", "green_shipped_test_rep2.txt", "green_shipped_test_rep3.txt",
                               "workflow_push_scan.json"),
        "verdict": "KEEP (the entry file is correct for its pin) / not promotable at this pin (see F12 + T1 receipts)",
        "not_tested": ["plugin-catalog-ci.yml pinned-source-validate job (needs the CLI; E52)", "docs site build with README fetch (readme: false)"],
    })


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    f12(); t1_capability(); t1_failopen(); slice_proof()
    for p in sorted(OUT.glob("*.json")):
        print(sha(p), p.name)
