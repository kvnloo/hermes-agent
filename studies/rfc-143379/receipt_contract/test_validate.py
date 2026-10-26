"""Synthetic, stdlib-only contract tests. No Hermes runtime or real RFC cases run."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

from validate import ADVISORY, ContractError, REQUIRED, validate


CANDIDATE = "a" * 40  # Synthetic fixture identity, NEVER a published combined source.
RUNNER = b"synthetic stand-in for #659 runner bytes; do not run\n"
SUITE = b"tests/tools/test_memory_tool.py\n"
PROBE = b"synthetic probe fixture; not a #654 test\n"
SCENARIOS = b"synthetic consent fixture; not real user data\n"
MEMORY_PATH = "tests/tools/test_memory_tool.py"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_xml(path: Path, identities: list[str], *, skipped: bool = False) -> None:
    root = ET.Element("testsuite", tests=str(len(identities)), failures="0",
                      errors="0", skipped="1" if skipped else "0")
    for i, identity in enumerate(identities):
        classname, name = identity.split("::", 1)
        test = ET.SubElement(root, "testcase", classname=classname, name=name)
        if skipped and i == 0:
            ET.SubElement(test, "skipped", message="synthetic skip")
    path.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))


class ReceiptContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="rfc143379-receipt-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.receipt_path = self.root / "receipt.json"
        self.runner_path = self.root / "run_fixed_substrate.py"
        self.suite_path = self.root / "297-suite-paths.txt"
        self.cases_path = self.root / "author-case-manifest.json"
        self.probe_path = self.root / "test_real_checkout.py"
        self.scenarios_path = self.root / "consent_scenarios.json"
        for path, data in (
            (self.runner_path, RUNNER), (self.suite_path, SUITE),
            (self.probe_path, PROBE), (self.scenarios_path, SCENARIOS),
        ):
            path.write_bytes(data)

        required_cases = {
            name: [f"probe.Tests::{selector.split(' or ')[0]}"]
            for name, selector in REQUIRED.items()
        }
        memory_cases = {MEMORY_PATH: [f"memory.Tests::test_case_{i:03d}"
                                      for i in range(297)]}
        advisory = [f"probe.Tests::{ADVISORY}"]
        self.contract = {
            "schema": "rfc143379.receipt-contract.v1",
            "evidence_kind": "synthetic",
            "candidate_label": "synthetic_fixture",
            "source_sha": CANDIDATE,
            "combined_sha": CANDIDATE,
            "runner_sha256": sha(RUNNER),
            "suite_manifest_sha256": sha(SUITE),
            "probe_sha256": sha(PROBE),
            "scenarios_sha256": sha(SCENARIOS),
            "required_cases": required_cases,
            "memory_cases": memory_cases,
            "advisory_cases": advisory,
            "acceptance": {
                "rule_id": "rfc143379-author-297-zero-gaps-v1",
                "authority": {
                    "issuer": "SYNTHETIC TEST ONLY",
                    "decision_url": "https://example.invalid/synthetic-not-authority",
                    "declared_at": "2026-10-26",
                    "scope": "Synthetic receipt-consumer mechanics; no RFC acceptance",
                },
            },
        }
        rows = []
        for name, selector in REQUIRED.items():
            rows.append(self.make_row(name, "required",
                                      "tests/tools/test_rfc_homework.py",
                                      selector, required_cases[name]))
        rows.append(self.make_row("doc_response_4096", "advisory",
                                  "tests/tools/test_rfc_homework.py",
                                  ADVISORY, advisory))
        rows.append(self.make_row("memory_suite_1", "memory_suite",
                                  MEMORY_PATH, "", memory_cases[MEMORY_PATH]))
        self.receipt = {
            "schema": "rfc143379.shared-falsifiers.v1",
            "candidate_sha": CANDIDATE,
            "probe_sha256": sha(PROBE),
            "scenarios_sha256": sha(SCENARIOS),
            "runner_sha256": sha(RUNNER),
            "suite_manifest_sha256": sha(SUITE),
            "unchanged_probe": True,
            "tracked_source_dirty": False,
            "suite_kind": "declared",
            "memory_test_count": 297,
            "required_probes_green": True,
            "claimed_297_battery_green": True,
            "overall": "PASS_CANDIDATE",
            "real_model": False,
            "real_compressor": False,
            "real_user_logs": False,
            "results": rows,
        }
        self.save()

    def make_row(self, label: str, category: str, path: str,
                 selector: str, identities: list[str]) -> dict:
        (self.root / (label + ".log")).write_text(
            "SYNTHETIC TEST DATA; no Hermes checkout was run\n", encoding="utf-8")
        write_xml(self.root / (label + ".xml"), identities)
        return {
            "label": label, "category": category, "path": path,
            "log": label + ".log", "junit": label + ".xml",
            "selector": selector, "exit_code": 0, "tests": len(identities),
            "failures": 0, "errors": 0, "skipped": 0, "passed": True,
        }

    def save(self) -> None:
        self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
        self.cases_path.write_text(json.dumps(self.contract), encoding="utf-8")

    def check(self) -> dict:
        return validate(self.receipt_path, self.runner_path, self.suite_path,
                        self.cases_path, self.probe_path, self.scenarios_path,
                        CANDIDATE, sha(RUNNER))

    def rejected(self, code: str) -> None:
        self.save()
        with self.assertRaises(ContractError) as raised:
            self.check()
        self.assertEqual(raised.exception.code, code)

    def test_valid_synthetic_receipt_is_never_certified_execution(self) -> None:
        result = self.check()
        self.assertEqual(result["verdict"], "VALID_SYNTHETIC")
        self.assertEqual(result["observed_memory_cases"], 297)
        self.assertIn("NOT certified combined execution", result["scope"])

    def test_missing_author_selected_297_case_manifest(self) -> None:
        self.cases_path.unlink()
        with self.assertRaises(ContractError) as caught:
            self.check()
        self.assertEqual(caught.exception.code, "MANIFEST_MISSING")

    def test_subset_manifest_cannot_pass_by_matching_297_summary(self) -> None:
        self.contract["memory_cases"][MEMORY_PATH].pop()
        self.rejected("MANIFEST_NOT_297")

    def test_wrong_source_sha(self) -> None:
        self.receipt["candidate_sha"] = "b" * 40
        self.rejected("SOURCE_SHA_MISMATCH")

    def test_missing_combined_source_sha(self) -> None:
        self.contract["combined_sha"] = None
        self.rejected("IDENTITY_INVALID")

    def test_mismatched_candidate_label(self) -> None:
        self.contract["candidate_label"] = "historical_readfix"
        self.rejected("CANDIDATE_MISMATCH")

    def test_wrong_runner_sha(self) -> None:
        self.receipt["runner_sha256"] = "b" * 64
        self.rejected("RUNNER_HASH_MISMATCH")

    def test_suite_manifest_digest_mismatch(self) -> None:
        self.receipt["suite_manifest_sha256"] = "b" * 64
        self.rejected("INPUT_HASH_MISMATCH")

    def test_duplicate_testcase_within_junit(self) -> None:
        path = self.root / "memory_suite_1.xml"
        tree = ET.parse(path)
        entries = tree.getroot().findall("testcase")
        entries[1].set("name", entries[0].get("name"))
        tree.write(path, encoding="utf-8")
        self.rejected("DUPLICATE_TESTCASE")

    def test_duplicate_expected_testcase_rejected(self) -> None:
        values = self.contract["memory_cases"][MEMORY_PATH]
        values[1] = values[0]
        self.rejected("DUPLICATE_EXPECTED_CASE")

    def test_skipped_required_case(self) -> None:
        write_xml(self.root / "read_dispatch.xml",
                  self.contract["required_cases"]["read_dispatch"], skipped=True)
        self.receipt["results"][0]["skipped"] = 1
        self.receipt["results"][0]["passed"] = False
        self.rejected("REQUIRED_NOT_GREEN")

    def test_skipped_memory_case(self) -> None:
        write_xml(self.root / "memory_suite_1.xml",
                  self.contract["memory_cases"][MEMORY_PATH], skipped=True)
        self.receipt["results"][5]["skipped"] = 1
        self.receipt["results"][5]["passed"] = False
        self.rejected("REQUIRED_NOT_GREEN")

    def test_forged_junit_summary_counters(self) -> None:
        path = self.root / "memory_suite_1.xml"
        tree = ET.parse(path)
        tree.getroot().set("tests", "298")
        tree.write(path, encoding="utf-8")
        self.rejected("COUNTER_MISMATCH")

    def test_forged_receipt_summary_counters(self) -> None:
        self.receipt["memory_test_count"] = 298
        self.rejected("SUMMARY_FORGED")

    def test_forged_per_row_counters(self) -> None:
        self.receipt["results"][5]["tests"] = 298
        self.rejected("COUNTER_MISMATCH")

    def test_stale_junit_old_relative_to_own_log(self) -> None:
        old = time.time() - 3600
        os.utime(self.root / "read_dispatch.xml", (old, old))
        self.rejected("STALE_REPORT")

    def test_stale_green_junit_cannot_override_failed_exit(self) -> None:
        self.receipt["results"][0]["exit_code"] = 1
        self.rejected("SUMMARY_FORGED")

    def test_missing_junit(self) -> None:
        (self.root / "read_dispatch.xml").unlink()
        self.rejected("REPORT_MISSING")

    def test_runner_selftests_not_candidate_memory_battery(self) -> None:
        self.receipt["suite_kind"] = "neighboring_only"
        self.rejected("RUNNER_BOUNDARY_INVALID")

    def test_mismatched_identity_even_with_297_count(self) -> None:
        self.contract["memory_cases"][MEMORY_PATH][0] = "memory.Tests::different_000"
        self.rejected("CASE_ID_MISMATCH")

    def test_unapproved_two_pp_gate_rejected(self) -> None:
        self.contract["acceptance"]["rule_id"] = "rfc143379-epsilon-2pp"
        self.rejected("RULE_CHANGE_NOT_AUTHORIZED")

    def test_missing_acceptance_authority(self) -> None:
        self.contract["acceptance"]["authority"] = None
        self.rejected("AUTHORITY_MISSING")

    def test_real_combined_label_cannot_be_self_assigned(self) -> None:
        self.contract["evidence_kind"] = "real_combined"
        self.rejected("CANDIDATE_MISMATCH")

    def test_extra_runner_row_not_silently_ignored(self) -> None:
        self.receipt["results"].append(copy.deepcopy(self.receipt["results"][0]))
        self.rejected("ROWS_INCOMPLETE")

    def test_probe_digest_must_match_unchanged_source(self) -> None:
        self.probe_path.write_bytes(b"untrusted mutated probe\n")
        self.rejected("INPUT_HASH_MISMATCH")


if __name__ == "__main__":
    unittest.main()
