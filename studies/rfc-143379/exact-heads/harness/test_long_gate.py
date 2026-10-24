"""Synthetic score-receipt gate arithmetic; not native Hermes verification."""
import unittest
from long_gate import REQUIRED, evaluate


def example():
    return {"metadata": {**{key: True for key in REQUIRED}, "k": 10},
            "max_cycle": 301,
            "rows": [{"ratio": ratio, "cycle": cycle, "probes": 100,
                      "baseline_correct": 20, "k_correct": 20,
                      "probe_set_id": f"shared-{ratio}-{cycle}"}
                     for ratio in (4, 8) for cycle in (300, 301)]}


class LongGateTests(unittest.TestCase):
    def test_synthetic_pass_only_when_complete(self):
        self.assertEqual(evaluate(example())["status"], "PASS")
        bad = example()
        bad["rows"].pop()
        self.assertEqual(evaluate(bad)["status"], "BLOCKED")

    def test_any_negative_point_fails(self):
        data = example()
        data["rows"][3]["k_correct"] = 19
        result = evaluate(data)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["minimum_delta_pp"], -1)

    def test_mocked_paraphrase_is_blocked(self):
        data = example()
        data["metadata"]["real_paraphrase"] = False
        self.assertEqual(evaluate(data)["status"], "BLOCKED")

    def test_incomplete_300_cycle_only_is_blocked(self):
        data = example()
        data["max_cycle"] = 300
        self.assertEqual(evaluate(data)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
