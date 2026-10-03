# Current-main importer memory-budget integration

Integration `9c56a7c6b76d93717e0eff4a861fcfc8ea953ec9`, tree `988e23ea1ce5c8d81cebdc42e13de266fd397a2b`, retains these exact parents:

1. Pinned authoritative upstream main `bd0affe5e5f723579df8902852f5d0c47795f355`.
2. **John Paul Soliva / jonpol01**'s original `6287208a45fe01d09bd85a86f5f7fc502671fcf7`, [upstream #123570](https://github.com/NousResearch/hermes-agent/pull/123570).

The author's patch, tests, documentation, commit and authorship remain intact. Codex prepared the local integration under Kevin Rajan's direction. [Fork #184](https://github.com/kvnloo/hermes-agent/pull/184) remains Kevin's original evidence carrier at `b54cb36f5a63d049a8ff9ec62f6278c172cd5c77`; no existing ref is replaced. This publication does not merge either PR or establish upstream ownership.

## Why this is new integration evidence

Fresh authoritative main ref and branch APIs agree on bd0affe; the upstream PR remains open/unmerged at 6287208a, with no new review or owner direction. Main still imports up to a hardcoded 20,000 characters; the author reads the destination memory budget and reports overflow. The author is one commit beyond merge base `d0288be5b3330d2442e3907185b8e9d0958297bb`, while main is 3771 commits beyond it.

Automatic composition changes only three files against main: importer, its existing tests, and one documentation line (53 additions/5 deletions). [Exact delta](main-delta.patch). Stable patch-id `20e30c89630e312afd2695ab40fc7d19ea5ecdc6` matches the author patch. Main's removed plugin-compatibility aliases remain removed. No new production logic, corrective patch, test case or policy was authored for this integration.

Prerequisite audit found the same default 2200, flat memory configuration/int coercion, and MemoryStore implementation. Main's newer memory_tool metrics wrapper remains in use, so the existing consumer cases actually exercise current-main dispatch, not an old module substituted into it. Source and consumer reviews found no blocker.

Kevin's [earlier exact-head 52-pass/negative/restored result](https://github.com/NousResearch/hermes-agent/pull/123570#issuecomment-5858818493) is historical. Neither it nor the completed earlier ancestor qualification was rerun or counted as fresh work. This receipt qualifies only the current-main composition below.

## Matched executed results

| Exact source | Importer selection | MemoryStore guards | Total |
|---|---|---|---|
| Integration 9c56a7c6 | 52 PASS | 8 PASS | **60 PASS**, exit0 |
| Whole pinned main bd0 + identical final importer test overlay | 50 PASS / 2 FAIL | 8 PASS | **58 PASS / 2 FAIL**, exit1 |
| Independent final-commit consumer rerun | 2 existing parameter cases PASS | Not repeated | **2 PASS**, exit0 |

The independent two are a subset of 60, not additional unique coverage. No new cases were added. Independent source review verified parents/tree, author patch-id and exact test bytes; independent consumer review executed the final two cases, inspected matched-main failures and found no blocker. Root reviewed the final delta and evidence.

Both negative failures are the existing parameterizations of `TestMergeSemantics::test_import_stays_within_the_memory_stores_limit`: actual imported length 6377 exceeds loaded limit 2200 (default) or 3000 (explicit). They fail on current-main production at the real length assertion, not during setup or a historical-parent substitution. Control has only the identical importer test file overlaid; production is untouched.

The cases call real import execution, write synthetic MEMORY.md, load the real on-disk MemoryStore, then require successful memory_tool remove/add operations. Profile home/config/source trees are owned temporary fixtures. No real credentials, user configuration, provider connection or paid call is involved. The negative stops at length before mutations; it does not independently prove failure sensitivity for each mutation. The consumer does not reload disk after remove/add. Eight inherited guard cases supplement ordinary add, overflow, remove, persistence/dedup loading and over-limit warnings; these are not the entire memory suite. The 52 importer cases retain existing dry-run, idempotence, backup/preservation and malformed-input checks.

## Reproduction with existing dependencies

Use separate disposable worktrees. Candidate checkout must be exact 9c56; control checkout must be exact bd0. Copy only `tests/hermes_cli/test_agent_import.py` from the candidate into the control, preserving bytes. Its SHA256 must be `687ad06d95017609896748068bf772d87b1c4671dc28278553b9b764597ccb8c` in both. No production file is copied to the control.

From each respective worktree run the same canonical selection, using an already available suitable Python environment and writable canonical scratch:

```sh
HERMES_PYTHON=/path/to/existing/python HERMES_TEST_FILE_RETRIES=0 HERMES_TEST_WORKERS=1 bash scripts/run_tests.sh tests/hermes_cli/test_agent_import.py tests/tools/test_memory_tool.py -k 'test_agent_import or test_add_entry or test_overflow_returns_consolidation_context or TestMemoryStoreRemove or TestMemoryStorePersistence or TestMemoryStoreCharLimitOnLoad' -q --tb=short
```

Expected outcomes are 60 pass on the integration, 58 pass/2 behavioral failures on the exact-main control. Independent focused command uses only the importer file with `-k test_import_stays_within_the_memory_stores_limit`. Existing dependencies were reused; no installs, update commands, service launches, network/model calls or CI reruns were needed. [Full source bindings](source-bindings.json), [independent source audit](independent-source-audit.json), [independent consumer bindings](independent-consumer-bindings.json).

## Limits and preserved holds

This is scoped current-main integration qualification, not whole-PR, release, async, native UI or all-configuration approval. The original importer reads destination raw config; effective/managed overlays and malformed-setting policy are not exhaustively aligned by these tests. No config architecture, memory eviction policy or overlapping proposal is imported. Source audit used overlapping #124064/#127318 only as author-supplied context, not new ownership or qualification.

Receipts contain public source provenance, hashes, a public code delta and synthetic-fixture results only. Raw logs, real configuration, private machine paths and credentials are excluded. Publication uses new downstream refs only; hosted CI is read-only checked afterward. Empty checks/statuses/runs mean **NOT_RUN**, never PASS. All existing owner and installation holds remain intact, including TUI after-landing, backup critical-file policy, memory-spill/headroom/checkpoint/native decisions, #123578, #417 and #131689. Separate CUA/Bend work remains untouched.
