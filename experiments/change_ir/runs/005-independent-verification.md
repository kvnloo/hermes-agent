# Run 005 — independent execution and measurement closeout

- Date: 2026-10-07
- Author: Codex, at the workspace owner's request
- Experiment snapshot: `kvnloo/hermes-agent@c09ff344d3a5b4b3bb7c57a9acaf0f5dbced5392`
- Materialization target: `NousResearch/hermes-agent@59a3866ea5a07290afd9a1d137d52d679b77f3ab`
- Tested realization: `kvnloo/hermes-agent@ae39a24e59e34b49695312585ad83ae9ccd97c6c`

## Verdict

The experiment's previously unresolved execution receipt is now **verified green**.
The exact realization referenced by `relations.json` ran its targeted suite successfully.
No additional production-code change was necessary to close that execution gap.

This receipt updates the current interpretation of the historical "queued" caveat in
`FINAL.md`, `README.md`, and Run 003. Those historical documents remain unchanged.

The changed-line reduction is independently reproduced. The historical review-context
percentage is arithmetically correct, but its exact character totals were not reproduced;
the explicit fresh measurement below yields **80.50%**, not 81.4%.

## Execution evidence

- [Run 37547255551](https://github.com/kvnloo/hermes-agent/actions/runs/37547255551):
  `status=completed`, `conclusion=success`.
- [Targeted job 112554100190](https://github.com/kvnloo/hermes-agent/actions/runs/37547255551/job/112554100190):
  started `2026-10-07T00:10:37Z`, completed `2026-10-07T00:11:18Z`.
- Run and job both identify head `ae39a24e59e34b49695312585ad83ae9ccd97c6c`.
- Command recorded by the workflow:

  ```text
  python -m pytest tests/gateway/test_telegram_group_gating.py -q
  ```

- Verbatim test summary from the successful job:

  ```text
  30 passed in 4.69s
  ```

The workflow used Linux and CPython 3.14.7. This is a verified remote execution,
not a claim that this review reran pytest locally or exercised live Telegram delivery.

## Behavior and scope review

The three added tests cover sibling-addressed human messages being observed without
dispatch, ordinary chatter remaining unobserved when only sibling mode is enabled,
and the previous drop behavior when sibling observation is disabled.

Source inspection at the tested head also confirms that the new branch checks the
opt-in flag, rejects bot-authored sibling messages, and requires an explicit observation
chat allowlist after the topic gate. Text and media handlers retain their user-authorization
checks; rejected dispatch routes may append an attributed transcript row with `observed: True`.
The observation path returns without calling the normal message-dispatch path.

Reviewed source identities at the tested head:

| Path | Blob identity |
|---|---|
| `gateway/config_loader.py` | `code@f7fcbf76` |
| `plugins/platforms/telegram/adapter.py` | `code@0c24106e` |
| `tests/gateway/test_telegram_group_gating.py` | `code@29780bd2` |

These are source-review findings, not additional executed test cases. Outbound final-response
mirroring, cross-profile writes, and live cross-host behavior remain outside this realization.
The 30-test result does not establish their correctness or authorize production deployment.

## E3 historical sample reconciliation

The complete `fixtures/78207.json` at the experiment snapshot contains 17 unique PR IDs.
Recounting all rows reproduces the published grouping:

| Historical group | Count | PRs |
|---|---:|---|
| Implemented / superseded | 8 | 78036, 77724, 77748, 77756, 77751, 77759, 77752, 77719 |
| Mixed | 2 | 78033, 77708 |
| Needs a fresh decision | 7 | 77911, 77907, 77909, 77706, 77707, 77710, 77711 |

For this aggregation, `moved` is a location qualifier; removing it leaves either only
`already_on_main`, only `needs_decision`, or a mixed state set. This reproduces the
receipt's grouping without treating `moved` alone as evidence of implementation.

This is a consistency check of the **2026-10-06 classification at target 59a3866e**.
It does not independently reclassify all 17 PRs against a newer main. The original
"0/17 safely replayable" conclusion remains attributed to Run 002's semantic review.

## Reproducible size measurement

Source PR head remains `fb7455387637634f275274516fde78ef722e0725`.
GitHub reports 818 additions and 6 deletions across 4 files. Comparing the materialization
target with `f582ac19` reproduces 79 additions and 3 deletions across 3 files.
The later CI-only commit is deliberately excluded from both code-size and packet measures.

| Measure | Original PR | Materialized operation |
|---|---:|---:|
| Changed source/test lines | 824 | 82 |
| Fresh GitHub diff characters | 47,609 | 7,519 |
| PR body characters | 9,131 | — |
| Issue-comment body characters | 10,818 | — |
| Review and inline-review body characters | 0 | — |
| Change IR fixture characters | — | 5,657 |
| Total measured packet characters | **67,558** | **13,176** |

Method: decode UTF-8 and count Unicode code points with Python `len(text)`. Count each
raw diff and each JSON body string exactly once, with no separators, API envelopes,
HTML rendering, log output, or CI-only workflow content added. All six issue comments
were returned in one page; the review and inline-review endpoints returned empty lists.

Recomputed results:

- Changed-line reduction: `100 * (1 - 82 / 824)` = **90.05%**.
- Packet-character reduction: `100 * (1 - 13176 / 67558)` = **80.50%**.
- Original/new packet ratio: `67558 / 13176` = **5.13x**.

Run 003's historical inputs, 67,555 and 12,540, do produce 81.44% and 5.39x.
Its 6,883-character materialization diff was not reproduced by either local Git's diff
or GitHub's comparison endpoint. The published receipt does not pin enough serialization
detail to explain the difference conclusively. Preserve that historical measurement;
use the explicitly defined fresh measurement above for this receipt.

This compares the whole old PR with **one selected surviving operation**. It is not an
equal-feature-scope comparison, a measured reduction in human review time, or evidence
of better acceptance/merge throughput. Human decision agreement was not benchmarked.

### Source commands

```bash
gh api repos/kvnloo/hermes-agent/actions/runs/37547255551
gh api repos/kvnloo/hermes-agent/actions/runs/37547255551/jobs
gh run view 37547255551 --repo kvnloo/hermes-agent --log
gh api repos/NousResearch/hermes-agent/pulls/105624
gh pr diff 105624 --repo NousResearch/hermes-agent
gh api 'repos/NousResearch/hermes-agent/issues/105624/comments?per_page=100'
gh api 'repos/NousResearch/hermes-agent/pulls/105624/comments?per_page=100'
gh api 'repos/NousResearch/hermes-agent/pulls/105624/reviews?per_page=100'
gh api repos/kvnloo/hermes-agent/compare/59a3866ea5a07290afd9a1d137d52d679b77f3ab...f582ac19 \
  -H 'Accept: application/vnd.github.diff'
git diff --numstat 59a3866e f582ac19
```

Before a later remeasurement, verify the source PR head and capture all comment pages;
discussion is mutable even when the code head has not changed. This review retained the
raw responses under `.git/change-ir-verification/` in its isolated checkout.

SHA-256 of the captured raw evidence:

| Artifact | SHA-256 |
|---|---|
| `source.diff` | `a432d20320566e1ce3072f7371d9a352aeaff0bd9c9bb762f197a3204472e65f` |
| `compare-remat.diff` | `dd29af58b84cc0c87a5be3217fe442571279794a07d9d0275875210eb19873a0` |
| `ci.log` | `3366357909df6d5271cb63a959248817b4a154902117b28ff7ba3a80f0af6451` |

## Closeout boundary

The execution gap is closed for the pinned experimental realization. Original authorship,
fixtures, relations, and historical receipts remain intact. This review adds only this receipt;
it neither changes the production runtime nor publishes a GitHub comment, PR, or deployment.

[Proposal #455](https://github.com/kvnloo/hermes-agent/issues/455) remains a separate productization
proposal, including ingestion, classification, collision detection, and materialization work.
Its unchecked acceptance criteria must not be reported as implemented by this experiment.
