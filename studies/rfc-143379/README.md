# Hermes RFC #143379 — reproducible homework (downstream-only)

Tracking: [kvnloo/hermes-agent#653](https://github.com/kvnloo/hermes-agent/issues/653). Upstream discussion: [NousResearch/hermes-agent#143379](https://github.com/NousResearch/hermes-agent/issues/143379). **Nothing in this PR posts or changes upstream.**

## Evidence tiers: read this before reporting results

- **Reproduced locally / isolated:** The original `memory/` and `consent/` Python experiments were executed in isolation, using synthetic data and selected PR-style control flow. This is **not a Hermes full-checkout test**, not a real compressor, not a live model, and not a production incident. Passing tests sometimes assert that the vulnerable behavior occurs.
- **Exact-head checkout probes:** `checkout/run_exact_heads.sh` runs real Hermes imports at the six pinned upstream PR commits, via temporary detached worktrees. It is **provided but has not been executed by this ChatGPT environment**. It may produce *failing* diagnostics by design. The operator should publish the actual head, exit status, failing assertions and logs before turning any suspected issue into an upstream factual claim.
- **Full model/evaluation:** Not run. Evaluate actual compaction, source recovery and consent under the frozen z0evals #56 cohort separately; do not treat idealized archive reachability as recall accuracy.

## Files

| Path | What it contains |
|---|---|
| `memory/lab.py` | PR-style disk/read-store model; scheduled read/add and anchor/write races; synthetic scoped correction/source digest; bounded UTF-8 pager |
| `memory/test_lab.py` | 17 synthetic mechanism tests with deterministic interleavings |
| `memory/bench.py` | **Complete** seeded 150/300-cycle exact-ID availability generator; ratios and probe policy are source code |
| `memory/results.json` + `memory/raw_coverage.csv` | Full aggregate + **250 per-seed rows** (not a graph screenshot) |
| `memory/run_against_checkout.sh` | Original conservative runner for existing checkout test files |
| `consent/runtime.py`, `consent/snapshots/*.py` | Exact case construction and source-adapted main, PR #116834, PR #116846, hypothetical combination gate shapes |
| `consent/test_consent.py` | 116 assertions across negative and positive controls |
| `consent/results.csv`, `summary.json`, `pytest_results.txt`, `run_results.txt` | Original synthetic output and test receipts |
| `checkout/consent_scenarios.json` | 12 **explicit** synthetic prohibited-write candidates and trusted-source opt-out annotations |
| `checkout/test_real_checkout.py` | New probes importing the **actual** checkout modules (not executed here) |
| `checkout/run_exact_heads.sh` | Pinned-SHA detached worktree runner and per-head logs; does not push or merge |
| `RFC1-HOMEWORK.md` | Analysis/comment source text, evidence tiers, open questions, suggested upstream sequencing |

## Pinned PR heads

| PR | Topic | Author / contributor | Exact SHA |
|---|---|---|---|
| [#141876](https://github.com/NousResearch/hermes-agent/pull/141876) | 16-line `read` restoration | c0wb0yp0tat0 | `af16e3ab16eed2492552c325ad1777533a8b7004` |
| [#116673](https://github.com/NousResearch/hermes-agent/pull/116673) | Chain-doc anchor and bounded routing | Finn763 | `2c1941aac46efac3b35605d99a8628e75a91c670` |
| [#139606](https://github.com/NousResearch/hermes-agent/pull/139606) | Seven-stage write gate | c0wb0yp0tat0, based on #135039 by uni5592427 and design feedback from RemanenetSpy and jimy-r | `5b31ccb7d56ad614da63588ef876584b9f95dd3f` |
| [#140008](https://github.com/NousResearch/hermes-agent/pull/140008) | Session preservation + dream cycle | c0wb0yp0tat0; references dreaming concept #25309 by Minamaged18 | `e543544aca215bf7ea838444b6df58bdbbd3e38c` |
| [#116834](https://github.com/NousResearch/hermes-agent/pull/116834) | Background USER.md staging | chelsealong | `f678f4c7e5d994f03d8759fe0e950d3407ccca7e` |
| [#116846](https://github.com/NousResearch/hermes-agent/pull/116846) | No-save self-report staging | liuhao1024 | `96dc75192a82b6c5645a89c2eb894fba97ad2bbd` |

Original main snapshot used for consent comparison: `fab9b01c915a3118cc8daa6cc1b18c15b3f982d0` on 2026-10-23. Later `main` versions may differ.

## Reproduce isolated results (Python 3.10+ and pytest)

From this folder:

```bash
(cd memory && python -m pytest -q test_lab.py && python bench.py)
(cd consent && python -m pytest -q test_consent.py && python runtime.py)
```

Expected isolated tests: **17/17** memory mechanisms and **116/116** consent assertions pass. The consent tests are designed to assert observed *failures of the no-save invariant* in the reviewed gate snippets, not that privacy is fixed. Bench output regenerates the committed aggregate JSON and per-seed CSV deterministically. The consent CSV omits secrets and uses the invented `SYNTHETIC-CONSENT-CODE-PX7412` marker.

## Exact-head reproduction in OMP's full checkout

From the fork's study branch, in a trusted shell with a full Hermes checkout present:

```bash
bash studies/rfc-143379/checkout/run_exact_heads.sh /absolute/path/to/hermes-checkout /tmp/rfc-143379-head-results all
cat /tmp/rfc-143379-head-results/manifest.tsv
```

Or scope to a single PR:

```bash
bash studies/rfc-143379/checkout/run_exact_heads.sh /absolute/path/to/hermes-checkout /tmp/rfc-143379-read 141876
```

The script checks exact commit SHAs, fetches `refs/pull/<number>/head` if the object is unavailable, creates temporary **detached** worktrees, copies the probes as untracked test fixtures, calls **that worktree's** canonical `scripts/run_tests.sh` with retries disabled, then removes the worktrees. No default-branch writes, no commits, no network posts. It records every exit code and full log, including failures and skips. Set `HERMES_PYTHON=/path/to/checkout-test-env/bin/python` when using an already-prepared interpreter (the runner honors that environment variable). It cannot silently substitute another head for a missing SHA.

`#141876`: read dispatch and read/add interleaving. `#116673`: those plus reference/unlink interleaving and exploratory response-size contract. `#139606`: advertised read action vs store availability. `#140008`: the PR's actual `tests/tools/test_dream_cycle.py` suite. `#116834` and `#116846`: all 12 consent cases, checking **both memory and pending JSON**. The runner does not claim tests across independently unmerged PRs constitute proof of their combined behavior.

## Current-head delta and Avrea verification (2026-10-25)

Companion **actual-head, native MBP/fleet evidence** already exists on
[`study/rfc-143379-exact-heads`](https://github.com/kvnloo/hermes-agent/tree/study/rfc-143379-exact-heads/studies/rfc-143379/exact-heads).
That branch records 7/12 native read assertions on #141876 versus 12/12
with an instrumented control, chain-document response measurements up to
1 MiB, 150/300/600-cycle deterministic compressor-boundary checks, and
production-module consent experiments. It **did not run the full upstream
suite or a real compressor/model**, and the historical 300-cycle RFC
K-recency result remains unreplicated. Keep that source-backed evidence
distinct from this PR's prospective Avrea CI receipts; don't duplicate
its raw data without a reason.

The historical matrix stays pinned to the six SHAs in the table above.
Finn763's #116673 has moved to `ffc651bd11982eb5b4e1412f1b4b4c34d91cd42d`.
Test that exact new head separately without erasing the baseline:

```bash
RFC_116673_SHA=ffc651bd11982eb5b4e1412f1b4b4c34d91cd42d \
  bash studies/rfc-143379/checkout/run_exact_heads.sh \
  /absolute/path/to/hermes-checkout /tmp/rfc-143379-latest-chain 116673
```

Additional **real-module** exploratory probes in `checkout/test_real_checkout.py`
check read freshness without prompt-cache mutation, UTF-8 BOM/Unicode,
undecodable disk preservation, and orphan-document read/write policy
(7 parametrized cases across four test functions). These tests may be RED
on experimental heads; a nonzero result is a diagnostic, not a production
incident. `read`/chain-doc capability gates are skips on heads that do
not implement those features; skip count must be reported.

`.github/workflows/rfc-143379-avrea.yml` is a fork-only,
branch-restricted GitHub Actions execution path using Avrea runners.
It runs the unfiltered Linux Python suite in two exact-SHA shards with
`scripts/run_tests.sh`, then runs the independent historical and
latest-chain PR-head probes. A run/checkout with no matching source SHA,
no runner, or missing artifacts is **NOT RUN**; green isolated tests
are not a substitute for the full CI suite or 300+ cycle real-model
compression qualification. Logs/manifests are retained as short-lived
GitHub Actions artifacts and should be linked to their run ID before
updating any upstream evidence claims.

## The 7.30% / 3.65% answer (critical distinction)

**These are observed counts of uniformly sampled probe indices in a deterministic toy exact-ID availability simulation, not observed model recall and not measured compressor fidelity.** `bench.py` generates `n` independent synthetic 80-bit `sha-...` strings from `random.Random(10000 * n + 100 * ratio + seed)`, then draws **80 indices with replacement** via `rng.randrange(n)` from each seeded stream. `seed` is exactly each integer in `[0, 24]`; each `(n, ratio)` has **25 seeds × 80 probes = 2,000 draws**. A synthetic `summary_only` retains no identifier; a fixed window retains the last `min(10, floor(n/ratio))` exact identifiers. The toy "4× compression" ratio affects only the **exact-entry budget cap**, `floor(n / 4)` (37 or 75 here). It does **not** run a compressor, tokenize texts, summarize with a model, or compress bytes.

At ratio 4, the 10-item window has **analytic capacity** `10/150 = 6.6667%` or `10/300 = 3.3333%` of uniformly sampled past positions. The seeded Monte Carlo produced **146/2000 = 7.30%** and **73/2000 = 3.65%**, respectively. The difference from the analytic probabilities is ordinary finite-sample variation. The toy archive control is 100% **by definition of an always-available oracle**, not measured recall. The RFC's own 150/300-cycle figures are a different experiment and are not reproduced by this benchmark.

For actual compression quality, use real source-backed retrieval and verified model outputs in z0evals #56, with the compressor in the loop; keep read, scope, provenance, token/latency and memory-consent receipts separate.

## Privacy, sources, and status

The consent lab uses only fabricated, non-identifying strings and ephemeral temporary directories. No real transcripts, personal attributes, tokens or secrets were ingested. “No-save” applies to write eligibility as well as to whether staged payloads retain content. This is a cooperative-mode retention policy study, **not a claim of crossing Hermes's OS isolation boundary**. No upstream comment, PR, issue, branch, or change was made for this homework.

Peer-reviewed hypothesis to test, not a verified implementation: Guanghui Min and Chen Chen, *[Prune the Summary, Not the History: Source-Judged Compaction for Long-Horizon Agents](https://arxiv.org/abs/2610.20927)*, arXiv:2610.20927 (October 2026). Its 83% figure refers to error attribution in a selected set of failed runs, **not** an 83% provenance-survival target; it reports 2.1–8.9 percentage-point cross-run reliability improvement with Jev in its evaluation.
