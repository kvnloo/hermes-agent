---
name: reference-led-ui-recovery
description: Use when recovering approved UI styles from history.
---

# Reference-led UI recovery

## Procedure

1. When Kevin names a library or says a component was used in another repo, recover that actual implementation before designing anything. Resolve uncertain repo spelling through his repo list and cross-harness history, inspect the canonical source/imports and upstream attribution, and pin the source revision. Reuse the library or faithfully port its rendering/behavior when the target runtime differs; do not reinterpret a reuse request as "inspired by" and invent a replacement. Carry the exact source locator and reuse requirement into every worker brief. Inspect existing UI code, screenshots and Git history before inventing a replacement. Use `git log --all -- <UI paths>`, `git show --stat <ref>`, and `git show <ref>:<file>` to locate approved theme freezes. Compare historical static pages with live components: approved styling may never have reached the runtime renderer.
2. Refresh relevant issue bodies/comments for newer image/video references. Inspect actual images and video frames before borrowing design or motion. If an attachment lacks a retrievable locator, report the gap; video-description prose is not visual evidence.
3. Extract typography, surfaces, strokes, geometry, accents and interactions separately from composition and content. Kevin's style requests do not imply changing density or forcing screenshot labels onto the product. Let content and density remain application-driven.
4. Ignore compression grain and artifacting. Recreate intentional dots, rings, brackets and connectors with crisp CSS/SVG and local fonts rather than raster textures. Clean instrument panels do not need generic noise, glass or heavy shadows.
5. When requested, recover style first in an isolated preview preserving the functional worktree/runtime. Build reusable theme tokens and primitives; explicitly label static historical architecture. Defer dynamic reintegration and content reorganization until the visual direction works.
6. Exercise the actual browser at desktop and narrow sizes, both themes, keyboard focus and disclosures. Compare screenshots with the references. Syntax checks and HTTP success alone do not prove visual fidelity or mounted interactions.
7. Verify preview URL/assets against intended source, then open it in the requested browser under the user's foreground permission. Read back page/window identity before claiming it opened. Keep preview, diagnostic and production identities distinct.
8. Reintegrate approved primitives into existing dynamic components without changing evidence or authority semantics. Preserve unknown/stale/degraded states; decorative animation must not imply witnessed execution or telemetry.

## Finding and showing reusable components

- Inspect implementation files, not PR titles or summaries, before declaring a library recovered: generic motion helpers can bear a library-related title without containing its renderer. Trace source imports and actual mounting in the running UI; a package or face generator without mounted consumers does not satisfy reuse.
- Components often live only on unmerged WIP branches, not the checked-out one. Search every ref: `git log --all --name-only --format= | sort -u | rg -i '(graph|tree|topolog|orb|glyph|fleet|ladder)[^/]*\.(jsx|tsx|js)$'`, then `git log --all -1 -- <file>` and `git branch -a --contains <sha>` to pick the branch; check it out in a detached worktree under `/mnt/zer0models/worktrees/`.
- To let the owner verify candidates, build a gallery page in that worktree that imports the components UNCHANGED and feeds them real data (e.g. a read-only snapshot of Hermes sessions, subagents via `parent_session_id`, repos touched by tool-call paths with time decay, and `git worktree list`). Label anything you invented as "new, for discussion" so it is not mistaken for the original.
- Components that fetch from a backend (orchestrator `/v1/pulse`, `/__zeros/api/*`) show empty states without it; feed props directly instead of starting the backend.
- When file watches are exhausted (vite dev dies with ENOSPC on `watch`), add the page as a rollup input, `vite build`, and serve `dist/` with `python3 -m http.server <port> --bind <tailnet-ip>`. Run builds as tracked background jobs.
- Screenshot heavy animated pages with headless chromium (`chromium --headless=new --hide-scrollbars --window-size=1100,4200 --virtual-time-budget=8000 --screenshot=out.png <url>`) when the browser tool's capture times out; open the URL on the owner's desktop with `xdg-open` and give the tailnet URL for the phone.
- After the owner confirms, extract into a shared library that consumes the design language as data (e.g. AODL `encodings/visual.json` and `topology-graphs.json`) rather than copying constants; keep the meaning of every visual channel.

## Delivery

Report the working preview, recovered style lineage, tested interactions and remaining separation. Never present a historical preview as live visibility. Keep assets and receipts in canonical project artifact stores.
