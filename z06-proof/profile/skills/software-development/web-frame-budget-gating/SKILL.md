---
name: web-frame-budget-gating
description: Use when gating web changes against a frame budget.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [performance, web, 120hz, traces, gates]
    related_skills: [native-feel-web-performance-research, light-browser-routing, deferred-layout-gate-diagnosis]
---

# Web frame-budget gating

## When to Use

Use when a scroll, scrub, pan/pinch, animation or cold-start change must be admitted against a high-refresh budget ("native app feel at 120 Hz") in headless browsers, or when repeated repair passes on a perf gate are not converging.

## Procedure

1. **Measure work, not cadence.** Trace the scripted interaction and sum main-thread work per frame (rAF callbacks, style, layout, pre-paint, paint, layerize, commit, main-thread decode). Gate example for 120 Hz: work p95 <= 4.0 ms, max <= 8.3 ms, forced layouts 0, LoAF 0, mobile profile at 4x CPU throttle. Report rAF cadence as information only: on a shared or loaded host it swings 2x with no code change and measures the host, not the page. Recipe: [frame-work harness](references/frame-work-harness.md).
2. **Validate the harness first.** A deliberately bad variant (forced layout every frame) must fail every repeat; the baseline must repeat tightly (declared IQR limit); run >= 10 interleaved A/B repeats, record host load per run, keep before/after on the same browser binary and GPU path (record the GL renderer). A gate that has not passed these checks cannot admit or reject anything.
3. **Check the sensor before fixing the defect.** For coverage/quality checks (tiles reaching the edge, gaps, stale detail), compare the sensor with actually painted pixels on the same journey plus a missing-layer control. A legacy sensor can report hundreds of gaps where the painted output has none; fix the measurement, not the renderer.
4. **Attribute, then fix in this order.** Forced layouts to their JS stacks (reads after writes in scroll/rAF/ResizeObserver code; compute visible windows from one scrollTop read). If paint/layerize still dominate, move dense animated collections to one canvas with a sprite atlas (time as a shader uniform, a few DOM image slots, native text, an accessible list). Then cold start, then tails (single rAF scheduler, preallocated arrays, pre-warmed shaders, capped swaps per frame).
5. **Keep locked designs locked.** When the owner locked the look, change only rendering internals and prove it with identical-state before/after screenshots (zero changed pixels outside declared raster regions).
6. **One concern per branch, merge through its channel.** Each improvement lands on the branch that owns the concern with before/after numbers from the same harness; the integration branch merges it after the per-merge verification.
7. **Stop non-converging passes.** After two repair passes that do not converge, present the owner a choice (merge on the met median budget with the tail tracked as open, or hold) rather than another near-identical pass. Never loosen a threshold to admit a change; fixing an invalid method is allowed and must be stated.
8. **Label emulation.** Headless numbers are EMULATION; final 120 Hz acceptance needs a real phone (a deploy or LAN preview the owner can open).

## Pitfalls

- Zero forced layouts is not sufficient: hundreds of animated DOM thumbnails stay bound by layerize/paint.
- A lossless sprite atlas can wreck cold start (tens of MB, seconds of blocking time): use lossy atlas pages sized to need, load after first paint, decode in a worker, upload in slices across frames.
- Test-harness observers can create the long tasks they report; defer harness serialization off the measured window.
- A load-average or free-VRAM admission gate never opens on a shared host; queue behind a lock instead of polling thresholds.
- "Input -> next rAF" measured from a loop that awaits rAF between inputs is one vsync (16.7 ms at 60 Hz) by construction; a `< 16 ms` gate on it can never pass. When several runs sit at exactly the frame interval, gate "presented in the next frame" (< 1.5x the measured median frame interval) plus main-thread work < frame budget, and state the method fix in the perf doc.
- A worker round trip on the edit -> paint path adds queueing delay (tens of ms on a busy host) even when handler CPU is sub-ms. Apply small pure commands synchronously on the main thread and paint from that patch; keep workers for off-path work (diffing, migration, serialization) and test that worker and main documents stay identical over a seeded random command sequence.
- Perf suites must be hermetic (generated fixtures of the same size, never a maintainer's real data); prove with `HOME=$(mktemp -d)`.
