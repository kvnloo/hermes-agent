# Hermes × Tern UX experiment harness

This directory is the common, renderer-independent harness for issue #436.

It does **not** choose a design. It keeps the A/B/C branches honest by giving every
variant the same scripted states, viewport sizes, attention vocabulary and receipt
format.

## Fixture

`TERN_UX_FIXTURE` is the fixed 14-step flow from #436:

1. fresh session
2. bounded request
3. thinking
4. read/search
5. write/edit
6. subagent starts
7. queued follow-up
8. approval
9. tool failure + recovery
10. successful completion
11. model picker
12. background/agent inspection
13. split preview
14. return to chat

Run every step at `narrow`, `normal` and `wide`.

Changing the fixture requires bumping `TERN_UX_FIXTURE_VERSION`; receipts from
different versions must not be compared as if they were the same experiment.

## Instrumentation contract

Each variant emits an `ExperimentFrame` describing only what it actually shows.
The harness derives:

- simultaneous high-salience element count
- persistent element count
- transient transcript/status rows
- coarse transcript/live-state/composer eye travel
- needs-user rank
- attention-contract violations
- optional measured time-to-needs-user from a human glance test

The validator intentionally encodes the design constraints we already agreed on:

- a needs-user step has one singular visual peak
- ambient/completed state cannot stay loud
- determinate progress requires a real denominator
- every state must answer: what is it doing, what happens next, where do I type,
  and how do I inspect more?

This is a comparison instrument, not a pixel-quality score.

## Branches

- `exp/tern-ux-base` — this harness + shared deterministic fixtures only
- `exp/tern-ux-omp-baseline` — A, OMP/Tern-native baseline
- `exp/tern-ux-hermes-baseline` — B, Hermes design-language baseline
- `exp/tern-ux-attention-minimal` — C, attention-minimal hybrid

Variant branches should import this harness rather than copy it.

## Provenance

Keep source credit attached to every implementation note:

- Tern/TSP — Stencil Labs
- mature OMP native Tern interaction patterns — Can Bölük / Stencil Labs
- Hermes Desktop/TUI behavior and design language — Hermes contributors

The canonical visual references and ownership rules live in issue #436.
