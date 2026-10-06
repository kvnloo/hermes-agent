# Parallel lane — native tool lifecycle

Parent baseline: `exp/tern-ux-omp-baseline` @ `fdf6a900`
Parent PR: #437
Umbrella: #432 / #436

## Goal

Project Hermes' existing authoritative tool lifecycle into Tern-native semantic tool nodes without moving tool authority into the renderer.

## First invariant

A single tool call keeps one stable native id across:

`pending/running → done | error | cancelled`

A later recovery call must be a different node; it must never rewrite a failed historical call into success.

## Inputs already owned by Hermes

- live `ActiveTool[]` from `turnStore`
- settled trail/diff segments already produced by `turnController`
- existing tool labels, args/context, duration, summaries and result text

## Initial slice

1. RED contract tests for stable tool identity.
2. Generic native `tool` projection only.
3. running + done + failure + cancellation states.
4. preserve consequential failure visibility.
5. no specialized per-tool renderer matrix yet.
6. share the existing transcript/composer frame-credit window.

## Hard guards

- no fake progress
- no tool execution from TSP events
- no second tool-state store
- no mutation of settled failure history
- no arbitrary animation loop
- Ink remains fallback when `tool` kind is unavailable

## Provenance

Tern/TSP: Stencil Labs.
OMP native tool projection reference: Can Bölük / Stencil Labs.
Hermes tool/runtime semantics: Hermes contributors.
Experiment direction: Kevin Rajan.
