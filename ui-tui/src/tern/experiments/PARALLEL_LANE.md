# Parallel lane — native subagents

Parent baseline: `exp/tern-ux-omp-baseline` @ `fdf6a900`
Parent PR: #437
Umbrella: #432 / #436

## Goal

Project Hermes' existing subagent/delegation state into Tern-native `agent` nodes while preserving Hermes as the authority for lineage, steering and interruption.

## First invariant

One Hermes subagent id maps to one stable native node for its lifetime.

Only authoritative values are shown: goal/label, lifecycle, model, active/last tool facts, elapsed time and existing token/cost data when present.

## Initial slice

1. RED contract tests for stable agent identity.
2. generic native `agent` projection from existing `SubagentProgress`.
3. running → terminal-state updates in place.
4. no inferred percent-complete.
5. inspect/expand behavior without losing transcript position.
6. steering/interrupt actions continue through existing Hermes controls only.

## Hard guards

- no inferred completion from elapsed time/tool count/tokens
- no second delegation registry
- no renderer-owned steering authority
- no hidden failure/waiting state
- Ink fallback when `agent` kind is unavailable

## Provenance

Tern/TSP: Stencil Labs.
OMP native agents reference: Can Bölük / Stencil Labs.
Hermes delegation semantics: Hermes contributors.
Experiment direction: Kevin Rajan.
