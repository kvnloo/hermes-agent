# Variant A — OMP/Tern-native baseline

Issue: #436

## Question

What does Hermes score like if we project it as closely as practical into the
**proven native OMP/Tern presentation grammar** before adding Hermes-specific
visual language?

## Canonical evidence

Primary visual reference:

- https://stencil.so/tern — **03 Graphics**
- compare `omp ANSI any terminal` with `omp native drawn by Tern`

Implementation reference:

- `can1357/oh-my-pi` current TSP stack, credited to Can Bölük / Stencil Labs
- the pinned implementation map already lives in #432

Do not use ordinary OMP terminal screenshots as the design target.

## First implementation slice

Keep it deliberately small:

1. one persistent inline surface
2. native transcript in `main`
3. native composer + live work facts in `dock`
4. one consequential prompt in `layer`
5. generic tool and agent semantics
6. no Hermes-specific navigation chrome

Run the exact `tern-ux-v1` fixture at all three viewport widths before adding
special cases.

## Success condition

This is the **control**, not the winner. It should establish what the most
mature known Tern-native coding-agent UX does on the shared Hermes state model.
