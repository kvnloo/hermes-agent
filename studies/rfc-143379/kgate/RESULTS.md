# Executed boundary result

Downstream Avrea [run 40293977816](https://github.com/kvnloo/fleet-runner/actions/runs/40293977816)
executed study `9e00c1f728e02a82a04df80c8832774365da4119` against upstream main
`e82bf01eec9bb58848209b07f0bc7d8895a39f9b`, with the canonical CI setup and
no network/LLM in the harness. At that tested study revision: **22 passed,
1 skipped** in study tests; **12 passed** in the upstream ghost-skill suite.
Later test-only/validation additions are re-run on the final PR SHA; see the
PR's exact-head hosted receipt rather than attributing this older count to it.

## Demote gap: PARTIAL overall, CONFIRMED mechanism

Both real pruning paths preserve the skill reload marker and omit a memory
reload marker. Tail demotion emits a session-search recovery pointer; proactive
pruning emits `[memory] read on memory`. The real memory read dispatch is
unsupported, and the chain-doc test is explicitly skipped. The memory result
used to test demotion is an injected historical result, not a fabricated live
API success. Source lines are in `../demote-gap/README.md`.

## Deterministic paired measurement (not model recall)

72 unique paired rows, 7,200 completed compressor generations, and 7,200 native
tool-result prunes. Both arms use the same frozen IDs and full source-trajectory
hashes. Each checkpoint/ratio cell has 12 probes across two counterbalanced
session seeds. Actual K10/K0 protected tails were 440/72 tokens.

| Requested ratio | Actual K10 | Actual K0 | 300-cycle hits K10/K0 | 600-cycle hits K10/K0 |
|---|---:|---:|---:|---:|
| 4× | 4.00140 | 4.00490 | 4/2 of 12 | 0/0 of 12 |
| 6× | 6.00661 | 6.01637 | 4/2 of 12 | 0/0 of 12 |
| 8× | 8.02731 | 8.01581 | 4/2 of 12 | 0/0 of 12 |

All checkpoint pairs meet the declared ratio tolerance and common token budget.
The unapproved statistical gate returns **INSUFFICIENT**: deterministic outcomes
are not model recall, real paraphrase is absent, most bins are missing, and the
sample is not powered. These availability counts are not an RFC gate pass.

The earlier pilot on `25a49da80efe40d7d4e0b9c42cb249b838944337` exposed missing
native scaffold accounting and an infeasible 8× request with a small workload.
It was not selected into the final cohort. Fixed non-target padding and a
label-independent scaffold budget controller corrected the measurement setup;
probe IDs/target source bytes were unchanged. All per-cycle transients remain
in the hosted trace. No real-model result was used for this calibration.

`receipts/avrea-r2.json` binds the source/run, JUnit testcase counts, per-cell
results and hashes of the complete hosted artifacts. `receipts/paired-r2.jsonl`
contains every paired row. The full trace stays in the linked run's artifacts.

No upstream writes, production compressor changes, full-suite claim, or change
to the RFC's original acceptance criterion.
