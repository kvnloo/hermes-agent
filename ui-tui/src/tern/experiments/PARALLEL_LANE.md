# Parallel lane — real Tern capture + attention receipts

Parent baseline: `exp/tern-ux-omp-baseline` @ `fdf6a900`
Parent PR: #437
Umbrella: #436

## Goal

Validate Variant A in **real Tern**, not the fake-peer PTY or authored replay.

This lane owns capture/measurement only. It should not become another renderer implementation branch.

## Required matrix

Run the same `tern-ux-v1` flow at:

- 80×28
- 120×36
- 180×44

Capture at least:

- idle / ready
- live streaming
- tool running
- tool failure + recovery
- subagent running
- queued follow-up
- approval / needs-user state
- completion
- return-to-chat with preserved draft

## Evidence rules

- actual Tern window only
- no generated mockups counted as evidence
- no ANSI OMP screenshots substituted for native Tern
- record exact commit SHA + Tern version + pane dimensions
- distinguish fixture replay from live Hermes
- keep `liveTernVerified=false` until a real run is captured

## Attention receipts

Use the existing five-second glance test and record:

- time to find needs-user state
- simultaneous high-salience elements
- persistent element count
- transient rows
- transcript ↔ state ↔ composer eye travel
- answer correctness for doing / needs-me / next / type / inspect

## Non-goals

- redesigning Variant A
- changing Hermes runtime state
- inventing new metrics mid-run
- promoting A before B/C have comparable receipts
