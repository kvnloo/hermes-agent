# Change IR experiment

Tracking: #453
Upstream motivation: NousResearch/hermes-agent#134008

## Claim under test

A code diff is a temporary realization of a more durable contribution object. The durable object should preserve **why** a change exists and **what must remain true**, while implementations can be regenerated against newer repository states.

This experiment deliberately does **not** attempt autonomous rebasing first. It tests whether we can represent enough durable information to make a later refresh smaller, safer, and easier to review.

## Change packet

A fixture records:

- provenance and stable change identity;
- problem and desired outcomes;
- invariants / non-goals;
- architectural decisions and unresolved questions;
- independent semantic operations;
- semantic anchors (symbols and behavioral surfaces, never line numbers);
- verification contracts/evidence;
- concrete realizations (PR/commit/tree state);
- timestamped historical refresh states (evidence, never mutable current truth).

Refresh states for an operation:

- `still_needed`
- `already_on_main`
- `moved`
- `invalidated`
- `needs_decision`
- `unknown`

## Probe

`refresh_probe.py` scans a current checkout for the semantic anchors named by a fixture.

Example:

```bash
python experiments/change_ir/refresh_probe.py \
  experiments/change_ir/fixtures/105624.json \
  --repo .
```

The output is intentionally conservative:

- `present`: all required textual anchors were found;
- `partial`: only some anchor evidence survived;
- `missing`: no configured textual evidence was found.

These are **anchor states, not semantic refresh states**. A `present` symbol does not prove behavior is equivalent; a `missing` symbol may mean the behavior moved or was renamed. An agent/human must use the evidence to classify the operation. Historical fixture states are timestamped baselines; each run records a new classification instead of rewriting history.

That distinction is the point of the experiment: make architectural drift visible without pretending textual matching solved semantic equivalence.

## Fixtures

### E1 — #105624

Tests preservation of the same change intent while Telegram's send and bot-observation architecture moves underneath it.

### E2 — #31157

Tests whether an old atomic PR can be decomposed into independently aging operations: salvage, reject/relocate, or require additional proof.

### E3 — #78207 — complete

The 17-PR Vox stale-wave was reclassified against current main. Result: 8 clearly implemented/superseded, 2 mixed-state, 7 requiring a fresh decision, and **0/17 safely replayable as-is**. See `runs/002-vox-17-prs.md`.

## Success criteria

The representation earns further work only if it makes current-main refreshes materially easier to review while preserving provenance. In particular:

1. invariants survive implementation drift;
2. independent operations do not share one artificial PR-level expiration date;
3. already-landed work is detectable before duplicate implementation;
4. semantic uncertainty stays explicit;
5. authors/diagnosers/reviewers keep credit across rematerializations.


## Final result

**Experiment complete — hypothesis supported.**

The decisive rematerialization took one surviving operation from #105624 and reconstructed it against current main instead of replaying the full stale PR:

- 824 → 82 changed lines (**90.0% reduction**)
- 67,555 → 12,540 measured review-context characters (**81.4% reduction**)
- **5.39× smaller** review packet

All five experimental criteria passed at the representation/workflow level. The branch-local execution workflow for the rematerialized slice is still queued behind the fork's Actions backlog and is explicitly not counted as a test pass.

See `FINAL.md` for the full assessment.
