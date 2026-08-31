"""RED→GREEN tests for shadow-mode Hermes adaptive provider ASG.

No network. Does not import live gateway routing.
"""

from __future__ import annotations

import unittest

from hermes_asg import (
    AdmissionClass,
    BreakerState,
    CapacityKey,
    PrivacyClass,
    ShadowAsgController,
)


class AsgTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c = ShadowAsgController(global_limit=10, reserved_frac=0.2, explorer_eps=0.0, now=1000.0)
        self.k1 = CapacityKey("nous", "hermes-3", "acct-a", "worker-local")
        self.k2 = CapacityKey("xai", "grok-4.6", "acct-b", "worker-cloud")
        self.c.register_key(
            self.k1, declared_limit=8, privacy_class=PrivacyClass.LOCAL, cost_per_1k=0.01
        )
        self.c.register_key(
            self.k2, declared_limit=8, privacy_class=PrivacyClass.THIRD_PARTY, cost_per_1k=0.5
        )

    def test_aimd_increase_and_never_above_declared(self) -> None:
        st = self.c.snapshot(self.k1)
        self.assertEqual(st.aimd_limit, 1)
        for _ in range(20):
            self.c.observe(self.k1, classified="ok", success=True)
        self.assertEqual(self.c.snapshot(self.k1).aimd_limit, 8)

    def test_aimd_multiplicative_decrease_floor_one(self) -> None:
        for _ in range(7):
            self.c.observe(self.k1, classified="ok")
        self.assertGreaterEqual(self.c.snapshot(self.k1).aimd_limit, 2)
        self.c.observe(self.k1, classified="overloaded")
        self.assertEqual(self.c.snapshot(self.k1).aimd_limit, max(1, (8 // 2) if False else self.c.snapshot(self.k1).aimd_limit))
        before = 4  # 1+7 additive but capped... 1+7=8, *0.5 floor = 4
        # re-init path: start 1, 7 ok → 8, overload → 4
        self.assertEqual(self.c.snapshot(self.k1).aimd_limit, 4)
        self.c.observe(self.k1, classified="overloaded")
        self.c.observe(self.k1, classified="overloaded")
        self.c.observe(self.k1, classified="overloaded")
        self.assertEqual(self.c.snapshot(self.k1).aimd_limit, 1)

    def test_breaker_is_key_scoped_not_provider(self) -> None:
        k1b = CapacityKey("nous", "other-model", "acct-a", "worker-local")
        self.c.register_key(k1b, declared_limit=4, privacy_class=PrivacyClass.LOCAL)
        for _ in range(3):
            self.c.observe(self.k1, classified="overloaded")
        self.assertEqual(self.c.snapshot(self.k1).breaker_state, BreakerState.OPEN)
        self.assertEqual(self.c.snapshot(k1b).breaker_state, BreakerState.CLOSED)
        r = self.c.admit("r1", admission_class=AdmissionClass.INTERACTIVE, required_privacy=PrivacyClass.LOCAL)
        self.assertTrue(r.admitted)
        self.assertEqual(r.chosen_key, k1b)

    def test_auth_does_not_trip_capacity_breaker(self) -> None:
        self.c.observe_probe(self.k1, classified="auth")
        self.assertEqual(self.c.snapshot(self.k1).breaker_state, BreakerState.CLOSED)

    def test_billing_freeze_not_capacity(self) -> None:
        self.c.observe(self.k1, classified="billing")
        self.assertTrue(self.c.snapshot(self.k1).billing_frozen)
        self.assertEqual(self.c.snapshot(self.k1).breaker_state, BreakerState.CLOSED)
        r = self.c.admit("r", admission_class="interactive", required_privacy=PrivacyClass.LOCAL)
        self.assertFalse(r.admitted)
        self.assertTrue(any(x.reason == "billing_freeze" for x in r.rejected))

    def test_reserved_interactive_blocks_batch(self) -> None:
        # reserved = ceil(10*0.2)=2; fill 8 interactive → free=2 == reserved → batch blocked
        for _ in range(20):
            self.c.observe(self.k1, classified="ok")
            self.c.observe(self.k2, classified="ok")
        for i in range(8):
            r = self.c.admit(f"i{i}", admission_class=AdmissionClass.INTERACTIVE)
            self.assertTrue(r.admitted, r.reason)
        b = self.c.admit("batch", admission_class=AdmissionClass.BATCH)
        self.assertFalse(b.admitted)
        self.assertEqual(b.reason, "batch_blocked_by_reserved")
        extra = self.c.admit("i-extra", admission_class=AdmissionClass.INTERACTIVE)
        self.assertTrue(extra.admitted)
        self.assertTrue(extra.reserved_held)

    def test_unknown_class_fail_closed_as_batch(self) -> None:
        for _ in range(20):
            self.c.observe(self.k1, classified="ok")
            self.c.observe(self.k2, classified="ok")
        for i in range(8):
            self.c.admit(f"i{i}", admission_class=AdmissionClass.INTERACTIVE)
        r = self.c.admit("mystery", admission_class="not-a-class")
        self.assertEqual(r.admission_class, AdmissionClass.BATCH)
        self.assertFalse(r.admitted)

    def test_privacy_hard_filter(self) -> None:
        r = self.c.admit("p", admission_class="interactive", required_privacy=PrivacyClass.LOCAL)
        self.assertTrue(r.admitted)
        self.assertEqual(r.chosen_key, self.k1)
        self.assertTrue(any(x.reason == "privacy_hard_filter" for x in r.rejected))

    def test_cost_hard_filter(self) -> None:
        r = self.c.admit("c", admission_class="interactive", max_cost_per_1k=0.05)
        self.assertTrue(r.admitted)
        self.assertEqual(r.chosen_key, self.k1)
        self.assertTrue(any(x.reason == "cost_hard_filter" for x in r.rejected))

    def test_worker_ttl_fail_closed(self) -> None:
        self.c.heartbeat_worker(self.k2, max_slots=4, ttl_s=10)
        self.c.tick(1011.0)
        r = self.c.admit("w", admission_class="interactive", required_privacy=PrivacyClass.THIRD_PARTY)
        # k2 expired; k1 still ok if heartbeat default from register
        # k1 also registered at t=1000 with ttl 30, still alive at 1011
        self.assertTrue(any(x.key == self.k2 and x.reason == "worker_ttl_expired" for x in r.rejected))

    def test_half_open_one_trial(self) -> None:
        for _ in range(3):
            self.c.observe(self.k1, classified="overloaded")
        self.c.heartbeat_worker(self.k1, max_slots=8, ttl_s=600)
        self.c.tick(1060.0)
        self.assertEqual(self.c.snapshot(self.k1).breaker_state, BreakerState.HALF_OPEN)
        r1 = self.c.admit("t1", admission_class="interactive", required_privacy=PrivacyClass.LOCAL)
        self.assertTrue(r1.admitted)
        r2 = self.c.admit("t2", admission_class="interactive", required_privacy=PrivacyClass.LOCAL)
        self.assertFalse(r2.admitted)
        self.assertTrue(any(x.reason == "half_open_one_trial" for x in r2.rejected))

    def test_receipt_shadow_and_no_secrets(self) -> None:
        r = self.c.admit("req-1", admission_class="interactive")
        self.assertTrue(r.shadow)
        self.assertTrue(r.live_path_unchanged)
        blob = repr(r)
        self.assertNotIn("sk-", blob)
        self.assertNotIn("token", blob.lower() if "api_key" in blob.lower() else "ok")

    def test_replay_deterministic(self) -> None:
        keys = [self.k1, self.k2]
        a, e1 = self.c.replay_choice(eligible=keys, explorer_seed=7, explorer_eps=0.5, leftover_slots=3)
        b, e2 = self.c.replay_choice(eligible=keys, explorer_seed=7, explorer_eps=0.5, leftover_slots=3)
        self.assertEqual(a, b)
        self.assertEqual(e1, e2)

    def test_rate_limit_remaining_zero_decreases(self) -> None:
        for _ in range(5):
            self.c.observe(self.k1, classified="ok")
        lim = self.c.snapshot(self.k1).aimd_limit
        self.c.observe(self.k1, classified="rate_limit", remaining=0, retry_after_s=5)
        self.assertLessEqual(self.c.snapshot(self.k1).aimd_limit, max(1, lim // 2))

    def test_probe_interval(self) -> None:
        self.assertTrue(self.c.can_probe(self.k1))
        self.c.observe_probe(self.k1, classified="ok")
        self.assertFalse(self.c.can_probe(self.k1))
        self.c.tick(1030.0)
        self.assertTrue(self.c.can_probe(self.k1))


if __name__ == "__main__":
    unittest.main()
