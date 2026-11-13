---
name: blender-screen-free-engraving
description: Use when replacing low-res print screens on Blender reliefs.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [blender, engraving, fidelity, procedural]
    related_skills: [dream-loop, blender-inert-assets]
---
# Screen-free relief engraving coupons

## When to Use
Use when replacing a low-resolution screened portrait or print on an existing Blender relief while preserving camera, geometry and protected scene elements.

## Procedure
1. Read scoped owner locks and the selected source fixture. Inspect native cheek, shadow/neck, brow and hair crops before choosing a stroke representation. A reference described as crosshatch may actually contain stepped nested open paths; two infinite line families produce the wrong lattice.
2. Audit the output-reachable material graph, not only its base-color node. Portrait, weather, normal and displacement images can all retain a low-resolution screen. Preserve original datablocks and geometry while replacing only the authorized material slot in a saved copy.
3. Render a clean-tone control before adding ink. Geometry normal + local AO is a resolution-independent tone proxy, not irradiance or reconstructed anatomy. Disconnecting an old portrait also removes any anatomical shading it supplied; do not mistake screen removal for appearance success. Keep an explicit option for an intentionally band-limited descreened tone field rather than claiming a large resampled map contains new observations.
4. Separate continuous tone, metric UV/object-space engraving, physical recess/roughness, sparkle pigment and inherited grain. Preserve the existing compositor and grain where locked. Never use window coordinates for the print pattern or emission as a substitute for every bright scratch.
5. Test one morphology change at a time against the same tone and lighting. Closed stepped Truchet paths can form flower/cross wallpaper. Tone-selected nested bundles can collapse to small chevron glyphs in lit areas and braided bands in shadow. Programmed width/count modulation is not proof of the intended visible grammar. Stop after two failed trials and request an owner decision between distinct representations unless the owner has explicitly authorized a broader experimental portfolio; in that case log every family and recombination and continue within that new budget.
6. Render real native and final-density border crops with the unchanged camera. For a 25,820×38,730 contract, 11,584×17,376 is only an intermediate 201 MP family. Assert Blender accepted the full dimensions, then check actual output size and hash. Do not upscale a small render or label an enlarged reference native zoom truth.
7. Include clean-tone, previous-material and new-engraving controls at identical settings. Preserve early reviewed captures if later rerendered at another sample count; disclose reviewer/capture lineage. Read-only fresh reviewers must receive owner preferences verbatim and distinguish sharp new lines from weak underlying form.
8. Verify import-inert application, no effective raster consumers where required, idempotence, and save/reopen state. Snapshot geometry/UVs, camera, protected assignments, lights/world/compositor and original image pixels. A saved graph without image nodes can prove source removal but never whole-scene appearance fidelity.
9. Package TARGET | previous relief | previous print | clean control | variants with native, explicitly labelled 3× display crops and true deep-density pixels. Mark failed appearance plainly, retain the defect ledger, and do not promote on crispness alone.

## Execution cautions
- Use the actual installed Blender binary and the project's approved clean background environment. Honour shared GPU admission/lock rules; check free VRAM before rendering and retain CPU fallback.
- Condition coverage-versus-tone measurements on the independent portrait tone field, not on a diagnostic binary ink map's own luminance. The latter produces empty dark bins even when every path is continuous; it can mislead reviewers into inventing bundle gating. Preserve ambiguous historical packets, recompute the correct metric, and separate visual insufficiency from implementation facts.
- Give reviewers actual full-canvas dimensions, border coordinates, unchanged camera receipts and image hashes. A 512-pixel image alone cannot prove it was rendered at 1GP density.
- Release a shared GPU lock before a CPU fallback; do not monopolize GPU admission while rendering on CPU. Bound simultaneous dense-relief processes because scene auditing and decoded atlases can cause paging even when GPU memory is free.
- Do not name a helper `inspect.py`: it can shadow Python's standard-library module and break Pillow/logging imports outside Blender. Use `inspect_source.py`.
- Gradient/Laplacian metrics are grain/contrast-sensitive diagnostics, not fidelity acceptance thresholds without calibration. Border-local compositor results do not prove full-frame bloom/seam equivalence.

## Source-traced portfolios
See [source-tracing lessons](references/source-tracing.md) for skeleton topology, region-outline failure modes, cubic fitting, broad-tone separation and final-density raster allocation.

## Verification
Require real saved native/deep-density images, dimension/hash manifests, clean-tone appearance inspection, unchanged protected-state receipts, independent reviewer notes, and an explicit owner checkpoint. Report incomplete target microdetail truth or soft/faceted form as unresolved, not as an inferred pass.
