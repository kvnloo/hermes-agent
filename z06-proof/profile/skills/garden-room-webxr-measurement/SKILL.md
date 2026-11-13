---
name: garden-room-webxr-measurement
description: Use when extending Garden Room AR measurement tools.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [webxr, threejs, android, measurement]
    related_skills: [threejs-real-gpu-receipts, company-os-visual-language]
---

# Garden Room AR measurement

## When to Use

Use for Garden Room camera tools, room calibration, dimension assignment, ruler fallbacks, and their injected XR tests.

- Keep changes inside `public/modules/ar*.js`, `ar.css`, and `routes/ar.py`; the host dynamically imports `init(GR)`. Discover the checkout and read the live GR API before editing.
- Use a separate transparent XR renderer while the host owns a normal requestAnimationFrame loop and cutaway camera. Require hit-test and dom-overlay. Request anchors, CPU depth, raw camera-access and plane-detection only as optional capabilities; never require plane detection on Android Chrome.
- For live scanning, copy XRWebGLBinding camera textures synchronously in the active XRFrame and encode/upload afterwards with the exact view pose and projection-derived intrinsics. Restore Three's previous render target AFTER renderer.resetState(); resetState unbinds framebuffers and clears its target cache, so GL framebuffer restoration alone is insufficient.
- End immersive AR before requesting getUserMedia fallback. Label DeviceOrientation-only video nonmetric: rotation alone cannot supply translation, triangulated room geometry, or layout corrections. Invalidate scan geometry on reference-space reset and hide stale/tracking-lost boxes.
- Keep live scans behind authenticated routes and a private mode-0600 Unix socket worker. Warm both detection and real gsplat CUDA forward/backward before announcing health; first-run JIT compilation can take minutes. Drop excess frames rather than queue them, and verify persisted stopped status/splat artifacts after stop.
- Treat detector boxes as uncertain semantic suggestions, not full 3D shapes. Show unknown depth explicitly, require Apply for plan changes, keep plant identities unsure without position-plus-appearance evidence, and label PlantCV output projected green area/colour proxies rather than total leaf area or a health diagnosis.
- Distinguish real image inference and Spark decoding from reconstruction quality. A valid sparse splat may only render disconnected blobs; inspect it with vision and never call that a coherent room. Keep COLMAP arbitrary-scale offline poses separate from metric XR evidence. Live scanner details and scripts live in docs/scan-live.md.
- Queue DOM placement requests and consume them inside the next active XRFrame. Anchor creation and depth reads must execute in the active frame, not an asynchronous button callback. Suppress beforexrselect on UI to prevent double placement.
- Fit two known floor corners with a rigid 2D rotation and translation, never scale sensor metres. Reject wrong-length or non-level correspondences. Bind saved calibration to the room polygon. Restore both persistent anchors and recompute the transform before reusing a saved alignment; a serialized transform is not localization.
- Hide live positions and footprints on tracking or anchor loss. Invalidate alignment on reference-space reset. Label any retained host-scene position as last tracked after XR ends.
- `GR.footprint(it)` returns an AABB object `{x0,x1,z0,z1}`, not point arrays. Plants use potD/potH/height; box plants use w/d/potH/height. Foliage height starts at the pot rim. Snap assignment to half an inch without claiming half-inch accuracy.
- Map photo taps through the actual object-fit content rectangle, not the full canvas element. Reset reference scale for each photo. Keep images local, label the mode a 2D estimate, and require coplanar reference and endpoints.
- Test pure geometry plus injected XRFrame/session contracts and real unsupported-camera UI in `node tests/ar.mjs`. Run `python tests/ar_api.py -v` with storage redirected to an owned TMPDIR. Intercept `/api/state` and calibration writes in browser tests. Inspect phone screenshots and distinguish injected XR screenshots from real passthrough evidence.
- Re-run `node tests/phone.mjs` before committing only owned files. If drag fails with offscreen projected coordinates, compare with AR stubbed out and check camera matrix freshness in the smoke test before changing product behavior. Do not edit another worker's smoke changes.
- For pasting a store link to place a real product (Amazon 3D package extraction, dimension proxies, staggered stands, HTTPS test server, the no-private-remote rule), read `references/retail-product-models.md`.
