---
name: gdp-wired-law-family-critic
description: Use when porting law families into a gdp-wired critic.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [verification, state-machines, differential-testing]
    related_skills: [differential-transition-harness]
---

# gdp-wired law-family critic

## When to Use

Use for a shadow-only port of an existing owner's laws, mutation battery, differential twin and real-history replay into gdp-wired.

## Procedure

1. Read the pinned source model, owner law file, proof helpers, mutants, runtime twin and replay adapter separately. Preserve owner claim names, order and quantifiers; helpers may strengthen induction but never replace the target claim.
2. Freeze source identity and keep private histories outside Git. Commit the importable port before proving. Follow the task's compute routing; a controller host under memory pressure must not run proving, typechecking, parity or replay as a fallback.
3. Separate reachable invariants from universal constructor step claims. Parameterize the latter's initial constructor so its guards are exercised without a long random prefix. Check both the original claim alone and the claim with independently proven helpers under `from:'any'`; explicitly document which helpers an observed-state caller must validate.
4. When flattening variants, compare constructor-relevant fields. Equality of all flat fields is a valid stronger substitute only when the encoding preserves irrelevant fields too. Do not turn an invalid numeric phase countermodel into a policy finding. State any unproved list-to-pointwise-board refinement explicitly.
5. Prove the unchanged claim, cross-check callback arithmetic against built expressions, compare interpreter and generated runtime, and retain a refused negative variant. A concrete negative witness must break the target claim, not merely an auxiliary invariant. Random tapes often never reach gated phases; supplement them with parameterized one-step witnesses and directed legal prefixes.
6. Replay every source mutant against every original claim. Keep refused-but-unwitnessed results separate from concrete kills. A generalized progress claim is valuable only after testing a non-equivalent mutant that survives the original suite, such as removing one permitted actor role while retaining the single role named by the original law.
7. Obtain differential expectations from the actual pinned runtime module, not a rewritten same-assumption oracle. Compare every step and refusal, preserve the real runtime state between events, record seed and tape bounds, and test missing-value boundaries separately. Never normalize a discovered null/sentinel divergence away.
8. Validate sabotage against an independently minted oracle tape. A synthetic zero-head path can be legal in a natural-number model while being refused by a Python twin with an absent head; use a complete-head path or explicitly retain that semantic difference.
9. Keep legal-transition theorem watches distinct from observed-evidence diagnostics. A refused action leaves a legal state and can satisfy every theorem while still representing a real violation in recorded evidence. Compare diagnostic codes/severities per item, classify metadata/time/ancestry scope gaps, and mark missing availability or cross-item information indeterminate rather than inventing it.
10. Keep proposed new policies visibly separate from owner laws. A counterexample to a proposed drift/freshness law is evidence for adjudication, not authority to change production. Record full commands, job IDs, source/commit provenance, exact counts, and honest non-proofs in the results report.
11. Adjudicate an alleged baseline escape against the unchanged source proof program and native twin tests, not only the truth of the ported theorem. A type-correct model restriction may preserve every theorem semantically yet invalidate the existing dependent proof terms; record that structural detection separately from behavioral test failures, and never repair proofs silently to manufacture an escape.
12. Preserve the source mutation runner's unique text anchors when constructing adjudication variants. Put an unchanged predicate in a helper if necessary; an unmatched mutation anchor is a harness failure, not evidence that a semantic defect survived or was detected. Run each variant from pristine source text and retain exact diffs and per-command exits.
11. Adjudicate an alleged A0 escape against the retained source proof and existing Python tests, not only the ported law propositions. Patch both original twins, print an actual non-equivalence witness, and run the unchanged PROOF.bend: proof helpers can depend definitionally on the old guard, payload or terminal transition and reject a mutant even when the stated laws remain mathematically true. Count this as an operational A0 detection when the experiment defines detection as proof-check failure; label the mechanism rather than claiming a semantic counterexample. Never repair the proof to manufacture an escape.
12. Establish a clean Python-test baseline before crediting test failures as mutant detection. A fleet image can lack both pytest and pip; those errors are infrastructure failures, not catches. If permitted, bootstrap hash-checked pure Python wheels into a job-local dependency directory and rerun on the assigned node, preserving versions and hashes; never fall back to the memory-constrained controller.
11. Adjudicate A0 escapes against the entire original pipeline, not only ported law formulas. Patch the actual twin and Bend model, execute a concrete before/after witness, rerun the unchanged proof file through the family's reference checker, and run existing Python tests. Implementation-dependent Bend proof terms and an exhaustive twin regression can already reject a mutant even when every abstract ported law remains true; record that as A0 detection rather than a new law-suite escape.
12. Reproduce IO outcome findings on the real pinned wrapper using fail-closed fake shell/service/delivery functions and isolated scratch paths. Keep simulated HEAD/delivery outcomes distinct from live observations, preserve error exits and diagnostic evidence, and include successful-reset or recovered-episode controls. Do not turn a hypothetical mutating consumer of a read-only receipt into a production mutation claim.
