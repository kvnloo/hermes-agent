#!/usr/bin/env python3
"""K-gate statistics for RFC #143379's 300+ cycle hard gate (stdlib only, seeded).

Inputs are the RFC's own published numbers:
  300-cycle K=10 6.1% vs K=0 9.6% (-3.5pp); rerun spread -9.2 .. +10.2pp;
  150-cycle gains +1.1 .. +2.3pp. The per-arm n is NOT published.

Questions:
  Q1  Which per-arm n are consistent with 6.1% and 9.6% (1-dp rounding)?
  Q2  Under a true delta of 0, how likely is |delta| >= 3.5pp, and is a
      19.4pp rerun range plausible from binomial noise alone?
  Q3  False-fail rate of the gate as written ("any point < 0 fails") when the
      window is truly neutral or truly +1.1pp better, by n and point count.
  Q4  n per bin a paired one-sided non-inferiority gate needs.
"""
import json, math, random, sys

SEED = 143379
rnd = random.Random(SEED)
out = {"seed": SEED}

# Q1 ---------------------------------------------------------------------------
cons = [n for n in range(10, 2001)
        if any(round(100 * k / n, 1) == 6.1 for k in range(n + 1))
        and any(round(100 * k / n, 1) == 9.6 for k in range(n + 1))]
out["Q1_consistent_n_first20"] = cons[:20]
out["Q1_smallest_n"] = cons[0]

# Q2 ---------------------------------------------------------------------------
def sim_delta(p0, p1, n, paired_rho=0.0):
    """One run: unpaired binomial (rho=0) or paired with latent correlation."""
    if paired_rho == 0.0:
        a = sum(rnd.random() < p1 for _ in range(n))
        b = sum(rnd.random() < p0 for _ in range(n))
        return (a - b) / n
    # paired: shared uniform with prob rho, else independent
    d = 0
    for _ in range(n):
        if rnd.random() < paired_rho:
            u = rnd.random(); x, y = u < p1, u < p0
        else:
            x, y = rnd.random() < p1, rnd.random() < p0
        d += x - y
    return d / n

p = 0.0785  # pooled midpoint of 6.1% and 9.6%
q2 = []
for n in [cons[0], 80, 114, 200, 500]:
    sd = math.sqrt(2 * p * (1 - p) / n)
    trials = 20000
    ds = [sim_delta(p, p, n) for _ in range(trials)]
    p_abs = sum(abs(d) >= 0.035 - 1e-12 for d in ds) / trials
    # range across R=5 reruns
    rng5 = []
    for _ in range(4000):
        r = [sim_delta(p, p, n) for _ in range(5)]
        rng5.append(max(r) - min(r))
    rng5.sort()
    q2.append({"n_per_arm": n, "null_sd_pp": round(100 * sd, 2),
               "P_abs_delta_ge_3.5pp": round(p_abs, 3),
               "median_range_5_reruns_pp": round(100 * rng5[len(rng5) // 2], 1),
               "P_range5_ge_19.4pp": round(sum(x >= 0.194 for x in rng5) / len(rng5), 3)})
out["Q2_null_noise"] = q2

# Q3 ---------------------------------------------------------------------------
# Gate as written: every measured point (cycle bin x ratio) in the 300+ band at
# 4x-8x must have delta >= 0. Points = bins * ratios.
q3 = []
for n in [80, 300, 1000]:
    for points in [1, 5, 18]:
        for true_pp in [0.0, 1.1]:
            trials = 2000 if n <= 300 else 600
            fails = 0
            for _ in range(trials):
                if any(sim_delta(p, p + true_pp / 100, n, paired_rho=0.5) < 0 for _ in range(points)):
                    fails += 1
            q3.append({"n_per_point": n, "points": points, "true_delta_pp": true_pp,
                       "paired_rho": 0.5, "P_gate_FAIL": round(fails / trials, 3)})
out["Q3_gate_as_written"] = q3

# Q4 ---------------------------------------------------------------------------
# Paired NI: pass if one-sided 95% LCB of mean delta > -eps in every bin.
# Var of a paired difference d in {-1,0,1}: approx p10+p01 discordance.
z_a, z_b = 1.645, 1.2816  # alpha .05 one-sided, power .90 per bin
q4 = []
for eps in [0.02, 0.03, 0.05]:
    for disc in [0.06, 0.10, 0.15]:  # discordant-pair rate
        n = math.ceil(((z_a + z_b) ** 2) * disc / eps ** 2)
        q4.append({"eps_pp": eps * 100, "discordant_rate": disc, "n_pairs_per_bin_90pct_power": n,
                   "bins18_total_pairs": n * 18})
out["Q4_paired_noninferiority"] = q4

json.dump(out, sys.stdout, indent=1)
print()
