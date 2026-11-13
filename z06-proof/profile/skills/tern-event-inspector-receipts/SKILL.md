---
name: tern-event-inspector-receipts
description: "Use when building event-fed Tern inspector sheets."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [tern, inspector, events, testing]
    related_skills: [tern-action-shortcut-receipts]
---

# Event-fed Tern inspector receipts

## When to Use

Use for read-only child-agent or event-fed detail sheets in the Tern frontend.

- Scope selections by the owning tool-call identity plus the stable child id. Legacy task-index ids repeat across delegations; never select by index or goal globally.
- Retain received tools and notes in the existing transcript projection, not a second inspector store. Derive the open sheet from that projection each frame so late events and completion remain visible.
- Resolve jobs-sheet entry points by exact canonical child id and owner session. If no observed transcript child matches a job, keep ordinary job detail rather than guessing or inventing history.
- Use the existing centralized sheet action bindings and app-owned overlay identity for scrolling. Send scroll commands only to a sheet descendant; verify long-log geometry actually moves under End or PageDown, not just that a command was emitted.
- Block late native composer edits and sends during read-only visits as well as parsed keys. Assert exact draft, cursor and focus readback for both Escape and the close button.
- Exercise real SDK Session handshakes and native node actions in Vitest. Disable splash in fixtures, include same-index children in different delegations, stream additional tools while open, and complete the parent turn before the child settles.
- Prove row-action coverage by temporarily disabling its dispatch and observing the new tests fail, then restore and rerun the complete gates.
- For isolated E2E, allowlist subagent notifications in the fixture recorder, tag them fixture-replay, and test a real row click plus final status and draft readback. Keep all RPC responses real and refuse prompt/control writes. A signed-out ordinary-window gate remains blocked; report separate tern-serve evidence honestly.
