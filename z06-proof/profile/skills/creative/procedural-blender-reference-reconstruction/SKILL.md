---
name: procedural-blender-reference-reconstruction
description: "Use when scripting Blender reference reconstructions."
version: 1.0.0
author: zer0 Chief of Staff
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [blender, procedural-modeling, reference-reconstruction, product-visualization, verification]
---

# Procedural Blender Reference Reconstruction

## When to use

Use for reconstructing a product, prop, hard-surface object, or small scene from images when the requested deliverable is an editable Blender artifact, especially when the user asks to use scripts.

## Always-on rules

- Treat **“use scripts” as an implementation constraint**, not a suggestion: generate geometry, materials, cameras, lights, output settings, renders, and validation through rerunnable Blender Python. Do not substitute manual Blender/MCP editing.
- Preserve the source images beside the project and inspect every supplied view before modeling; rear, side, and macro views often reveal features absent from the hero angle.
- Keep observed facts separate from inferred dimensions, hidden geometry, labels, and materials. Never imply manufacturer accuracy without measurements.
- Deliver an editable `.blend`, the generator, the validator, representative renders, and a short README with exact reproduction commands.
- A successful Blender process is not proof of a successful visual. Reopen the saved file in a fresh process, validate structure and output, then inspect the actual rendered pixels.
- Do not claim exact identity when pictograms, fonts, microtexture, optical falloff, or concealed construction were approximated; list residual mismatches succinctly.

## Procedure

### Saved-mesh anatomy and comparison safeguards

- Diagnose eye/aperture visibility with neutral shading, actual material-slot inventory, surface normals, and first-hit ray tests before changing anatomy; a clay override can hide a healthy insert, and an empty material list cannot be presented as recovered source shading.
- Deform a body aperture and its separate insert with the same bounded map, then snap documented shared rim correspondences and verify both vertex gaps and matching boundary edges; unchanged eye objects are not a valid constraint when surrounding anatomy changes.
- Update the Blender view layer before serializing newly positioned camera matrices; otherwise a manifest can silently freeze stale identity transforms although the subsequent render updates correctly.
- Compare mesh intersections with fixed baseline triangulation for both body and inserts; geometry-dependent quad tessellation can change triangle identities and produce false new-collision reports.
- Distinguish exact interface contacts from noninterface intersections, and report pre-existing intersections rather than claiming a fully clean mesh from a zero-new-defects result.
- Reject localized anatomy fields that create cheek shelves or brow scallops; use coordinated cross-section changes with continuous support before escalating another tiny surface patch.


### 1. Acquire and classify the references

1. Download original-resolution media into `references/` without recompression.
2. Record provenance and the supplied caption in the README.
3. Inspect all views and inventory:
   - silhouette and proportions;
   - repeated components and control spacing;
   - bevel and panel hierarchy;
   - materials and roughness;
   - camera perspective, crop, focus, and lighting;
   - labels, ports, seams, fasteners, and hidden/inferred areas.
4. Decide which visual dimensions are authoritative and which are estimates.

### 2. Establish a self-contained output directory

Use one task directory containing:

```text
asset-name/
  build_asset.py
  validate_asset.py
  asset-name.blend
  references/
  renders/
  README.md
  build_manifest.json
  validation_report.json
```

Do not modify a neighboring asset merely because its materials or lighting are useful. Copy or reimplement reusable patterns inside the new directory unless the repository already exposes a stable shared module.

### 3. Build procedurally

- Write one deterministic generator that starts from a clean scene.
- Name collections, geometry, materials, cameras, and lights by role.
- Use reusable helpers for rounded boxes, repeated buttons, labels, booleans, knurling, and look-at camera setup.
- Prefer real editable geometry for silhouette-critical detail. Shader-only or texture-only detail is acceptable only when it survives the target shot and remains honest in the README.
- Set units and authored dimensions explicitly.
- Pack nonstandard fonts or other required resources into the `.blend` when portability matters.
- Use fixed seeds and explicit render settings. Expose practical command-line switches such as resolution, samples, engine, selected views, and build-only mode.

Typical run:

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python asset-name/build_asset.py -- \
  --samples 96 --resolution 1200
```

### 4. Match the evidence views

Create cameras corresponding to the supplied views rather than one generic beauty camera. For each view, match in this order:

1. object extent and silhouette;
2. camera elevation and azimuth;
3. focal length/perspective;
4. crop and negative space;
5. key/fill/rim placement;
6. focus distance and depth of field;
7. microtexture and labels.

Do not spend time perfecting hidden topology before the evidence cameras read correctly.

### 5. Validate in a fresh Blender process

Run the validator against the saved artifact, not the in-memory scene:

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python asset-name/validate_asset.py
```

Follow `references/verification-contract.md`. Fail closed when the file cannot reopen, required named objects/materials/cameras are absent, geometry dimensions are invalid, or required renders are missing/blank.

### Library transplantation safeguards

Pass a copy of requested names to `bpy.data.libraries.load`: the destination object list is replaced with loaded Object values. Unlinked loaded objects may have unevaluated identity `matrix_world`; do not treat that as the donor's saved transform. Preserve the recipient transform and verify the transplanted mesh's world coordinates against a previously exported donor array before saving.

### Busy headed audit safeguards

- Treat MCP client timeouts as transport failures, not cancellation: a synchronous Blender main-thread handler may keep executing after the caller disconnects. Before another RPC, inspect completion artifacts, the existing process's log, main-thread CPU deltas, and open-file/read-counter activity without attaching a debugger or signaling the process. Never queue a replacement audit or writer merely because the first caller timed out.
- Materialize NPZ arrays once before per-face loops (`with np.load(path) as archive: parents = archive['parents']`); repeated lazy archive indexing decompresses the entire member on every iteration. Export bounded scene data from headed Blender and run expensive numerical comparisons in a separate ordinary Python process—not a second Blender. Benchmark on the actual data before dispatch, compare cached scalar and vectorized results, and include an injected-defect regression so speed does not silently weaken validation.
- State the off-process audit's coverage explicitly: absent replacement/split topology or an approximate area formula cannot certify exact Blender geometry. Keep exact Blender-dependent checks bounded and separate from exported-data checks.
- A disk fix cannot alter an already executing script. While an old job progresses, use a passive completion watcher with an actual completion notification and bounded expiry, and fix/test the replacement audit off-process concurrently. Do not merely wait and describe that as a repair; do not interrupt the user's live application without authorization or queue competing RPCs.
- Distinguish receipt-file creation from completed scene restoration: if a script writes JSON before reopening its candidate, require completion/reopen evidence and at most one bounded read-only availability probe before releasing the next writer. Zero TCP queues do not prove an empty application command queue.

### Local BMesh repair safeguards

- When continuing an explicitly authorized existing headed Blender, save a uniquely named `save_as_mainfile(copy=True)` recovery and verify it exists before mode changes or loading a baseline. Reopen saved candidates in that same process with `load_ui=False` when a second Blender is forbidden; do not steal desktop focus.
- Track original BMVert references separately across bisect: new vertices may inherit integer custom-data layers, so inherited IDs are not proof of unchanged source vertices.
- Require cut-boundary cycle checks and before/after boundary-edge counts. A nonempty `holes_fill` result does not prove closure; reject any unexpected new boundary edges.
- Judge digit count by visible terminal anatomy, not the number of long tips: a truncated extra lobe with a residual cleft still fails a three-claw repair. Retain the baseline instead of polishing the stump with smoothing.
- For full bounded foot reconstruction, separate the exact retained ankle section from the new anatomical surface. A jagged all-vertices-below face boundary can create pleated lofts; use a verified single planar boundary cycle and stitch the new connected surface without moving retained vertices.
- Model actual digit branches and their attachment volumes, not radial silhouette spikes on a skirt. If using an analytic implicit reconstruction, constrain ankle-to-metatarsal cross-sections to a continuous monotone transition; independently weighted profiles can create non-anatomical stacked shelves.
- Validate saved reconstruction with an independent oriented coordinate-polygon hash outside the permitted region, component counts, local nonadjacent triangle intersections, and baseline-relative degeneracy counts. Numerically weld duplicate isosurface vertices only within newly generated geometry; do not smooth retained anatomy to conceal a rejected digit.
- Keep paired cameras identical and label any ankle-clipped overhead render as supplementary cutaway evidence. Preserve rejected structural hypotheses and their scripts, but distinguish a limited anatomy-review candidate from overall creature acceptance.

### 6. Perform visual QA

Inspect every final view for subject visibility, scale, camera composition, clipping, impossible intersections, lighting, material response, label legibility, and correspondence to its specific reference. Use one contact sheet for the first pass, then zoom into any suspicious frame.

Iterate the generator—not the saved `.blend`—so the correction remains reproducible.

### 7. Deliver and version

- Rerun generator and validator from scratch before delivery.
- Commit only the new asset directory when the surrounding experiment tree contains unrelated untracked work.
- If the repository lacks an author identity, set a repository-local automation identity rather than changing global Git configuration.
- Report artifact path, reproduction commands, structural validation, render dimensions, visual verdict, residual mismatches, and commit hash.

## Derived launch-video workflow

When the user asks for a short launch video after approving the renders, treat the verified render set as the canonical media input. Stage copies inside the video project, create cinematic crop/push motion without inventing product capabilities, run framework checks, inspect deterministic timestamps, render the MP4, verify it with `ffprobe`, and inspect an evenly sampled contact sheet before delivery.
