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
- concrete realizations (PR/commit/tree state);\n- timestamped historical refresh states (evidence, never mutable current truth).

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

### E3 — #78207 (next)

Use the Vox Lockin stale-PR wave as a larger-scale classification dataset: `still_needed`, `already_on_main`, `moved`, and salvage-with-credit.

## Success criteria

The representation earns further work only if it makes current-main refreshes materially easier to review while preserving provenance. In particular:

1. invariants survive implementation drift;
2. independent operations do not share one artificial PR-level expiration date;
3. already-landed work is detectable before duplicate implementation;
4. semantic uncertainty stays explicit;
5. authors/diagnosers/reviewers keep credit across rematerializations.
