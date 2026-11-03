#!/usr/bin/env python3
"""Offline, fail-closed consumer of #659 rfc143379.shared-falsifiers.v1 receipts.

No runner, Hermes import, network operation, or model execution occurs here.
The operator must supply independent, pinned source/runner identities and an
author-selected testcase manifest. Passing validates *receipt identity only*.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import xml.etree.ElementTree as ET


SCHEMA = "rfc143379.receipt-contract.v1"
RUNNER_SCHEMA = "rfc143379.shared-falsifiers.v1"
RULE = "rfc143379-author-297-zero-gaps-v1"
PROBE_PATH = "tests/tools/test_rfc_homework.py"
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
COUNTERS = ("tests", "failures", "errors", "skipped")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
STALE_LOG_SKEW_NS = 60 * 1_000_000_000


class ContractError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(detail)


def demand(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise ContractError(code, detail)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("INPUT_UNREADABLE", f"{path}: {exc}") from exc
    demand(isinstance(value, dict), "SCHEMA_INVALID", f"{path} must be a JSON object")
    return value


def check_file(path: Path, kind: str) -> None:
    demand(path.is_file() and not path.is_symlink(), "MANIFEST_MISSING",
           f"Missing or symlinked {kind}: {path}")


def check_sha(value: object, pattern: re.Pattern[str], field: str) -> None:
    demand(isinstance(value, str) and bool(pattern.fullmatch(value)),
           "IDENTITY_INVALID", f"{field} must be a full lowercase hex digest")


def suite_paths(path: Path) -> list[str]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    demand(bool(lines) and len(lines) == len(set(lines)), "SUITE_PATHS_INVALID",
           "The #659 suite manifest needs unique, nonempty test paths")
    for item in lines:
        posix = PurePosixPath(item)
        demand(item.startswith("tests/") and item.endswith(".py")
               and not posix.is_absolute() and ".." not in posix.parts
               and "\\" not in item and posix.as_posix() == item,
               "SUITE_PATHS_INVALID", f"Noncanonical runner test path: {item}")
    return lines


def expected_ids(value: object, label: str) -> set[str]:
    demand(isinstance(value, list) and bool(value), "CASE_MANIFEST_INVALID",
           f"Missing exact testcase identities for {label}")
    demand(all(isinstance(v, str) and re.fullmatch(r"[^:\s]+::[^\r\n]+", v)
               for v in value), "CASE_MANIFEST_INVALID", f"Bad testcase identity: {label}")
    demand(len(value) == len(set(value)), "DUPLICATE_EXPECTED_CASE",
           f"Duplicate author-manifest testcase: {label}")
    return set(value)


def junit_cases(path: Path) -> tuple[set[str], dict[str, int]]:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ContractError("JUNIT_INVALID", f"{path.name}: {exc}") from exc
    demand(root.tag in {"testsuite", "testsuites"}, "JUNIT_INVALID",
           f"Unsupported JUnit root in {path.name}")
    suites = [root] if root.tag == "testsuite" else list(root)
    demand(bool(suites), "JUNIT_INVALID", f"No test suites in {path.name}")
    observed: set[str] = set()
    totals = dict.fromkeys(COUNTERS, 0)
    for suite in suites:
        demand(suite.tag == "testsuite" and suite.find("testsuite") is None,
               "JUNIT_INVALID", f"Nested/non-suite entry in {path.name}")
        cases = suite.findall("testcase")
        actual = dict.fromkeys(COUNTERS, 0)
        for case in cases:
            name, classname = case.get("name"), case.get("classname")
            demand(bool(name) and bool(classname), "JUNIT_INVALID",
                   f"Unidentified testcase in {path.name}")
            identity = f"{classname}::{name}"
            demand(identity not in observed, "DUPLICATE_TESTCASE",
                   f"Repeated testcase {identity} in {path.name}")
            observed.add(identity)
            statuses = [tag for tag in ("failure", "error", "skipped")
                        if case.find(tag) is not None]
            demand(len(statuses) <= 1, "JUNIT_INVALID",
                   f"Multiple terminal states for {identity}")
            actual["tests"] += 1
            for status in statuses:
                actual[{"failure": "failures", "error": "errors",
                        "skipped": "skipped"}[status]] += 1
        for key in COUNTERS:
            raw = suite.get(key)
            demand(raw is not None and raw.isdecimal()
                   and int(raw) == actual[key], "COUNTER_MISMATCH",
                   f"{path.name}: JUnit {key} differs from testcase records")
            totals[key] += actual[key]
    return observed, totals


def report_path(folder: Path, name: object, expected: str) -> Path:
    demand(name == expected, "REPORT_PATH_INVALID",
           f"Expected runner-owned file {expected}, got {name!r}")
    result = folder / expected
    demand(result.is_file() and not result.is_symlink()
           and result.resolve().parent == folder.resolve(),
           "REPORT_MISSING", f"Missing/nonlocal runner report: {expected}")
    return result


def verify_row(folder: Path, row: dict, label: str, category: str,
               test_path: str, selector: str, identities: set[str],
               seen: set[str], required: bool) -> int:
    demand(row.get("label") == label and row.get("category") == category
           and row.get("path") == test_path and row.get("selector") == selector,
           "ROW_IDENTITY_MISMATCH", f"Wrong label, class, path or selector at {label}")
    log = report_path(folder, row.get("log"), label + ".log")
    junit = report_path(folder, row.get("junit"), label + ".xml")
    demand(junit.stat().st_mtime_ns + STALE_LOG_SKEW_NS >= log.stat().st_mtime_ns,
           "STALE_REPORT", f"{label}: JUnit predates the companion log by >60s")
    demand(not row.get("report_error"), "JUNIT_INVALID",
           f"{label}: runner could not parse its own report")
    actual_ids, counts = junit_cases(junit)
    demand(not (actual_ids & seen), "DUPLICATE_TESTCASE",
           f"{label}: identity was already counted in another report")
    seen.update(actual_ids)
    demand(actual_ids == identities, "CASE_ID_MISMATCH",
           f"{label}: missing={sorted(identities - actual_ids)[:3]}, "
           f"extra={sorted(actual_ids - identities)[:3]}")
    for key in COUNTERS:
        n = row.get(key)
        demand(type(n) is int and n == counts[key], "COUNTER_MISMATCH",
               f"{label}: receipt {key} disagrees with JUnit cases")
    passed = (row.get("exit_code") == 0 and counts["tests"] > 0
              and all(counts[key] == 0 for key in ("failures", "errors", "skipped")))
    demand(type(row.get("passed")) is bool and row["passed"] == passed,
           "SUMMARY_FORGED", f"{label}: runner pass flag disagrees with actual records")
    if required:
        demand(passed, "REQUIRED_NOT_GREEN",
               f"{label}: required run failed, errored, skipped or was not executed")
    return counts["tests"]


def validate(receipt_path: Path, runner_path: Path, suite_path: Path,
             cases_path: Path, probe_path: Path, scenarios_path: Path,
             expected_source_sha: str, expected_runner_sha256: str) -> dict:
    for path, kind in ((receipt_path, "receipt"), (runner_path, "runner"),
                       (suite_path, "297 suite-manifest"),
                       (cases_path, "author testcase manifest"),
                       (probe_path, "unchanged probe"), (scenarios_path, "consent fixture")):
        check_file(path, kind)
    receipt, contract = read_json(receipt_path), read_json(cases_path)
    demand(receipt.get("schema") == RUNNER_SCHEMA and contract.get("schema") == SCHEMA,
           "SCHEMA_INVALID", "Expected #659 runner receipt and v1 consumer manifest")
    kind = contract.get("evidence_kind")
    demand(kind in ("synthetic", "real_combined"), "CANDIDATE_MISMATCH",
           "Declare synthetic or real_combined explicitly")
    label = "synthetic_fixture" if kind == "synthetic" else "combined_substrate"
    demand(contract.get("candidate_label") == label, "CANDIDATE_MISMATCH",
           f"Wrong label for {kind}")
    check_sha(expected_source_sha, HEX40, "expected_source_sha")
    check_sha(expected_runner_sha256, HEX64, "expected_runner_sha256")
    for field in ("source_sha", "combined_sha"):
        check_sha(contract.get(field), HEX40, field)
    demand(receipt.get("candidate_sha") == expected_source_sha
           == contract["source_sha"] == contract["combined_sha"],
           "SOURCE_SHA_MISMATCH", "Runner candidate, source, combined head and independent pin differ")
    for field, path, pin in (
        ("runner_sha256", runner_path, expected_runner_sha256),
        ("suite_manifest_sha256", suite_path, contract.get("suite_manifest_sha256")),
        ("probe_sha256", probe_path, contract.get("probe_sha256")),
        ("scenarios_sha256", scenarios_path, contract.get("scenarios_sha256")),
    ):
        check_sha(pin, HEX64, field + " trusted pin")
        demand(receipt.get(field) == pin and digest(path) == pin,
               "RUNNER_HASH_MISMATCH" if field == "runner_sha256" else "INPUT_HASH_MISMATCH",
               f"{field} differs from the supplied files or external pin")
    acceptance = contract.get("acceptance")
    demand(isinstance(acceptance, dict), "AUTHORITY_MISSING",
           "Author-controlled acceptance policy metadata required")
    demand(acceptance.get("rule_id") == RULE, "RULE_CHANGE_NOT_AUTHORIZED",
           "A changed numerical gate (including epsilon=2pp) needs separate author approval")
    authority = acceptance.get("authority")
    demand(isinstance(authority, dict)
           and all(isinstance(authority.get(k), str) and authority[k].strip()
                   for k in ("issuer", "decision_url", "declared_at", "scope"))
           and authority["decision_url"].startswith("https://"),
           "AUTHORITY_MISSING", "Record provenance and decision link; verify authority externally")
    paths = suite_paths(suite_path)
    required_cases, memory_cases = contract.get("required_cases"), contract.get("memory_cases")
    demand(isinstance(required_cases, dict) and set(required_cases) == set(REQUIRED)
           and isinstance(memory_cases, dict) and set(memory_cases) == set(paths),
           "CASE_MANIFEST_INVALID", "Declared probe labels or runner suite paths differ")
    probe_ids = {k: expected_ids(v, k) for k, v in required_cases.items()}
    battery_ids = {k: expected_ids(v, k) for k, v in memory_cases.items()}
    advisory = expected_ids(contract.get("advisory_cases"), "advisory")
    all_required = [i for cases in list(probe_ids.values()) + list(battery_ids.values())
                    for i in cases]
    demand(len(all_required) == len(set(all_required)), "DUPLICATE_EXPECTED_CASE",
           "A required testcase appears more than once in the manifest")
    demand(sum(map(len, battery_ids.values())) == 297, "MANIFEST_NOT_297",
           "Only the author's exact 297 identities, not a count or subset, can qualify")
    demand(receipt.get("suite_kind") == "declared"
           and receipt.get("unchanged_probe") is True
           and receipt.get("tracked_source_dirty") is False,
           "RUNNER_BOUNDARY_INVALID", "Only a clean, unchanged-probe declared suite qualifies")
    rows = receipt.get("results")
    demand(isinstance(rows, list) and len(rows) == 5 + len(paths)
           and all(isinstance(r, dict) for r in rows),
           "ROWS_INCOMPLETE", "Expected four required, one advisory and each declared memory path")
    folder = receipt_path.parent.resolve()
    seen: set[str] = set()
    for i, (name, selector) in enumerate(REQUIRED.items()):
        verify_row(folder, rows[i], name, "required", PROBE_PATH,
                   selector, probe_ids[name], seen, required=True)
    verify_row(folder, rows[4], "doc_response_4096", "advisory", PROBE_PATH,
               ADVISORY, advisory, seen, required=False)
    observed = 0
    for i, path in enumerate(paths, 1):
        observed += verify_row(folder, rows[i + 4], f"memory_suite_{i}",
                               "memory_suite", path, "", battery_ids[path], seen, required=True)
    demand(observed == 297 and receipt.get("memory_test_count") == observed
           and receipt.get("required_probes_green") is True
           and receipt.get("claimed_297_battery_green") is True
           and receipt.get("overall") == "PASS_CANDIDATE",
           "SUMMARY_FORGED", "Memory count, gate counters or candidate result differ from evidence")
    demand(all(receipt.get(k) is False for k in
               ("real_model", "real_compressor", "real_user_logs")),
           "CLAIM_SCOPE_INVALID", "Wrapper receipts cannot prove model, compressor or field-log claims")
    return {
        "verdict": "VALID_SYNTHETIC" if kind == "synthetic" else "VALID_RECEIPT",
        "candidate_sha": expected_source_sha,
        "observed_memory_cases": observed,
        "scope": "identity/completeness only; NOT certified combined execution or model evidence",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("receipt", "runner", "suite-manifest", "case-manifest", "probe", "scenarios"):
        parser.add_argument("--" + field, required=True, type=Path)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    args = parser.parse_args()
    try:
        result = validate(args.receipt, args.runner, args.suite_manifest,
                          args.case_manifest, args.probe, args.scenarios,
                          args.expected_source_sha, args.expected_runner_sha256)
    except ContractError as exc:
        print(json.dumps({"verdict": "NOT_CERTIFIED", "code": exc.code, "detail": str(exc)}))
        return 1
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"verdict": "NOT_CERTIFIED", "code": "INPUT_UNREADABLE",
                          "detail": str(exc)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
