---
name: tern-sdk-retention-gates
description: Use when implementing Tern transcript retention.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [tern, retention, performance, typescript]
    related_skills: [benchmark-checklist, tern-action-shortcut-receipts]
---

# Tern SDK retention gates

## When to Use

Use when adding settling, eviction, bounded rendering or lazy history restoration to a Tern SDK frontend.

## Procedure

- Read the installed SDK surface, wire event union and published retention protocol before designing reload. SDK 0.1.0 has settle/send/gone but no child adopt/forget or viewport/reload event; whole-surface OpenOptions.adopt is not entry adoption. Never invent an event. Document explicit history navigation as a capability-limited fallback.
- Separate gateway-owned transcript data from evictable presentation trees. Keep IDs/order/revision metadata, release settled JSX caches and SDK Trees, and scan the hot/protected set on tokens. Recompute structural membership at turn boundaries and track late old-entry invalidations explicitly.
- Own incremental main children through public Tree/View.ops and Surface.send when the SDK cannot forget subtrees. Keep chrome in a small SDK reconciler and combine its ops with main updates in one credit-paced real frame; split chrome/main sends can queue edits to a subtree evicted between them.
- Ignore foreign/unknown gone IDs and never target an evicted ID with del/set/text/settle. Re-add before the next resident sibling using original IDs. Protect the bounded requested reading page until another page replaces it; settling it immediately can cause the budget pass to evict it again before display.
- Preserve actions without storing all historical handler closures. Rebuild the addressed settled entry only on an actual action, recheck its current session/lifetime at execution, and let native toggle events reach the fold-state mirror.
- Use the existing real App/SDK/encoder benchmark; separate cold upload from streaming p95/bytes. Warm both variants equally before measured cases, alternate history sizes and before/after order, use fresh processes for repeated comparisons, and keep raw results plus machine/load/source receipts. Cold JIT differences can make a shared-host Vitest wall-clock ratio flaky even when the deterministic rebuild counter passes.
- Prove emitted wire identity/order/text/tool results, protected running/approval/failure state, no settled rebuilds on tokens, bounded reload pages, stale actions, late updates and blocked/hidden final close. Verify tern-serve separately from native-window and mark authentication-gated native work blocked rather than green.
