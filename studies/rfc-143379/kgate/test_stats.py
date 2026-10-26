"""Pure stdlib tests: python3 -m unittest discover -s <kgate> -p test_stats.py."""
from dataclasses import asdict, replace
import math
import unittest
from typing import cast

from stats import (BINS, PairedRow, Probe, cluster_plan, digest, evaluate,
                   paired_counts, sample_size, seed_cluster_bootstrap, simultaneous_lcb)


def fixture(y10=1, y0=0):
    probes = [Probe(s, f"p{i}", 1, "a" * 64, "synthetic:test", f"literal-{s}-{i}")
              for s in (1, 2) for i in (0, 1)]
    rows = [PairedRow(p, c, r, r, r, y10 if p.probe_id == "p0" else 0, y0,
                      digest([asdict(p) for p in probes]), 10, 0, 10, 20, 100,
                      "K0,K10" if p.session_seed == 1 else "K10,K0",
                      "model_exact_recitation", "test-model", "b" * 64, "c" * 64,
                      "native", "real", 0) for c, r in BINS for p in probes]
    return probes, rows


class StatisticsTests(unittest.TestCase):
    def test_power_comment_exact_numbers(self):
        self.assertEqual(sample_size(comparisons=1), 2474)
        self.assertEqual(sample_size(), 5226)
        self.assertEqual(sample_size(simultaneous_power=True), 10240)

    def test_design_effect(self):
        plan = cluster_plan(10240)
        self.assertAlmostEqual(plan["design_effect"], 1.79)
        self.assertEqual(plan["raw_n"], 18330)
        self.assertEqual(plan["seeds"], 230)
        self.assertEqual(cluster_plan(10240, rho=0)["seeds"], 128)

    def test_neutral_zero_margin_has_no_finite_power(self):
        with self.assertRaises(ValueError):
            sample_size(epsilon=0)

    def test_paired_discordance_not_unpaired_se(self):
        pairs = [(1, 0)] * 3 + [(0, 1)] + [(0, 0)] * 6
        result = paired_counts(pairs)
        self.assertEqual((result["b"], result["c"], result["n"]), (3, 1, 10))
        self.assertAlmostEqual(result["delta"], .2)
        self.assertAlmostEqual(result["se"], math.sqrt(.036))
        ci = simultaneous_lcb(pairs)
        self.assertAlmostEqual(ci["z"], 2.772921294608661, places=6)
        self.assertLess(ci["lcb"], simultaneous_lcb(pairs, comparisons=1)["lcb"])

    def test_invalid_pairs(self):
        for pairs in ([], [(2, 0)], [(True, 0)]):
            with self.assertRaises(ValueError):
                paired_counts(pairs)

    def test_schema_roundtrip_and_literal_validation(self):
        _, rows = fixture()
        self.assertEqual(PairedRow.from_dict(rows[0].to_dict()), rows[0])
        with self.assertRaises(ValueError):
            replace(rows[0].probe, source_digest="A" * 64)
        with self.assertRaises(ValueError):
            replace(rows[0], ratio_actual=float("nan"))
        with self.assertRaises(ValueError):
            replace(rows[0], y10=True)

    def test_missing_prohibited_outcome_is_not_assumed_clean(self):
        probes, rows = fixture()
        fields = rows[0].to_dict()
        del fields["prohibited_regressions"]
        with self.assertRaises(TypeError):
            PairedRow.from_dict(fields)
        result = evaluate(rows, probes, approved=cast(bool, "yes"))
        self.assertIn("proposal_not_approved", result["reasons"])

    def test_whole_cluster_resampling(self):
        _, rows = fixture()
        rows = [replace(r, y10=int(r.probe.session_seed == 1), y0=int(r.probe.session_seed == 2))
                for r in rows[:4]]
        result = seed_cluster_bootstrap(rows, draws=7200, seed=8)
        self.assertEqual(result["clusters"], 2)
        self.assertEqual(result["lcb"], -1)
        self.assertEqual(result, seed_cluster_bootstrap(rows, draws=7200, seed=8))
        with self.assertRaises(ValueError):
            seed_cluster_bootstrap(rows[:2])
        with self.assertRaises(ValueError):
            seed_cluster_bootstrap(rows, draws=100)

    def gate(self, rows, probes, **kw):
        return evaluate(rows, probes, approved=True, min_effective_n=2, min_seeds=2,
                        rho=0, draws=7200, **kw)

    def test_complete_positive_proposal_pass(self):
        probes, rows = fixture()
        self.assertEqual(self.gate(rows, probes)["status"], "PASS")

    def test_negative_proposal_fail(self):
        probes, rows = fixture(0, 1)
        rows = [replace(r, y0=0) if r.probe.probe_id == "p1" else r for r in rows]
        self.assertEqual(self.gate(rows, probes)["status"], "FAIL")

    def test_default_requires_approval_and_power(self):
        probes, rows = fixture()
        result = evaluate(rows, probes)
        self.assertEqual(result["status"], "INSUFFICIENT")
        self.assertIn("proposal_not_approved", result["reasons"])
        self.assertIn("missing_or_underpowered_bin", result["reasons"])

    def test_refusals_remain_scored(self):
        probes, rows = fixture()
        probes[0] = replace(probes[0], source_access="refused")
        h = digest([asdict(p) for p in probes])
        lookup = {(p.session_seed, p.probe_id): p for p in probes}
        rows = [replace(r, probe=lookup[(r.probe.session_seed, r.probe.probe_id)], manifest_digest=h)
                for r in rows]
        self.assertEqual(self.gate(rows, probes)["status"], "PASS")
        self.assertEqual(self.gate(rows[1:], probes)["status"], "INSUFFICIENT")

    def test_fail_closed_controls(self):
        probes, rows = fixture()
        cases = [rows[4:], rows + [rows[0]],
                 [replace(rows[0], ratio_actual=9), *rows[1:]],
                 [replace(rows[0], manifest_digest="d" * 64), *rows[1:]],
                 [replace(rows[0], measurement="deterministic_boundary"), *rows[1:]],
                 [replace(rows[0], model="other"), *rows[1:]],
                 [replace(rows[0], summary_tokens=200), *rows[1:]],
                 [replace(rows[0], trajectory_digest="d" * 64), *rows[1:]],
                 [replace(rows[0], token_budget=101), *rows[1:]],
                 [replace(r, arm_order="K0,K10") for r in rows]]
        for case in cases:
            self.assertEqual(self.gate(case, probes)["status"], "INSUFFICIENT")

    def test_prohibited_regression_hard_fails(self):
        probes, rows = fixture()
        rows[0] = replace(rows[0], prohibited_regressions=1)
        self.assertEqual(evaluate(rows, probes)["status"], "FAIL")

    def test_degenerate_sample_does_not_certify_population(self):
        probes, rows = fixture(0, 0)
        self.assertEqual(self.gate(rows, probes)["status"], "INSUFFICIENT")


if __name__ == "__main__":
    unittest.main()
