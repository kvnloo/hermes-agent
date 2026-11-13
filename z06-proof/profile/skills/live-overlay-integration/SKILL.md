---
name: live-overlay-integration
description: Use when a running page must show new slices.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [overlay, live-server, visual, workers]
    related_skills: [webgpu-canvas-recovery]
---

# Live overlay integration

## When to Use

Use when the user wants a running local page to show new visual slices, including when they ask for several slices in parallel. The deliverable is the page, not modules on disk.

## Procedure

1. If they asked for the visual result, dispatch the slices and wire them in the same stretch. Do not end on a list of what is missing.
2. Give each worker disjoint files. If workers must not edit the server, the parent owns injection. A finished module that is not referenced by the HTML is not on the page.
3. Inject scripts in dependency order. A control API that later scripts call loads first. A client that imports a sibling module is `type="module"`, and the server must answer that relative import. A classic script that only assigns `window` stays a classic script.
4. Read the running process environment before restarting. Keep the archive database path and the asset root. A Node server caches imported modules, so a mapper or route change is invisible until that process is replaced.
5. After restart, require the HTML to contain the new tags, each script URL to return 200, and any DOM marker the slice owns to exist. An additive widen runs after a saved view restores, so a collapsed save cannot wipe the wider start and a wide save is not shrunk.
6. Map a worker only onto a city id already in the registry. Do not invent a city to place a checkout.
7. Paint a short settlement name on a known program city. Leave the host renderer's own settlement label alone. An unknown id stays unnamed. Put the task in the hover, not on the marker face. A truncated commit message is not a city or a unit.
8. Widen a reveal by adding hex keys and calling `animate`. Do not call `onResize` or `setSize` from a boot timer. That assigns `canvas.width` and blanks a Wayland WebGPU surface about a second after a good first frame.

## Pitfalls

- Do not treat a worker's "files written, tests passed" summary as the page. Confirm the served HTML and a live DOM read. A source match for a function name is not the reloaded view.
- Do not claim the canvas from a browser that cannot create the renderer. Report the DOM layer you actually saw.
- Do not hide the minimap or collapse the reveal to make a marker easier to see. Unhide an existing control; do not add a second one.
- Do not stop at a status of what is missing when the user asked to see the page. Wire the slice into the server they reload, then say what that reload shows.
- Wait for the FX host group and placed cities, not merely a nonempty grid map, before testing an injected Kingdom layer. Automatic realm expansion can clear cells while its terrain solver is still running; collect the host readiness fields and console on timeout before retrying an owned headless browser.
- Install a browser's fake clock before scheduling the timer under test. Installing it after a return card opens leaves its native dismissal timer outside clock control and produces a false failure.
- Observe the host HUD's element sizes when placing additive drawers. A bottom event strip can wrap independently of window resize, so recompute safe bounds with ResizeObserver and verify rectangles at a narrower viewport.
- Verify a persisted overlay with an actual reload and exact entry-key comparison. For deterministic injected-state tests, route the reloaded state endpoint to that same explicit fixture so real polling cannot masquerade as persistence corruption.
- Do not invent a settlement, quest, or worker to fill a gap. Name only cities that already exist.
- For Three.js world layers, follow [world-effects verification](references/world-effects-validation.md): geometry counts alone do not prove visibility, and procedural maps require placement-aware fixtures.
