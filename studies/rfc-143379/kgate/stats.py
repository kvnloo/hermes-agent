"""Paired non-inferiority proposal; never a replacement for RFC143379's gate.

Rates and margins are fractions, not percentage points. Normal intervals and
power are planning approximations. Bootstrap resamples whole session seeds.
"""
from collections import defaultdict
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import random
import re
from statistics import NormalDist

CYCLES = (300, 400, 500, 600, 700, 800)
RATIOS = (4, 6, 8)
BINS = tuple((c, r) for c in CYCLES for r in RATIOS)


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True)
class Probe:
    session_seed: int
    probe_id: str
    source_cycle: int
    source_digest: str
    source_scope: str
    target_literal: str
    source_access: str = "available"
    stratum: str = "historical"
    eligible: bool = True

    def __post_init__(self):
        if (type(self.session_seed) is not int or type(self.source_cycle) is not int
                or self.source_cycle < 1):
            raise ValueError("invalid seed/source cycle")
        if not all((self.probe_id, self.source_scope, self.target_literal)):
            raise ValueError("empty source identity")
        if not re.fullmatch(r"[0-9a-f]{64}", self.source_digest):
            raise ValueError("source_digest must be literal lowercase SHA256")
        if self.source_access not in {"available", "unresolved", "refused"}:
            raise ValueError("invalid source_access")
        if type(self.eligible) is not bool:
            raise ValueError("eligibility must be explicit boolean")


@dataclass(frozen=True)
class PairedRow:
    probe: Probe
    cycle: int
    ratio_target: int
    ratio_actual: float  # K10; K0 is recorded separately, never assumed matched
    ratio_actual0: float
    y10: int
    y0: int
    manifest_digest: str
    retained_K_tokens: int
    retained_K0_tokens: int
    summary_tokens: int
    summary0_tokens: int
    token_budget: int
    arm_order: str
    measurement: str
    model: str
    scorer_digest: str
    trajectory_digest: str
    pruning: str
    paraphrase: str
    prohibited_regressions: int

    def __post_init__(self):
        if any(type(y) is not int or y not in (0, 1) for y in (self.y10, self.y0)):
            raise ValueError("paired outcomes must be binary integers")
        if (type(self.cycle) is not int or self.cycle < self.probe.source_cycle
                or type(self.ratio_target) is not int or self.ratio_target not in RATIOS):
            raise ValueError("ineligible cycle/ratio")
        if self.measurement not in {"model_exact_recitation", "deterministic_boundary"}:
            raise ValueError("unknown measurement kind")
        if not all(isinstance(s, str) and s for s in (self.model, self.pruning, self.paraphrase)):
            raise ValueError("explicit model and controls required")
        for x in (self.ratio_actual, self.ratio_actual0):
            if not math.isfinite(x) or x <= 0:
                raise ValueError("invalid realized ratio")
        for x in (self.manifest_digest, self.scorer_digest, self.trajectory_digest):
            if not re.fullmatch(r"[0-9a-f]{64}", x):
                raise ValueError("invalid digest")
        if self.arm_order not in {"K0,K10", "K10,K0"}:
            raise ValueError("invalid arm order")
        counts = (self.retained_K_tokens, self.retained_K0_tokens, self.summary_tokens,
                  self.summary0_tokens, self.token_budget, self.prohibited_regressions)
        if any(type(n) is not int or n < 0 for n in counts) or self.token_budget == 0:
            raise ValueError("invalid budget/count")

    def to_dict(self):
        # Flat public paired-manifest format, convenient for CSV/JSONL joins.
        fields = asdict(self)
        return {**fields.pop("probe"), **fields}

    @classmethod
    def from_dict(cls, fields):
        fields = dict(fields)
        probe = Probe(**{k: fields.pop(k) for k in Probe.__dataclass_fields__})
        return cls(probe=probe, **fields)


def paired_counts(pairs):
    pairs = list(pairs)
    if not pairs or any(type(a) is not int or type(b) is not int or
                        a not in (0, 1) or b not in (0, 1) for a, b in pairs):
        raise ValueError("nonempty binary pairs required")
    n = len(pairs)
    b = sum(a == 1 and z == 0 for a, z in pairs)
    c = sum(a == 0 and z == 1 for a, z in pairs)
    delta, q = (b - c) / n, (b + c) / n
    return {"n": n, "b": b, "c": c, "delta": delta, "q": q,
            "se": math.sqrt(max(0.0, q - delta * delta) / n)}


def simultaneous_lcb(pairs, alpha=.05, comparisons=18):
    if not 0 < alpha < 1 or type(comparisons) is not int or comparisons < 1:
        raise ValueError("invalid familywise alpha/comparisons")
    result = paired_counts(pairs)
    z = NormalDist().inv_cdf(1 - alpha / comparisons)
    return {**result, "z": z, "lcb": max(-1., result["delta"] - z * result["se"])}


def seed_cluster_bootstrap(rows, *, alpha=.05, comparisons=18, draws=20000, seed=0):
    """Percentile lower bound, resampling seeds with replacement (not rows).

    The statistic is the probe-weighted mean; variable-sized seed clusters retain
    all their rows. This is an approximate CI, not a finite-sample guarantee.
    """
    if not 0 < alpha < 1 or comparisons < 1 or draws < math.ceil(20 * comparisons / alpha):
        raise ValueError("need >=20 expected draws in the Bonferroni lower tail")
    clusters = defaultdict(list)
    for row in rows:
        clusters[row.probe.session_seed].append(row.y10 - row.y0)
    if len(clusters) < 2:
        raise ValueError("at least two independent seeds required")
    totals = [(sum(v), len(v)) for _, v in sorted(clusters.items())]
    rng = random.Random(seed)
    samples = []
    for _ in range(draws):
        picked = rng.choices(totals, k=len(totals))
        samples.append(sum(s for s, _ in picked) / sum(n for _, n in picked))
    samples.sort()
    return {"clusters": len(totals), "draws": draws, "seed": seed,
            "lcb": samples[max(0, math.floor((draws - 1) * alpha / comparisons))]}


def sample_size(*, q=.16, delta_true=0., epsilon=.02, alpha=.05,
                comparisons=18, power=.8, simultaneous_power=False):
    """Normal planning n; union-bound type-II error for all-bin power if asked."""
    if not 0 < q <= 1 or abs(delta_true) > q or delta_true + epsilon <= 0:
        raise ValueError("positive separation and feasible discordance required")
    if not 0 < alpha < 1 or not 0 < power < 1 or comparisons < 1:
        raise ValueError("invalid alpha/power/comparisons")
    bin_power = 1 - (1 - power) / comparisons if simultaneous_power else power
    z = NormalDist().inv_cdf
    return math.ceil((z(1 - alpha / comparisons) + z(bin_power)) ** 2 *
                     (q - delta_true ** 2) / (delta_true + epsilon) ** 2)


def cluster_plan(effective_n, probes_per_seed=80, rho=.01):
    if effective_n < 1 or probes_per_seed < 1 or not 0 <= rho <= 1:
        raise ValueError("invalid cluster planning inputs")
    design_effect = 1 + (probes_per_seed - 1) * rho
    raw_n = math.ceil(effective_n * design_effect)
    return {"design_effect": design_effect, "raw_n": raw_n,
            "seeds": math.ceil(raw_n / probes_per_seed)}


def evaluate(rows, manifest, *, approved=False, epsilon=.02, alpha=.05,
             ratio_tolerance=.05, min_effective_n=10240, min_seeds=128,
             rho=.01, draws=20000):
    """Proposal only: PASS needs complete frozen pairs, all 18 bins and approval.

    FAIL is an observed hard regression or an adequately sampled rejected bin.
    Missing domain/power, bad joins, deterministic measurements and unapproved
    policy are INSUFFICIENT. No absent/refused query may be silently dropped.
    Caller must preregister rho/minimums from a blinded pilot before model runs.
    """
    rows, manifest = list(rows), list(manifest)
    reasons = []
    if approved is not True:
        reasons.append("proposal_not_approved")
    if epsilon < 0 or not 0 < alpha < 1 or not 0 <= rho <= 1:
        raise ValueError("invalid gate policy")
    if min_effective_n < 2 or min_seeds < 2 or not 0 <= ratio_tolerance < 1:
        raise ValueError("invalid gate minimums/tolerance")
    manifest_hash = digest([asdict(p) for p in manifest])
    probes = {(p.session_seed, p.probe_id): p for p in manifest if p.eligible}
    if not probes or len({(p.session_seed, p.probe_id) for p in manifest}) != len(manifest):
        reasons.append("empty_or_duplicate_manifest")
    grouped = defaultdict(list)
    seen = set()
    protocol = set()
    run_metadata = defaultdict(set)
    seed_trajectories = defaultdict(set)
    for row in rows:
        key = (row.probe.session_seed, row.probe.probe_id)
        pair_key = (*key, row.cycle, row.ratio_target)
        if pair_key in seen:
            reasons.append("duplicate_pair")
        seen.add(pair_key)
        if probes.get(key) != row.probe or row.manifest_digest != manifest_hash:
            reasons.append("manifest_mismatch")
        if row.measurement != "model_exact_recitation":
            reasons.append("not_model_recall")
        if row.paraphrase != "real" or not row.pruning:
            reasons.append("unqualified_controls")
        protocol.add((row.model, row.scorer_digest, row.pruning, row.paraphrase))
        run_metadata[(row.probe.session_seed, row.cycle, row.ratio_target)].add((
            row.ratio_actual, row.ratio_actual0, row.token_budget, row.arm_order,
            row.retained_K_tokens, row.retained_K0_tokens, row.summary_tokens, row.summary0_tokens))
        seed_trajectories[row.probe.session_seed].add(row.trajectory_digest)
        if max(abs(row.ratio_actual / row.ratio_target - 1),
               abs(row.ratio_actual0 / row.ratio_target - 1),
               abs(row.ratio_actual / row.ratio_actual0 - 1)) > ratio_tolerance:
            reasons.append("ratio_mismatch")
        if max(row.retained_K_tokens + row.summary_tokens,
               row.retained_K0_tokens + row.summary0_tokens) > row.token_budget:
            reasons.append("budget_exceeded")
        cell = (row.cycle // 100 * 100, row.ratio_target)
        if cell not in BINS:
            reasons.append("outside_registered_domain")
        grouped[cell].append(row)
    if len(protocol) != 1:
        reasons.append("protocol_drift_or_empty")
    if any(len(values) != 1 for values in run_metadata.values()):
        reasons.append("checkpoint_metadata_drift")
    if any(len(values) != 1 for values in seed_trajectories.values()):
        reasons.append("trajectory_drift")
    if {r.arm_order for r in rows} != {"K0,K10", "K10,K0"}:
        reasons.append("arm_order_not_counterbalanced")
    if any(row.prohibited_regressions for row in rows):
        return {"status": "FAIL", "proposal_only": True, "reasons": ["prohibited_regression"], "cells": []}
    cells = []
    rejected = False
    for cell in BINS:
        sample = grouped[cell]
        counts = defaultdict(int)
        checkpoints = {r.cycle for r in sample}
        for cycle in checkpoints:
            if {(r.probe.session_seed, r.probe.probe_id) for r in sample if r.cycle == cycle} != set(probes):
                reasons.append("missing_manifest_pairs")
        for row in sample:
            counts[row.probe.session_seed] += 1
        # Conservative max-cluster size design effect for unequal clusters.
        effective = len(sample) / (1 + (max(counts.values(), default=1) - 1) * rho)
        if not sample or effective < min_effective_n or len(counts) < min_seeds:
            reasons.append("missing_or_underpowered_bin")
            cells.append({"bin": cell, "n": len(sample), "effective_n": effective, "lcb": None})
            continue
        pairs = [(r.y10, r.y0) for r in sample]
        normal = simultaneous_lcb(pairs, alpha, len(BINS))
        boot = seed_cluster_bootstrap(sample, alpha=alpha, comparisons=len(BINS), draws=draws)
        # Repeated perfect pairs yield a degenerate percentile interval. Do not
        # pretend this certifies the population from a constant observed sample.
        if len({r.y10 - r.y0 for r in sample}) == 1:
            reasons.append("degenerate_interval_requires_finite_sample_method")
        rejected |= boot["lcb"] < -epsilon
        cells.append({"bin": cell, **normal, "effective_n": effective,
                      "bootstrap": boot, "gate_lcb": boot["lcb"]})
    status = "INSUFFICIENT" if reasons else ("FAIL" if rejected else "PASS")
    return {"status": status, "proposal_only": True, "epsilon": epsilon,
            "reasons": sorted(set(reasons)), "cells": cells}
