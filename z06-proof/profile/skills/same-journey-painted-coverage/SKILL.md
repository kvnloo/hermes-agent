---
name: same-journey-painted-coverage
description: Use when canvas bounds disagree with visible coverage.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [browser, canvas, measurement, performance]
---

# Same-journey painted coverage

## When to Use

Use when a canvas geometry metric reports holes but a layered renderer appears covered, or when two coverage harnesses disagree.

## Procedure

1. Preserve the legacy sampler, assertions and input journey. Add a versioned sensor to the same queued measurement task so both results refer to identical input and state; a different tape cannot resolve a sensor disagreement.
2. Retain actual painted source rectangles, layer visibility and opacity, transformed image bounds and the frame bounds. Compute clipped rectangle-union coverage offline, not from canvas bounding boxes or a sparse grid that can miss interior holes. Keep full-frame and visible-viewport results distinct.
3. Treat a painted lower-resolution floor as coverage, not as HQ fidelity. Preserve resolution, HQ-after-lift, upload-tail and motion metrics separately. Do not stretch the detail canvas to satisfy a rectangle test.
4. Validate representative flagged frames with a copied composite of real canvas pixels. Never read back the app canvas directly: it can change raster behavior. Keep readback diagnostics separate from timing runs.
5. Inject an explicitly synthetic missing-layer control and require the sensor to detect real transparent pixels. Retain PNGs and raw observations. A natural flag with fully opaque lower layers is a false positive for plate exposure, not proof that every visual-quality defect is fixed.
6. Do not invent a production renderer fix when the same-journey measurement and pixel readback reproduce no hole. Commit the measurement repair on its owning feature lane, keep held renderer experiments isolated, and report the remaining physical-device or sharpness issue plainly.
7. Generate verifier adapters in caller-supplied scratch directories and refuse to overwrite existing evidence. Pin browser/ANGLE/network settings across arms. Instrumented timing must not be causally compared with historical uninstrumented timing.
