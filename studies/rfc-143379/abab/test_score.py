"""Offline tests for the ABAB receipt gate; not evidence of Hermes correctness."""
import copy
import unittest

from score import evaluate


def example():
    sha = "a" * 64
    head = "b" * 40
    return {
        "head": head, "real_modules": True, "real_model": False,
        "real_compressor": False, "fixture_sha256": sha,
        "read_source_sha256": sha,
        "runs": [
            {"period": period, "policy": policy, "profile": f"/tmp/isolated/{period}",
             "head": head, "fixture_sha256": sha,
             "reader_observed_pre_write_snapshot": True,
             "writer_committed_before_reader_release": True,
             "read_success": True, "write_success": True,
             "disk_survived": True, "prompt_frozen": True,
             "usage_matches_read_snapshot": True,
             "cache_fresh_after_join": period.startswith("B")}
            for period, policy in zip(("A1", "B1", "A2", "B2"),
                                       ("native", "stateless", "native", "stateless"))
        ],
    }


class ABABReceiptTests(unittest.TestCase):
    def test_complete_actual_native_pattern_is_mechanism_pass(self):
        self.assertEqual(evaluate(example())["status"], "PASS_MECHANISM")

    def test_missing_period_is_not_green(self):
        data = example()
        data["runs"].pop()
        self.assertEqual(evaluate(data)["status"], "BLOCKED")

    def test_reordered_periods_are_blocked(self):
        data = example()
        data["runs"][0], data["runs"][1] = data["runs"][1], data["runs"][0]
        self.assertEqual(evaluate(data)["status"], "BLOCKED")

    def test_reused_profile_does_not_certify(self):
        data = example()
        data["runs"][3]["profile"] = data["runs"][1]["profile"]
        self.assertEqual(evaluate(data)["status"], "BLOCKED")

    def test_wrong_source_or_fixture_is_blocked(self):
        data = example()
        data["runs"][2]["head"] = "c" * 40
        self.assertEqual(evaluate(data)["status"], "BLOCKED")
        data = example()
        data["runs"][2]["fixture_sha256"] = "d" * 64
        self.assertEqual(evaluate(data)["status"], "BLOCKED")

    def test_not_real_module_or_fake_model_claim_is_blocked(self):
        for key, value in (("real_modules", False), ("real_model", True),
                           ("real_compressor", True)):
            data = example()
            data[key] = value
            self.assertEqual(evaluate(data)["status"], "BLOCKED")

    def test_stale_candidate_is_not_green(self):
        data = example()
        data["runs"][3]["cache_fresh_after_join"] = False
        self.assertEqual(evaluate(data)["status"], "FAIL_CANDIDATE")

    def test_no_bug_left_does_not_claim_candidate_gain(self):
        data = example()
        data["runs"][0]["cache_fresh_after_join"] = True
        data["runs"][2]["cache_fresh_after_join"] = True
        self.assertEqual(evaluate(data)["status"], "NO_GAP")

    def test_single_baseline_disagreement_is_inconclusive(self):
        data = example()
        data["runs"][2]["cache_fresh_after_join"] = True
        self.assertEqual(evaluate(data)["status"], "INCONCLUSIVE")

    def test_unproven_order_blocks_certification(self):
        data = example()
        data["runs"][1]["writer_committed_before_reader_release"] = False
        self.assertEqual(evaluate(data)["status"], "BLOCKED")

    def test_invalid_usage_and_partial_disk_fail_even_if_cache_fresh(self):
        for key in ("usage_matches_read_snapshot", "disk_survived"):
            data = copy.deepcopy(example())
            data["runs"][3][key] = False
            self.assertEqual(evaluate(data)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
