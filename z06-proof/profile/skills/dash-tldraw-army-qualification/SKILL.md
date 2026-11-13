---
name: dash-tldraw-army-qualification
description: Use when integrating tldraw in Dash annotation.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [dash, tldraw, annotation, expo-dom, tester-army]
---

# Dash tldraw annotation qualification

## When to Use

Use for Dash's Expo DOM tldraw integration, offline asset network gates, stroke-contract adapters, or the matching tester-army journeys.

## Boundaries

- Read the task's release-base requirements, `AGENTS.md`, `TESTING.md` and the repo's verify-dash skill first. Run only committed `e2e/mbp-army` Playwright journeys for behavioral proof; typecheck/lint are hygiene, not acceptance.
- Keep native Skia as the default until an explicitly authorized device gate passes. Do not use the owner's phones, live bridge or served worktrees for a browser-only slice.
- Do not add a license key or modify license checks/watermark behavior for localhost development. The default mobile unlicensed watermark is an 8px-wide edge affordance with hidden button text; do not mistake it for accidental clipping and override it.

## SDK and adapter

- Pin the exact SDK version; for 5.5.2, use `GeoShapeGeoStyle`, not `DefaultGeoStyle`.
- Capture timed/pressure-bearing pointer samples inside the DOM boundary: 5.5.2 draw segments contain compressed base64 `path`, not timestamped point arrays.
- Convert screen samples to page coordinates with `editor.screenToPage`, save them shape-locally, then apply the shape's page transform before dividing by the capture dimensions. Camera zoom must never be normalized as if it were capture-space geometry.
- Preserve unchanged Stroke object identity when syncing a DOM document: Dash's `finishSend` excludes its immutable submitted snapshot by reference. On confirmation, reconcile only submitted shapes, leaving newer committed or still-live ink intact; do not blindly clear the DOM or retain stale submitted marks. Gate confirmation reconciliation on the status transition, not every render while status remains `sent`.
- Preserve stable IDs through undo/redo. Suppress document-listener bridge callbacks during live drawing; publish completed strokes and deletion edits, including erasure with no newly created shape.
- Expo DOM imperative factories accept JSON-valued arguments and return void. Derive the argument type from `Parameters<DOMImperativeFactory[string]>`; `JSONValue` is not exported from `expo/dom`. Parse argument objects at the boundary and use callback actions for export completion.
- Preserve the original opening timestamp while waiting for editor mount; otherwise a cold editor arriving late falsely reports a one-frame warm-open duration.

## Offline assets

- Override fonts, icons, translations **and embedIcons**. `hideUi` does not prevent tldraw from preloading all embed logos.
- Bundle version-matched assets from the published `@tldraw/assets` package and retain its license. Data URLs work in Expo DOM on file origins without an HTTP asset host.
- Monitor requests from initial navigation, not just annotation entry. Dash's eager ShimmerText bootstrap loads CanvasKit even when annotation defaults to tldraw, so fixing only tldraw CDN URLs is insufficient. Self-host the lockfile-pinned CanvasKit WASM too, without disabling or mocking requests.

## Army evidence

- Enter windowed-chat annotation through Options -> Annotate. The `Annotate this screen` shortcut is conditional on a non-windowed options panel and is not a universal entry.
- Compare engines in fresh browser contexts, each following real pairing. Reusing an already-paired profile while calling the pairing fixture again waits forever for a Pair screen that correctly no longer appears. Never clear/seed stores to compensate.
- Let the army's Playwright configuration own tracing for `browser.newContext()` too; manually calling `context.tracing.start()` fails with 'Tracing has been already started'. Capture explicit per-engine screenshots and let normal context cleanup finalize traces.
- Freeze Date with Playwright's fixed-time clock while leaving rAF/performance timers running for deterministic sample timestamps. Capture the real uploaded JSON and actual WebSocket marker text, not an imported serializer called from the test runner.
- Canonicalize only the generated navigation screen UUID when comparing otherwise identical sessions. Keep the rest of the serialized JSON byte-equal, and record both originals.
- Exercise camera zoom through real wheel/pinch input; use rendered DOM transforms for independent coordinate expectations, not an editor global or a test-only camera setter.
- Freeze the same army files on an unchanged-base branch and the implementation branch. Check their diff is empty before citing before/after evidence. Invalid selectors are harness errors, not evidence that the feature failed on base.
- Download raw receipts and inspect screenshots. A passing annotation subtest does not make an O15 suite green when another release-base journey fails.

## Remote runner pitfalls

- Fleet source snapshots omit Git metadata. `scripts/army.sh` requires a real checkout; do not fabricate a Git identity or receipt to run it. Use an exact-head checkout on the runner or the repository's CI job.
- If a worker clone fails to load CA trust anchors, do not disable TLS verification. Report the worker limitation and use a properly provisioned runner/CI.
