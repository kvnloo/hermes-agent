# Paired K-gate proposal and deterministic boundary harness

**Not an RFC acceptance change.** The RFC's original hard gate remains:
for all tested cycles ≥300 and ratios 4×–8×, min(K10 − K0) ≥0 percentage points.
The finite 18-bin, ε=2pp non-inferiority rule below is an **unapproved proposal**.
No deterministic harness result certifies model recall or that original rule.

## Artifacts

- `stats.py`: immutable probe/paired-row schemas, flat JSON round-trip,
  discordances, paired standard error, Bonferroni normal lower bound,
  session-seed cluster percentile bootstrap, power/design-effect calculator,
  fail-closed PASS/FAIL/INSUFFICIENT proposal evaluator.
- `test_stats.py`: light stdlib-only unit tests; no Hermes imports.
- `manifest.py`, `frozen-manifest.json`: public synthetic source generator and
  frozen source/target manifest. Same source IDs at 300 and 600, in both arms
  and all ratio requests. Changing the manifest or source bytes is rejected.
- `harness.py`, `test_harness.py`: actual pinned Hermes `ContextCompressor`
  with **only `_call_summary_llm` replaced** by a deterministic literal-free
  summary. Native planning, pruning, iterative previous-summary handling,
  assembly and anti-growth checks still execute. Network is blocked.
- `run-hosted.sh`: exact-pin hosted orchestration after CI-parity setup.

## Statistical contract

A pair has one immutable `(session_seed, probe_id, source_digest, source_scope,
target_literal, eligibility)` identity and matched cycle/trajectory. Outcomes
are binary integers `y10,y0`; unresolved/refused sources remain scored cases.
Rows additionally record requested and **both actual** ratios, manifest/scorer/
trajectory hashes, arm order, model, pruning/paraphrase control, retained K and
summary tokens for both arms, common budget, and prohibited regressions.

For n pairs: b counts `(1,0)`, c counts `(0,1)`, q=(b+c)/n,
δ=(b−c)/n, SE=sqrt((q−δ²)/n). The illustrative normal lower bound is
δ−Φ⁻¹(1−.05/18)SE, with z≈2.772921. The gate uses the **seed-cluster bootstrap**
lower percentile instead of treating within-session probes as independent.
This is an approximate interval, not an exact finite-sample guarantee.
The bootstrap retains all rows in a drawn seed, including unequal cluster
sizes, and requires at least 20 expected replicates in its adjusted lower tail.
Degenerate observed differences are INSUFFICIENT, not false certainty.

Proposed domain: 300–399 through 800–899, crossed with 4×/6×/8× = 18 bins.
PASS requires approval, complete eligible manifests in every observed
checkpoint, all bins, realized ratios within preregistered tolerance, common
controls/budgets, enough effective pairs and independent seeds, all LCB≥−.02,
and zero prohibited regressions. Hard regressions FAIL. Missing controls,
coverage, power, approval or model measurements are INSUFFICIENT. A populated,
qualified rejected cell produces FAIL. This does not certify untested points.
Minima/ICC/tolerance must be preregistered from a blinded pilot; defaults are
planning assumptions, not estimates from this synthetic run.

Power reproduces
[RFC143379-KGATE-POWER-01](https://github.com/kvnloo/hermes-agent/pull/654#issuecomment-6410234331):

| Design, q=.16, true δ=0, ε=.02 | Effective paired probes/bin |
|---|---:|
| One bin, α=.05, 80% power | 2,474 |
| 18-bin Bonferroni, 80% per-bin power | 5,226 |
| 18-bin Bonferroni + union-bound ≥80% all-bin power | 10,240 |

`ceil((z_(1−alpha/m)+z_power)^2 * (q−δ²)/(δ+ε)^2)`;
all-bin per-cell power is `1−.20/18`. At 80 probes/seed and ICC=.01, design
effect=1.79, raw pairs=18,330, seeds=230. At ICC=0, 128 seeds.
These are normal planning approximations, not observed efficacy. A zero margin
at true neutrality has no finite n under this design; the calculator rejects it.

## What the harness actually measures

**Deterministic boundary measurement, not model recall.** Exact substring
availability in visible message content is the score, not an answer from a
model. It never reads hidden session archives as an oracle. Each cycle feeds
40 synthetic conversational rounds plus one long tool result and executes one
real `compress()` generation. Every generation must actually call the replaced
summarizer and increment `compression_count`; no-ops/fallbacks fail the run.
The same trajectory runs uninterrupted through checkpoint 300 then 600.
Thus “600” means 600 actual compaction generations, not 600 messages.

K10 requests ten protected user rounds via the native `min_tail_user_messages`
guard; K0 disables that optional window. **Native K0 still retains mandatory
active-turn anchors.** This baseline is explicitly not a physically empty tail,
and K is not ten tokens. Both use a one-token discretionary tail budget; realized
native tail size is recorded. Legacy-tail mode isolates recency from lean mode's
extra deterministic verbatim-user section. Native tool pruning remains on.
A common fixed output-budget function is registered from the synthetic source
workload and requested ratio; the larger K tail consumes summary space. Fixed
non-target padding in the oldest 30 rounds makes room for an 8× request. A
deterministic controller measures native prefix/scaffold overhead after each
boundary and reserves it at the next one, without looking at target outcomes.
Summary-token accounting is the post-boundary residual after native head/tail
tokens, so merged summary carriers do not double-count tail text. All transient
ratios are retained in the trace. Native floors can still prevent a requested
budget/ratio being attained; all mismatches stay
in the output and the proposal gate refuses certification. No post-hoc ratio
filtering or guaranteed K0-zero assumption like the earlier toy benchmark.

Two seeds counterbalance arm order with fresh compressor instances. Six frozen
probes per seed × two checkpoints × three ratios = 72 paired rows. This is a
boundary smoke cohort, not powered model evidence. Cycle 600 intentionally
uses the *same* older targets, not newly resampled questions. Real paraphrase,
model inference, retrieval, protected-scope behavior and population generality
are NOT measured. The proposal gate must return INSUFFICIENT.

## Run

Local, stdlib only:

```sh
python3 -m unittest discover -s studies/rfc-143379/kgate -p test_stats.py -v
```

Hosted: checkout the published **study SHA**, prepare the canonical Hermes CI
environment using the supplied CI setup procedure, then invoke `run-hosted.sh`.
It creates an isolated worktree at upstream main
`e82bf01eec9bb58848209b07f0bc7d8895a39f9b` and uses that source for all Hermes
imports. No runtime-installation or live-profile mutation is needed. Artifacts:
JUnit XML, demote verdict/stubs, 72 paired rows, the complete per-cycle trace,
manifest copy/hash, harness report and study/source SHAs under `rfc-out/`.

No full Hermes suite, real-model calls, field logs or combined memory substrate
are included. Source-owner credit remains with the upstream authors and
KGATE-POWER-01's author; this downstream leaf implements the proposed study.
