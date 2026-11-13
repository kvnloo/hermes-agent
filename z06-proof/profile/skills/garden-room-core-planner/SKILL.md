---
name: garden-room-core-planner
description: Use when changing Garden Room geometry or optimizer.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [garden-room, threejs, geometry, optimization]
    related_skills: [garden-room-zen-module-qualification, rendered-ui-qualification]
---

# Garden Room core planner

## When to Use
Use for compass migrations, room constraints, arrangement scoring, or core dock/scene-filter changes.

## Workflow

- Inspect the real refs with vision before changing handedness. Photo descriptions can conflate white doors beyond a broad hall arch with an additional room opening; ask rather than invent geometry. Compass direction is owner-supplied, not recoverable from an unlabelled photograph.
- For x=east, z=south, rotate clockwise using x'=depth-z, z'=x, quarter-turn rot'=(rot+1)%4. Preserve polygon vertex order and edge-local window/opening indices and distances; the same edge then rotates with its physical wall. Back up all saved state/layouts before migration, mark the schema version, migrate legacy item-only saved layouts, and prove idempotence in a disposable directory under TMPDIR. Normalize incoming old-version writes too, otherwise stale tabs can restore the old compass.
- Treat each plant's pot footprint plus 5–10 cm breathing room as physical constraints. Do not let different support IDs hide collisions, infer support from full containment and capacity, or ignore a tall fridge merely because a plant is raised. Use a 72 cm corridor plus doorway/fridge swing clearances. Apply only proposals with no hard warnings. Do not add unobserved furniture to the current layout; editable optional stands can be user-added.
- A largest-first greedy pack plus annealing can trap large pots in floor slivers while small pots occupy shelves. Add plant position swaps before deterministic conflict repair so a smaller pot can occupy the narrow slot and release a shelf for the larger plant. Ensure repair references the returned candidate collection, not the annealer's discarded working collection. Reassignment of stake lights must not lower the accepted score.
- Run expensive proposals in a Worker and show results progressively, preserving the synchronous GR API for module compatibility. If serializing pure functions into a Blob worker, explicitly include every constant/helper and assert seeded worker/direct score parity to prevent a second drifting optimizer.
- Consolidate ar/voice/chat/scan/scan_live registrations into GR.addHubItem; legacy GR.addDock calls for those keys must route automatically. Sort optional dock entries deterministically because asynchronous module imports otherwise reorder them between reloads. Keep Real as an Explore scene filter; do not silently align image-generated splats lacking calibration.
- In browser tests route GET /api/state to {}, intercept writes, and inject the desired real saved fixture through localStorage. Also isolate layouts and Zen progress. Verify owner bytes are unchanged after tests. Run tests/phone.mjs and the zen/voice/ar/history suites; AR now enters via the Live hub. Check 412x915 screenshots with vision and fit the entire top view including raised walls, not just the floor.
- garden_room has no private Git remote. github.com/kvnloo/garden-room is a PUBLIC scrubbed snapshot (tools/publish_public.py, one commit per publish, unrelated history). Never push working branches there, because that publishes home photos and private history. Hand over a bundle or patches and ask the owner where a private remote should live.
- Equipment proxies: the listing's "Number of Levels" and "N shelves" often count boards on staggered multi-tower stands. Cross-check the spec-table count against the title and bullets, and test the shelf gap (uniform gaps under 20 cm cannot hold pots). Draw staggered stands as two towers plus centre bridges (boards = 2k + c, levels = k + c), and label the result approximate. For a planner close-up, hide the large item group and the billboards for that one shot only: GR.meshOf does not hide plant meshes.
- To run a branch for the owner, start a spare-port worktree server (systemd-run --user transient unit) and expose it with `tailscale serve --bg --https=<port> http://127.0.0.1:<port>`. WebXR, the camera and the mic need that HTTPS ts.net origin. The worktree data/.token differs from main's. A PWA share_target only reaches an installed PWA of the same origin.
- For scan imports, keep real nonmetric photo/COLMAP records separate from injected metric test contracts; never promote arbitrary scale to metres. Match globally across all 25 appearance candidates, preserve unseen items, and recheck composed fridge swings. Use GR.saveLayout with exact readback and the shared GR.applyPlan mesh rebuild, not data-only moves. Capture the review baseline before its asynchronous request so edits during that request cannot be overwritten. Before a top-view screenshot, click #ar-close and await #gr-ar hidden: GR.ar.stop() alone ends sensors but leaves the overlay visible.
