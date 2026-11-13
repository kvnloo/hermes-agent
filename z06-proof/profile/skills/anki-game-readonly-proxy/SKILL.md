---
name: anki-game-readonly-proxy
description: Use when wiring read-only Anki snapshots into a game.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [anki, readonly, integration, terminal-only]
    related_skills: [anki-disposable-fsrs-bridge, test-driven-development, focus-safe-desktop-automation]
---

# Read-only Anki-to-game integration

## When to Use

Use for local game-server adapters that display stock Anki note/card identities and next-available queues without modifying Anki or palace bindings.

## Workflow

- Obey terminal-only scope literally: run unit/typecheck/build/HTTP checks, never a browser, GUI, compositor, screenshots/OCR or workspace/focus probes. GUI verification being blocked does not block backend implementation.
- Read the integration contract and canonical Anki bridge README before coding. If a lane lacks peer source, discover the main worktree with `git worktree list` and read only the necessary public contract there; do not cherry-pick or modify peer/vendor/main files.
- Pin the server-side upstream to an exact loopback host/port. Forward only exact allowlisted GET paths; deny request bodies, queries, URL aliases, writes and redirects. Enforce exact Host/Origin on the game endpoint. Do not forward browser cookies, authorization or Origin headers.
- Bound upstream total time (not just idle timeout), header size and streamed body bytes. Project validated JSON into a strict output allowlist; do not relay raw collection fields or upstream error bodies. Fail visibly unavailable on malformed, stale or inconsistent data.
- Cross-check decimal-string note/card IDs against stable concept IDs. Preserve locus geometry, theme identity and saved-state/event schemas. Treat Anki next-available as including new/learning-ahead cards, not as a derived due schedule.
- Keep runtime snapshots in memory only. Expire availability, clear it on failed refresh, and label frozen public offline content separately. Game self-reports remain spatial_practice, never Anki review writes.
- Test a fixed-target proxy against ephemeral synthetic HTTP fixtures by replacing only its low-level transport inside the test process. Do not ship arbitrary-URL or fixture environment overrides. Test silence and slow trickles, oversized streams, malformed/stale data, origin/path/method security, and bridge restart.
- Add a one-command terminal-only real readback that owns ephemeral game servers, compares every note/card reference and public concept with direct GETs, validates served HTML/assets, checks unchanged source bytes and an empty isolated outbox, and closes only its owned listeners. Never fabricate a successful real result from fixtures.
- Verify independent frontend snapshot state with reordered inputs, unavailable/stale/empty queues, identifier changes, and fresh-client restart. Distinguish these tests and HTTP output contracts from unverified GUI appearance.
- Keep private evidence outside Git, commit only the owned lane files, and include the exact commit plus real command outputs in a receipt. Parent integration owns live service launch/restart.
