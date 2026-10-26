"""Offline runner regressions. These never execute Hermes or a live model."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("fixed_runner", HERE / "run_fixed_substrate.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def report(*cases: str, tests: int | None = None, failures: int = 0,
           errors: int = 0, skipped: int = 0) -> str:
    return (f'<testsuites><testsuite tests="{len(cases) if tests is None else tests}" '
            f'failures="{failures}" errors="{errors}" skipped="{skipped}">'
            + "".join(cases) + '</testsuite></testsuites>')


PASS = '<testcase classname="synthetic" name="test_example"/>'


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rfc-runner-selftest-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checkout = self.root / "checkout"
        self.out = self.root / "results"
        (self.checkout / "scripts").mkdir(parents=True)
        (self.checkout / "tests/tools").mkdir(parents=True)
        self.out.mkdir()
        (self.checkout / "tests/tools/test_sample.py").write_text("# synthetic runner fixture\n")
        executable = self.checkout / "scripts/run_tests.sh"
        executable.write_text(
            f'#!{sys.executable}\n'
            'from pathlib import Path\nimport sys\n'
            'report = Path("response.xml")\n'
            'if report.exists():\n'
            '    output = next(a.split("=", 1)[1] for a in sys.argv if a.startswith("--junitxml="))\n'
            '    Path(output).write_bytes(report.read_bytes())\n'
            'sys.exit(0)\n')
        executable.chmod(0o700)

    def execute(self, xml=None, path="tests/tools/test_sample.py"):
        if xml is not None:
            (self.checkout / "response.xml").write_text(xml)
        return runner.run_one(self.checkout, self.out, os.environ.copy(),
                              "probe", "required", path)

    def test_fresh_report_passes(self):
        self.assertTrue(self.execute(report(PASS))["passed"])

    def test_missing_report_never_passes(self):
        self.assertFalse(self.execute()["passed"])

    def test_stale_success_cannot_certify_a_reportless_run(self):
        (self.out / "probe.xml").write_text(report(PASS))
        self.assertFalse(self.execute()["passed"])

    def test_child_failure_cannot_hide_behind_green_summary(self):
        case = '<testcase name="test_bad"><failure message="regression"/></testcase>'
        self.assertFalse(self.execute(report(case))["passed"])

    def test_297_claim_requires_297_actual_cases(self):
        self.assertFalse(self.execute(report(PASS, tests=297))["passed"])

    def test_empty_summary_cannot_certify_tests(self):
        self.assertFalse(self.execute(report(tests=1))["passed"])

    def test_malformed_report_is_a_failed_receipt_not_a_crash(self):
        self.assertFalse(self.execute("<testsuites>")["passed"])

    def test_real_failure_is_preserved(self):
        case = '<testcase name="test_bad"><failure/></testcase>'
        self.assertFalse(self.execute(report(case, failures=1))["passed"])

    def test_skipped_case_is_not_green(self):
        case = '<testcase name="test_skip"><skipped/></testcase>'
        self.assertFalse(self.execute(report(case, skipped=1))["passed"])

    def test_duplicate_case_identity_is_not_extra_coverage(self):
        self.assertFalse(self.execute(report(PASS, PASS))["passed"])

    def test_test_file_symlink_cannot_escape_checkout(self):
        outside = self.root / "outside.py"
        outside.write_text("# never run\n")
        (self.checkout / "tests/tools/test_escape.py").symlink_to(outside)
        self.assertFalse(self.execute(report(PASS), "tests/tools/test_escape.py")["passed"])

    def test_manifest_cannot_count_one_file_twice_via_alias(self):
        manifest = self.root / "battery.txt"
        manifest.write_text("tests/tools/test_sample.py\ntests//tools/test_sample.py\n")
        with self.assertRaises(ValueError):
            runner.suite_paths(manifest)

    def test_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            runner.validate_path("tests/../outside.py")

    def test_nonempty_output_is_rejected_without_destroying_receipt(self):
        study = self.root / "study"
        study.mkdir()
        for name, text in (("run_fixed_substrate.py", (HERE / "run_fixed_substrate.py").read_text()),
                           ("test_real_checkout.py", "# synthetic fixture\n"),
                           ("consent_scenarios.json", "[]\n")):
            (study / name).write_text(text)
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.checkout), *args], text=True).strip()
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Synthetic Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "synthetic fixture")
        head = git("rev-parse", "HEAD")
        old = '{"overall":"PRIOR_EVIDENCE_DO_NOT_OVERWRITE"}\n'
        (self.out / "receipt.json").write_text(old)
        result = subprocess.run([sys.executable, str(study / "run_fixed_substrate.py"),
                                 str(self.checkout), head, str(self.out)], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual((self.out / "receipt.json").read_text(), old)


if __name__ == "__main__":
    unittest.main()
