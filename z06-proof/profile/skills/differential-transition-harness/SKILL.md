---
name: differential-transition-harness
description: Use when proving a pure transition with replayable tapes.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [testing, rules, differential, property-tests]
    related_skills: [test-driven-development, rule-profile-provenance-freeze]
---

# Differential transition harness

## When to Use

Use when a new pure transition must match current engine behavior before a second implementation or a second domain is allowed to change the protocol. Do not use this for a provenance-only audit, and do not fix known semantic debt while extracting the seam.

## Procedure

1. Branch a new worktree from the pinned base SHA. Leave the previous checkout untouched. Do not reset, stash, rebase, or merge.
2. Write a source-scan test for the generic files first, in a file that only reads text. A bundler resolves `import()`, including dynamic import, at transform time, so a test file that names a missing module fails to load and no assertion runs. Watch the scan fail because the files are absent. It must stay red if those files import the domain implementation, domain constants, or a domain-name discriminator.
3. Keep the generic layer to tape, runner, and compare. It may clone and align steps. It must not read domain fields or interpret domain events.
4. Put generators, event mapping, normalization, oracle scope, and invariants in the domain adapter. Compare externally meaningful observations, not private object layouts. A missing effect list means that path does not emit effects; do not treat it as a mismatch.
5. Run the same seeded tape through production behavior, the compatibility adapter, and the generic transition. Include an independent oracle only on the subset it actually models. Abstain, and stay abstained after an event the oracle cannot follow, rather than comparing a stale oracle state.
6. Classify the first divergence before changing code: production bug, adapter bug, generic kernel bug, stale or limited oracle, harness bug, intentional rule difference, known preserved debt, or intentional test-only sabotage. The sabotage class means production is the reference and the extra path is knowingly wrong. Never write that fixture as a production bug — the report becomes the evidence trail, and a later session will treat production as the thing that is wrong. Do not normalize a real difference away so the paths agree.
7. A same-assumption oracle is a witness, not rule authority. If it shares a known bug with production, agreement is not conformance. See `rule-profile-provenance-freeze`.
8. Do not treat a phase named terminal as match completion unless the profile's terminal predicate is match completion. A recorded-but-inert match-structure field stays out of the generic kernel.
9. Prove the harness can fail. Sabotage only inside a test-owned runner or a local model edit that is reverted before commit. Record the shortest failing tape inside the property callback — do not depend on the assertion error exposing a structured counterexample. Persist the formatted first-divergence report, including the sabotage class and the sentence that production is the reference. Then revert the mutation.
10. When replaying persisted supervision tapes, audit event serialization against the event constructors before comparing. A snapshot can omit host or successor fields, and owner routing dispositions may be projected outside the pure FSM. Record those omissions and compare raw process transitions, disposition projections, and outcome claims separately; never synthesize a log-read or Finish event to force agreement.
11. Bound tape length and run count. Record the seed. Do not add wall-clock assertions to semantic properties, and do not loosen an existing timing gate. If a new layer misses one, drop redundant copies on the hot path and re-run that gate in isolation against the baseline. A miss while the suite is loaded is not a semantic regression until that isolated comparison says so.
12. Commit tests and the fixture only when production behavior is unchanged. Publish or push only when the task authorizes it; a local-only experiment must stay local. A compare link is not a merge.
13. A proof language is another evidence path, not a runtime. Follow `references/proof-backend-spike.md`. Proof success is not equivalence to the existing implementation.

## Pitfalls

- Checkpoint a mutation matrix after each variant, including exact model/law fingerprints and the source revision. Resume identical completed cells instead of repeating a large monolithic matrix; a timeout must not discard the completed differential evidence.
- Audit mutations of shared helpers transitively. A lease helper mutation can also affect a device lock, while a mutation of a held-case predicate must not change the free case. Boundary tests should distinguish the original mutation from an accidentally stronger mutant.
- Scan generic source for domain tokens after every edit — a comment or a convenience import puts domain policy back in the kernel.
- Reconstructing the next step from the normalized observation drops fields the engine needs to continue — keep the real owner in the runner closure, and use the owner's serialize/restore for checkpoint equality.
- Skipping an out-of-scope event without deactivating the oracle desynchronizes later steps — once the oracle cannot follow, exclude it from the rest of that tape.
- For finite-control ports, enumerate the exact missing/false/true product and report raw-invalid probes separately. Match the externally returned result, not an intermediate eligibility gate; a rollback gate and the full action recommendation can deliberately use different codes.
- Do not reconstruct complete rule inputs from historical verdicts. Inventory tapes lacking required snapshot/source fields as unreplayable coverage debt, and keep synthetic fixture replay separate from real-history replay.
- Compare proof costs with matching measurement boundaries: report cold whole-command medians for both tools separately from warm per-law timings, and label whole-family time divided by law count as amortized rather than isolated per-law cost.
- Separate a read-only preflight from any hypothetical lifecycle consumer. A pure decision about observed facts is not an atomic transition, a lock, or authorization; label proposed coordinated protocols separately from production parity.
- Stream large finite-domain differentials and report the exact bounds, seed, group counts, source hashes, and negative control. Exhaustive bounded lists and representative count relations do not prove equivalence over arbitrary OS observations or unbounded values.
- Preserve an unchanged expensive law when bounding its proof search. Record an unknown/time-budget limitation separately from a concrete refutation; do not replace an arbitrary-event claim with a smaller or more constrained claim and call it the same proof. Use a subprocess timeout for a hard wall cap: an internal solver deadline may not cover preprocessing or certificate checking.
