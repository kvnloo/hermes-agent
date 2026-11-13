---
name: gdp-wired-law-measurement
description: "Use when measuring gdp-wired law mutation coverage."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [verification, mutation, gdp-wired]
---

# gdp-wired law measurement

## When to Use

Use for shared gdp-wired mutation batteries, suite kill matrices, survivor calibration, or recovery of an interrupted measurement run.

## Procedure

- Read the experiment's current contract and compute-routing brief before acting; these override remembered paths and budgets. Keep code isolated under the assigned tools worktree and never patch the trusted kernel to improve a score.
- Use the generic `z0/tools/battery.ts` against a module exporting `bendLaws` and `extras` in `z0/entry.ts` shape. Group identical compiled implementations and union their laws before mutation, otherwise repeated Entries inflate denominators and miss suite-level kills.
- Keep a machine's laws fixed while editing one implementation AST site. For Fun decisions, retain public returns/law/relate callbacks and re-run unchanged specification callbacks over a changed return expression. Never structurally replace matching terms in an inlined goal: a literal or input can occur independently in the spec and output. Bare decide has no implementation/spec boundary; mark unsupported instead of changing the law.
- A kill requires a concrete legal violating trace or decision draw. Refused arbitrary-state proof without a reachable violation is unknown. A survivor requires proven AND kernel checked. Sample agreement establishes only likely equivalence, not equivalence; preserve unknowns in the score denominator.
- Serialize Map witnesses explicitly; vanilla JSON.stringify silently turns maps into empty objects and destroys replay evidence.
- Hand-check selected survivors with explicit legal traces and every suite law monitored. For equivalent comparisons such as natural x=0 versus x<=0, kernel-check the universal local predicate equivalence rather than relying only on samples.
- Route every proof, battery, test and typecheck to the authorized MBP fleet lane. `bunx` may be absent there; use `bun node_modules/typescript/bin/tsc`. A tools-scoped tsconfig avoids typechecking the entire large example/test tree under a 2 GiB budget. Bound typechecks and report resource timeouts honestly.
- Bound the whole mutant's diagnostic proof work with one shared deadline, not a fresh deadline per law. Reuse a proven+checked suite proof for its constituent law cells; skip remaining diagnostics explicitly as unknown once the deadline is exhausted. Otherwise a large law suite multiplies the nominal per-mutant budget into minutes. Keep concrete run monitoring independent of proof refusal.
- Keep checkpoint JSON `complete:false` until every Entry and mutation group finishes. Preserve superseded/partial runs outside canonical battery paths. Aggregation must tolerate missing families and retain auxiliary remeasurements separately rather than adding repeated measurements to the same total.
- After OOM recovery, commit the recovered implementation before resuming expensive work. Re-observe git state and retain every fleet job ID, source commit, seed, cap, unknown count and runtime in the report.
