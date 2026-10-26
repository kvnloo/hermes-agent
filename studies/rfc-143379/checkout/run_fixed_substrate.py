#!/usr/bin/env python3
"""Exact-head, downstream-only falsifier runner for Hermes RFC #143379.

Runs the unchanged #654 probes on a disposable candidate checkout. No patching,
upstream publication, network fetch, real user logs, or production profiles.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

REQUIRED = {
    "read_dispatch": "test_read_dispatch_contract",
    "read_concurrency": "test_read_concurrency_snapshot",
    "chain_reference_race": "test_chain_doc_reference_race",
    "encoding_freshness": (
        "test_read_reflects_external_edit_without_mutating_frozen_prompt or "
        "test_read_handles_utf8_bom_without_rewriting or "
        "test_read_corrupt_utf8_keeps_disk_untouched or "
        "test_chain_doc_orphan_remains_readable_but_not_writable"
    ),
}
ADVISORY = "test_chain_doc_read_response_budget_candidate"
NEIGHBORS = [
    "tests/tools/test_memory_tool.py",
    "tests/tools/test_memory_patch_action.py",
    "tests/tools/test_memory_target_contract.py",
    "tests/tools/test_memory_tool_schema.py",
    "tests/tools/test_memory_chain_docs.py",
]
CREDENTIAL_KEYS = ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "NOUS_API_KEY")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(path: Path) -> dict[str, int]:
    result = dict.fromkeys(("tests", "failures", "errors", "skipped"), 0)
    if not path.exists():
        return result
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    for suite in suites:
        for key in result:
            result[key] += int(suite.get(key, "0"))
    return result


def suite_paths(manifest: Path | None) -> tuple[list[str], str]:
    if manifest is None:
        return NEIGHBORS, "neighboring_only"
    paths = [line.strip() for line in manifest.read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    if not paths or len(paths) != len(set(paths)):
        raise ValueError("Suite manifest must contain nonempty unique test paths")
    return paths, "declared"


def validate_path(path: str) -> None:
    parts = Path(path).parts
    if not path.startswith("tests/") or ".." in parts or Path(path).is_absolute():
        raise ValueError(f"Unsafe test path: {path}")


def run_one(checkout: Path, out: Path, env: dict[str, str], label: str,
            category: str, test_path: str, selector: str = "") -> dict:
    validate_path(test_path)
    log = out / f"{label}.log"
    junit = out / f"{label}.xml"
    row = {"label": label, "category": category, "path": test_path,
           "log": log.name, "junit": junit.name, "selector": selector}
    if not (checkout / test_path).is_file():
        log.write_text("Test file missing at exact candidate commit\n", encoding="utf-8")
        row["exit_code"] = "MISSING"
    else:
        cmd = [str(checkout / "scripts/run_tests.sh"), test_path,
               "--file-retries", "0", "--", "-q"]
        if selector:
            cmd.extend(("-k", selector))
        cmd.append(f"--junitxml={junit}")
        with log.open("w", encoding="utf-8") as stream:
            try:
                proc = subprocess.run(cmd, cwd=checkout, env=env, stdout=stream,
                                      stderr=subprocess.STDOUT, timeout=7200, check=False)
                row["exit_code"] = proc.returncode
            except subprocess.TimeoutExpired:
                row["exit_code"] = "TIMEOUT"
    row.update(counts(junit))
    row["passed"] = (row["exit_code"] == 0 and row["tests"] > 0
                     and row["failures"] == row["errors"] == row["skipped"] == 0)
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path, help="Hermes checkout containing the candidate commit")
    parser.add_argument("fixed_sha", help="exact published 40-character candidate commit SHA")
    parser.add_argument("output", type=Path)
    parser.add_argument("--suite-manifest", type=Path, help="author-defined 297-test memory battery files")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.fixed_sha):
        parser.error("Fixed SHA must be 40 lowercase hex characters; not a branch name")
    repo = args.repo.resolve()
    if not (repo / "scripts/run_tests.sh").is_file():
        parser.error("Expected an existing Hermes checkout with scripts/run_tests.sh")
    try:
        git(repo, "cat-file", "-e", f"{args.fixed_sha}^{{commit}}")
    except subprocess.CalledProcessError:
        parser.error("Exact commit unavailable. Fetch the published ref/bundle; never substitute a branch tip")
    study = Path(__file__).resolve().parent
    probe = study / "test_real_checkout.py"
    scenarios = study / "consent_scenarios.json"
    if not probe.is_file() or not scenarios.is_file():
        parser.error("Missing unchanged #654 probe and synthetic consent fixture")
    memory_paths, suite_kind = suite_paths(args.suite_manifest)
    for path in memory_paths:
        validate_path(path)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hermes-rfc143379-fixed-") as temp:
        root = Path(temp)
        checkout = root / "candidate"
        git(repo, "worktree", "add", "--detach", str(checkout), args.fixed_sha)
        try:
            if git(checkout, "rev-parse", "HEAD") != args.fixed_sha:
                raise RuntimeError("Detached candidate SHA mismatch")
            target_probe = checkout / "tests/tools/test_rfc_homework.py"
            target_scenarios = checkout / "tests/tools/rfc_consent_scenarios.json"
            if target_probe.exists() or target_scenarios.exists():
                raise RuntimeError("Candidate already contains injected test path; refusing overwrite")
            target_probe.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(probe, target_probe)
            shutil.copyfile(scenarios, target_scenarios)
            env = os.environ.copy()
            for key in CREDENTIAL_KEYS:
                env.pop(key, None)
            env["HERMES_HOME"] = str(root / "isolated-hermes-home")
            Path(env["HERMES_HOME"]).mkdir()
            rows = [run_one(checkout, out, env, label, "required",
                            "tests/tools/test_rfc_homework.py", selector)
                    for label, selector in REQUIRED.items()]
            rows.append(run_one(checkout, out, env, "doc_response_4096", "advisory",
                                "tests/tools/test_rfc_homework.py", ADVISORY))
            for i, path in enumerate(memory_paths, 1):
                rows.append(run_one(checkout, out, env, f"memory_suite_{i}", "memory_suite", path))
            tracked_dirty = bool(git(checkout, "status", "--porcelain", "--untracked-files=no"))
        finally:
            git(repo, "worktree", "remove", "--force", str(checkout))
    required = [r for r in rows if r["category"] == "required"]
    battery = [r for r in rows if r["category"] == "memory_suite"]
    battery_count = sum(r["tests"] for r in battery)
    required_green = len(required) == len(REQUIRED) and all(r["passed"] for r in required)
    battery_297_green = (suite_kind == "declared" and bool(battery)
                         and all(r["passed"] for r in battery) and battery_count == 297)
    certified = required_green and battery_297_green and not tracked_dirty
    receipt = {
        "schema": "rfc143379.shared-falsifiers.v1", "candidate_sha": args.fixed_sha,
        "probe_sha256": sha256(probe), "scenarios_sha256": sha256(scenarios),
        "unchanged_probe": True, "tracked_source_dirty": tracked_dirty,
        "suite_kind": suite_kind, "memory_test_count": battery_count,
        "required_probes_green": required_green,
        "claimed_297_battery_green": battery_297_green,
        "overall": "PASS_CANDIDATE" if certified else "NOT_CERTIFIED",
        "real_model": False, "real_compressor": False, "real_user_logs": False,
        "advisory_policy": "The 4 KiB doc-response budget is not an accepted upstream contract.",
        "results": rows,
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: receipt[key] for key in
                     ("candidate_sha", "required_probes_green", "claimed_297_battery_green",
                      "memory_test_count", "overall")}))
    return 0 if certified else 1


if __name__ == "__main__":
    raise SystemExit(main())
