---
name: z0int-verifier-budget-gates
description: "Use when changing z0int verifier or tick budgets."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [z0int, verification, deadlines, testing]
---
# z0int verifier budget gates

## When to Use

Use for verifier deadline propagation, partial reporting, bounded continuation, and loop-tick regression qualification in z0intelligence.

## Procedure

- Read `outcome_verifier.py`, `loop_tick.py`, and the affected tests before changing the budget boundary. Preserve signal, promotion, and learning semantics.
- Pass a keyword-only monotonic deadline through both Claude transcript and AgentsView session sweeps. Check before session lookup/join; finish started sessions atomically. Report partial separately from successful completion, including visited and deferred counts.
- Do not run global GitHub planning/prefetch across all sessions when a deadline applies. Per-session cancellation is cooperative, not an in-flight subprocess hard timeout.
- Ensure bounded retries prioritize sessions containing unwritten captured turns. Append idempotency alone does not prevent repeatedly spending the budget on the first already-written session. Preserve existing ledger bytes and order.
- Cover expired deadlines, exact fake-clock tick exhaustion, both session readers, and bounded retries with append-prefix assertions. Include an opportunity-only first session with no observed outcome: zero-row diagnostic sessions must not repeatedly consume every bounded retry and starve sessions that can append unwritten rows. Use synthetic homes and fake/disabled GitHub; no sleeps or live network in regressions.
- Run only the task-authorized affected test files, without xdist. A typical scope is test_verify_harness.py, test_outcome_verifier.py, test_loop_tick.py, test_turn_readers.py, and test_loop_data_sources.py.
- Fixture storage must be outside Git worktrees and outside protected harness-data roots. Some Hermes profile scratch roots are intentionally refused by legacy imports; repository-local temporary homes are also refused by the tick. Use an approved external synthetic test root rather than patching or bypassing guards.
- Read `.github/scripts/check-receipt.py` before publishing. PR evidence needs issue, base/head SHA, and truthful red/green test evidence; preserve any explicitly requested final attribution footer. Report hosted failures outside modified surfaces rather than claiming all CI passed.
