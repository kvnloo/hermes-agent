---
name: private-linearraw-candidate
description: Use when staging private LinearRaw material candidates.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [blender, materials, raw, privacy, provenance]
    related_skills: [local-image-evidence-provenance, blender-material-identity-audit, bounded-cooperative-job-admission]
---

# Private LinearRaw material candidates

## When to Use

Use for authorized local recovery or new extraction of private photographic material, especially when a guarded scene candidate must be deferred safely.

## Workflow

- Re-hash the original and search only authorized recovery roots before choosing a new extraction; a historical winner name is not a recovered crop or homography.
- Label newly authored controls NEW_EXTRACTION and keep physical scale, physical aspect and visual acceptance explicitly unresolved when unsupported.
- Keep private pixel bytes local. Do not send images, screenshots or pixel-encoded surrogates to vision/reranking services when upload is prohibited. Local scalar CV screening is not semantic or planarity approval; provide a private local review page and say what remains unverified.
- Try LibRaw first, then inspect TIFF photometric/compression/shape for unsupported LinearRaw DNGs. For a single JPEG-XL strip, decode with imagecodecs using numthreads=1 directly into an owned uint16 TIFF memmap, avoiding an extra full-frame float buffer.
- Respect DNG WhiteLevel and label inverse AsShotNeutral as a camera-WB approximation, not a camera-to-sRGB conversion. Generate previews by row-block area averaging; retain unchanged camera-linear values separately.
- Prefer a conservative native-resolution interior slice when no trustworthy geometric controls exist. Persist both corner conventions and exact translation homographies; do not invent projective correction or flatten a curved arch.
- Verify the crop against the exact sensor-native source slice, decoded color resolution/dtype, flat normal values and every output hash. Keep unblended repeat diagnostics local and make no seamless claim.
- Restrict any scene application to explicit already-planar polygon ownership. Append slots instead of rewriting shared material graphs; preserve original slots, curved surfaces, geometry, UVs and non-owned assignments. Save/reopen and test the preservation guard with a deliberate non-owned mutation before acceptance.
- Run Blender only through the required scheduler and inherited lock, preserving its reserve and floor. On deferral stop immediately with a ready queue; never poll or weaken admission.
- Preserve failed requests and logs. Confirm only the failed attempt's runner, child and process group are gone before scheduler reconciliation; stage corrected inputs as a new request identity.
- Diagnose Blender bootstrap failures before touching scene scripts. A system Blender can infer a standalone Python prefix from inherited PATH and lose standard extension modules even after PYTHONPATH is cleared. Compare its linked Python and system interpreter, then stage an isolated system PATH for the child; call the repair unverified until it actually executes.
- For a no-save planar-facing diagnostic, load the hash-pinned candidate read-only under the inherited scene lock, verify the exact owned polygons and saved material-node mapping, and raster only those authored triangles using the packed derivative pixels. Use a bounded stdlib PNG path when sanitized Blender lacks imaging packages; show outward-facing orthographic panels at shared scene scale and label UNAPPROVED / NEW_EXTRACTION. State that display-encoded base-color sampling is not a Blender shader/lighting render, independently decode the output locally, and preserve source hashes and prior successful checkpoints.
- Separate tested extraction integrity from optional Blender application. A ready queue is not a saved/reopened scene candidate, and an exit-zero runner is not artifact acceptance.
