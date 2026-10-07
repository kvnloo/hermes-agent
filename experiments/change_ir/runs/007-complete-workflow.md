# Run 007 — Change IR v0 acceptance exercise

- Date: 2026-10-07
- Scope: [proposal #455](https://github.com/kvnloo/hermes-agent/issues/455)
- Previous target: `59a3866ea5a07290afd9a1d137d52d679b77f3ab`
- Current target: `c1b205df6805db947e32091dead615546621ee7a`
- Product: [optional Change IR skill](../../../optional-skills/software-development/change-ir/SKILL.md)
- Machine-readable evidence: [run receipt](007-complete-workflow.json)

## Result

All thirteen v0 criteria were exercised locally. The active agent does semantic
extraction, classification and code reconstruction using Hermes's existing tool
surface. The stdlib helper collects and binds evidence, compares curated contracts,
preserves history, materializes selected changes and gates PR preparation on tests.
This is an agent-assisted workflow, not a new autonomous model service.

The skill is packaged for the existing optional-skill loader. Its exported bundle
runs outside this checkout; production Hermes and Telegram were not modified.
Publication and maintainer acceptance are separate from this local acceptance run.

## Acceptance evidence

| # | Criterion | Observed result |
|---|---|---|
| 1 | Ingest real intent | Collected #44881/#78207 issues, #105624/#31157 PRs and all discussion/review pages; ingested three stable packets. Collected target AGENTS, contribution docs, code and tests. |
| 2 | Historical rerun | The same #31157 packet was reviewed at both pinned SHAs. New receipts preserve its July `still_needed` baseline. Original fixtures remain byte-identical. |
| 3 | Independent states | #31157 simultaneously records MCP `already_on_main + moved`, GitNexus `invalidated`, and GWS `needs_decision`. |
| 4 | Later implementation credit | Preserved the earlier proposal, independent diagnosis/fix and later behavior-test contributors through explicit provenance edges. |
| 5 | Anchors are not proof | Integration test leaves matching anchors `unknown` without a review. Reviewed code states require collected code evidence. |
| 6 | Same-operation collision | Source-reviewed #102199/#102320 contracts yield `same_operation`, confidence `high_under_supplied_contracts`, with both owners and source links. |
| 7 | Distinct boundaries | #105608 gateway marker writer and #128970 updater admission remain `related_distinct_boundary` relative to the preflight operation. |
| 8 | Policy overlap | #102258 repair/chown remains `overlapping_policy`; #102208 remediation UX is complementary. No merge order or winner is inferred. |
| 9 | Smaller packet | #105624 review plus selected diff: 13,171 versus 67,558 Unicode code points, an 80.50% reduction. |
| 10 | Current-main materialization | Reconstructed one selected operation on fresh branch `codex/change-ir-current-sibling-observe` at `c1b205df`; 79 additions, 3 deletions, 3 files. |
| 11 | Verification before promotion | Exact reviewed contract passed 30 tests with unchanged inputs, then `prepare-pr` produced the draft. Wrong commands, failed/stale receipts and changed inputs are rejected by integration checks. |
| 12 | No inferred authority | Maintainer decisions remain empty; receipts record `acceptance_inferred=false` and `promotion_authorized=false`. |
| 13 | GitHub review retained | Preparation emits an ordinary PR body with the selected plan, verification and credit. It neither publishes nor merges/closes contributions. |

## Fresh source review

MCP refresh now snapshots `self.session`, returns if it is absent, and performs the
RPC against that snapshot in `tools/mcp_tool_health.py`. The teardown/reconnect
tests exercise the resulting lifecycle. This independently validates the move and
behavior; the old `mcp_tool.py` anchor is not used as proof.

- Earlier proposal: [#31157](https://github.com/NousResearch/hermes-agent/pull/31157), @sege66.
- Production diagnosis: [#109824](https://github.com/NousResearch/hermes-agent/issues/109824), @patrykkopycinski.
- Independent fix: [1c82c22e](https://github.com/NousResearch/hermes-agent/commit/1c82c22eb69c502d6298703d0ebbc971f7eac6cd), @salch-cred, @Tranquil-Flow, @ildunari, @andrexibiza, @ly6751.
- Behavior tests: [37eb4d0b](https://github.com/NousResearch/hermes-agent/commit/37eb4d0b375feb3352ad87c95a1aa8481d605174), @austinpickett, @ly6751, @salch-cred.

The MCP suite was source-reviewed, not executed in this run. GWS remains a decision
and verification gap, not a claimed missing or implemented feature.

The six collision PRs were fetched again (25 source records). Their source
descriptions/reviews support the historical Run 004 contract distinctions. In
particular #102258's initial post-update repair was later described by its author
as preflight plus post-update repair; its review explicitly calls for composition
with #102199. The historical catalog itself was not silently rewritten.
The detector flags coordination under reviewed contracts, not formal equivalence
of the complete implementations. Conflicting supersession claims yield `unknown`.

## Executed checks

All tests used the repository's canonical `scripts/run_tests.sh` and an isolated
test interpreter, with retries disabled.

| Check | Result |
|---|---|
| Workflow, collection, collision and optional bundle integration | 4 passed |
| New skill authoring standards | 7 passed |
| Selected Telegram realization at `c1b205df` | 30 passed |
| Same regression tests on unmodified `c1b205df` production code | 29 passed, 1 expected failure |
| Repository `scripts/check --staged --base 66d9f847` | 11 checks passed |

The failing base test was
`test_sibling_addressed_user_can_be_observed_without_dispatch`: dispatch correctly
returned false, but passive observation returned false rather than true. The
materialized operation makes that test pass without regressing the other 29.

Tested source identities:

| Path | Blob identity |
|---|---|
| `gateway/config_loader.py` | `code@f7fcbf76` |
| `plugins/platforms/telegram/adapter.py` | `code@0c24106e` |
| `tests/gateway/test_telegram_group_gating.py` | `code@29780bd2` |

The selected patch reuses the previously reviewed implementation by @kvnloo and
the original intent by @majkonautic/@DavidMetcalfe, after confirming these exact
surfaces still fit the new main. The entire stale PR is not replayed.

## Measurement and limits

The denominator follows Run 005: original PR diff 47,609 + body 9,131 + comments
10,818 = 67,558. The new numerator is rendered review 5,662 + selected local diff
7,509 = 13,171. Counts use `len(utf8_decoded_text)` without API envelopes.
Raw evidence is retained separately and is not included in the compact packet.
This compares one selected operation with the stale PR review surface; it does
not measure model tokens, reviewer time or equivalent full-feature delivery.

The broad `is:pr "root-owned"` search included 100 of 405 candidates and explicitly
reports incomplete coverage. The six acceptance-fixture PRs were collected
separately. Git history is shallow; contribution-doc excerpts stop at 250 lines.
Neither limitation is used to prove absence or comprehensive duplicate detection.

Final-response mirroring, live Telegram traffic and the GWS credential proposal
remain outside this materialization. E3's 17-PR grouping remains the historical
Run 002/005 assessment; ingestion here does not silently reclassify it.

Raw source bundles, immutable receipts, full logs and generated PR drafts are
retained in the local clone's `.git/change-ir-complete/`, with a local archive at
`.git/change-ir-complete-receipts.zip`. The committed JSON records artifact hashes,
source IDs/links, per-operation decisions, provenance and measurements for review.
