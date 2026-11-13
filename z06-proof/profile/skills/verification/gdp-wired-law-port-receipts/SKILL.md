---
name: gdp-wired-law-port-receipts
description: Use when porting source laws to gdp-wired.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [verification, proofs, differential]
    related_skills: [differential-transition-harness, systematic-debugging]
---

# gdp-wired law-port receipts

## When to Use

Use for source-faithful gdp-wired ports, mutation batteries, extractor qualification and private history replay.

## Procedure

1. Pin both sources and read the target repository's own gdp-wired skill. Keep source law names, order, quantifiers and literal witnesses unchanged; put generalizations in separate extras.
2. Substitute fixed source-law arguments into the builder rather than hoping random draws meet a sparse constant premise. Execute an actual concrete witness for each broken variant.
3. `rule.decide` does not expose step flags. Reuse the flag's expression explicitly in a decision instead of assuming it is present.
4. Direct carried-map evaluation with `evalC` needs maps and zero defaults, or the runtime's `carriedView`. Absent request-set cells are zero, not state-map declarations. Use `crossCheckDecision` to check callbacks against their built conditions.
5. Separate scalar sample magnitude from builder-check key bounds. `crossCheckDecision` enumerates keys through `bound`; a large arithmetic threshold can cause enormous repeated scans. Draw arithmetic at the needed magnitude while keeping the builder's key domain appropriate.
6. Prove bit-domain invariants for natural-valued ghost flags. Assigning only 0/1 on reachable runs does not constrain an arbitrary observed state without that invariant.
7. Use an unbounded log with occurrence ghosts for event-order extras and prove every helper. Report bare and helper-assisted `from:'any'` verdicts. Distinguish strict event positions from timestamp equality the original law permits.
8. A broken sequence variant must break the target ordering claim, not just a helper. Watch the target alone on an explicit trace; separately require kernel refusal. For a newly authored Bend law, run a target-only reference and mutant, then the mutant with only pre-existing laws/proofs. A generic proof helper may reject a source-local change even when no prior law states the missing behavior; distinguish that proof sensitivity from unique semantic coverage.
9. Extract unchanged real files and enumerate callable entries mechanically. Retry legitimate caller initial states where supported. Never relabel a hand model as extracted or claim real-code proofs when nothing extracted.
10. Separate controlled differential agreement from out-of-region challenges. Retain and classify first differences; do not normalize provenance, unknown identities or time precision into agreement. Include test-owned sabotage with production explicitly the reference.
11. Keep private replay inputs/artifacts outside Git. Missing historical instrumentation cannot become invented verifier receipts, authority, delegate liveness or prevention credit.
12. Persist rows incrementally and retain each command's exit code. A wrapper's final successful command is not a passing battery: validate row totals and strict status from fetched artifacts. Route heavy work to the approved compute lane.
13. In Bend mutation checks, inspect raw diagnostics and independently check the mutated model before crediting a law catch. `SOME PROOFS FAIL` also appears for parser errors, so require a well-typed mutant and a type mismatch at the intended theorem, not merely a wrapper's rejection count. Match only parameter/field scrutinees; put computed-value matching in its own helper.
14. Keep a minimal compiler probe when proofs and generated runs disagree. In pinned gdp-wired `3cdf37e`, a log with zero queries emits `let ;` and throws at the first compiled step, despite valid proofs. Preserve that raw failure. An unused observational query can avoid the emitter path without changing guards, but must itself be cross-checked; do not patch an out-of-scope core or call this a kernel soundness failure.
15. When a literal-set law stalls at quantified shape facts, expose the literal's redundant ground values at the relevant key rather than weaken the claim. Distinguish prover instantiation limitations from a real counterexample; the literal-to-map encoding remains an explicit obligation.
15. Isolate a newly authored law's mutant against the same checkout's pre-change laws and proofs. Require the new proof to fail at the named law while the old suite passes the identical mutant; retain raw output, not just the battery's refusal boolean. A constant wrong terminal transition can avoid incidental proof-normalization failures in unrelated invariants when testing absorption, while still providing a real one-event semantic counterexample. Keep generated proof sources synchronized with the checked proof file.
15. For an absorbing-state rule, quantify over arbitrary finite future event tapes and preserve the complete state payload, rather than checking one restart example. Retain raw target-mutant output and require an actual proof-failure marker; then remove only the newly added law/proof in a temporary mutant copy and rerun legacy proofs to establish whether the new law alone detects the bug. Update a generated proof's generator as well as its output.
