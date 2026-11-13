---
name: garden-room-zen-module-qualification
description: Use when extending Garden Room care and mood modules.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [threejs, garden-room, gamification, testing]
    related_skills: [threejs-real-gpu-receipts, rendered-ui-qualification]
---

# Garden Room care-module qualification

## When to Use

Use for care, mood, reward or animation modules layered on the Garden Room planner, and for their browser or route evidence.

## Workflow

- Discover the exact repository and dirty worktree first. Keep optional features inside `public/modules/<name>.js` exporting `init(GR)`, their own linked CSS, and `routes/<name>.py` exporting `handle(h, method, path) -> bool`; do not overwrite parallel `app.js` or `server.py` work.
- Read the current `GR` seam and scoring implementation. Treat `_sat` and exact overlap warnings as planner-owned facts. Virtual watering, trimming and feeding must not change light satisfaction, collision warnings, layout dimensions or saved positions.
- Use a shared canvas atlas and fixed instanced billboard pool for faces, thought bubbles and transient effects. Reuse matrix/vector objects per frame; throttle inventory and health scans. Capture each grow-light material's original emissive intensity in a WeakMap so rescans cannot integrate the pulse into the baseline.
- Keep care transforms on the model holder and preserve captured base transforms. Compose with history previews through a separate child growth wrapper rather than fighting for holder scale.
- Provide real touch targets for canvas thoughts and an accessible roster equivalent. Reserve HUD space next to optional voice controls; inspect actual screenshots because asynchronous module CSS can introduce collisions without console errors. Keep phone docks horizontally reachable and desktop docks evenly distributed.
- Persist a bounded care journal atomically under `data/zen/`; use revision checks, local fallback, online retries and GET readback before showing saved status. Document whether concurrent rewards merge additively or conservatively.
- Intercept **both** `/api/state` and `/api/zen/progress` in every browser test, including the original phone smoke: onboarding alone can otherwise award and write progress to the owner's journal. Backend route tests must point their data directory at a disposable directory under TMPDIR.
- Give the phone drag smoke a visible isolated small-pot fixture. The optimizer can place every small pot near the window outside the portrait camera crop; choosing the nearest optimized plant is not a guaranteed on-screen touch target.
- Use installed Chromium with Vulkan/ANGLE hardware flags and record the unmasked GPU renderer. Measure an actual five-second RAF window plus the module callback CPU cost; stagger real care actions during the window to keep transient pools active. A disabled-effects comparison that retains mood billboards is not a whole-module-removal baseline. Do not claim a physical phone's 60fps from a desktop GPU at phone dimensions.
- Inspect generated room, watering, quest, roster, narrow-phone and tablet PNGs. Verify repeated watering and repeated quest claims cannot farm rewards, cooldowns differ by family, night moods and reduced motion work, care does not alter the planner, offline care survives, and revision conflicts preserve logs. Rerun `node tests/phone.mjs` before completion.
- For a plant almanac, recover GrowTwin history by reading `PlantCareTwin.tsx` at historical commits, not just HEAD: later identity-review revisions remove the Almanac tab. If `ctx search` auto-refresh stalls, inspect `ctx search --help` and use `--refresh off` to query the existing generation without a new refresh. Keep the index freshness limitation explicit.
- Give almanac previews one detached WebGL renderer and copy only intersecting canvases into card-local 2D canvases. Dispose an offscreen-model LRU on close; test that reduced motion draws once. CSS grid cards inside a flex scroller need explicit max-content rows and noncollapsing card sizes: assert row boxes do not overlap and inspect the grid screenshot.
- Keep care references distinct from inventory identity, planner light estimates, virtual Zen scores and real history observations. Label editorial watering/climate bands as starting points, never measured ideals. Preserve unknown species and avoid inferring pet safety from an edible common name.
- The current History module may register only an item action, with no `GR.history` export. Detect at call time and open its existing History item action as a compatibility path rather than inventing a private API. Cover newest-photo sorting, actual history opening, selection plus camera framing, and absent optional modules.
- New route modules load at server startup. Verify on an isolated server first, then restart the live service and read back the exact authenticated endpoint before claiming deployment. Track only curated `data/almanac/` reference files explicitly when `data/` is ignored; never force-add the owner's journal, photos or token.
- In shared parallel work, rerun the original phone smoke after service restart. A newly loaded sibling module can introduce unrelated failing requests or persistence paths; report that exact endpoint and leave sibling-owned code untouched. New browser tests should intercept all mutating `/api/**` calls, not only known layout and Zen routes.
- Commit only owned files explicitly; generated screenshots and private care data remain ignored. Report measured values, test counts, screenshot paths, physical-device limitations and unbuilt ideas.
