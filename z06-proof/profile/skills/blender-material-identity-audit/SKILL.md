---
name: blender-material-identity-audit
description: Use when auditing material identity across Blender themes.
---

# Cross-theme robot/material identity

Treat geometry, albedo, printed graphics, roughness/metallic/normal, emission,
lighting and compositing as separate evidence channels. Same mesh/pose is not
proof of same materials; a blue beauty image alone is not proof of blue albedo.

## Workflow

1. Read the real render entry point, imports/shims and source-scene selection.
   Distinguish current code from old proof images and baked donor scenes. Freeze
   a Git revision in an isolated worktree when another worker owns the scene.
   Verify stored frame hashes and Git provenance separately from current shader
   state. Renderers may reuse an existing image/receipt pair without checking
   source changes. Record optional flags that can mutate albedo after the shared
   theme setup; a default-path pass does not cover opt-in experiments.
2. Check reference provenance. A huge image may be an old render, not measured
   material truth. Inspect stable references plus native-resolution overlapping
   crops. Record source pixel coordinates and hashes; never use downscaled
   thumbnails to judge decal fidelity. Disable Pillow's pixel guard only for a
   trusted local image after validating its expected dimensions.
3. In headless Blender, reload a fresh donor for each variant. Fingerprint the
   actual reachable Principled input graphs, including image bytes/colorspaces,
   ramps, UV/mapping, filtering and numeric inputs. Compare material-slot
   assignments, geometry/UV hashes and transforms separately. Inspect actual
   output connectivity before concluding graphs describe the rendered surface.
   When regenerated BMesh primitives differ in raw face/loop enumeration, compare
   canonical oriented faces with per-corner UVs, material slots and smooth flags
   before declaring shape drift. Preserve winding (cyclic rotation is equivalent;
   reversal is not), vertex-coordinate checks and the raw failed diagnostic. Do
   not ignore real UV or geometry changes merely to make a guard pass.
4. Render three diagnostics: actual beauty; robot-only base color connected to
   unit emission with exposure zero/Standard transform; original BSDFs under
   identical neutral lighting. Keep camera, geometry, UVs, seed and settings fixed.
   Never save altered diagnostic shaders back into source scenes.
5. Compare decoded pixels, not PNG hashes alone. Preserve raw maximum/mean deltas,
   alpha agreement and changed-pixel counts. If neutral GPU output differs at
   the least-significant level, rerender the exact same scene as a repeatability
   control before choosing any tolerance. Do not silently change a failed exact
   equality assertion into a broad visual pass.
6. Include a negative control using an actual differing donor or a deliberate
   test-only material change. A useful method must detect real albedo replacement.
7. For image-feature measurements, version the mask, fit domain, connectivity,
   boundary policy, pixel/physical units, density tiles and spectral bands together.
   Do not splice an older unmasked CLI into later masked receipts. Establish pure
   math with synthetic fixtures, then measure immutable real crops. For pre-print
   emission versus printed beauty, reuse one shared exclusion mask for both
   display and scene-linear data; separate printed geometry may remain visible.
   Preserve an exact-repeat failure and raw float deltas rather than silently
   broadening equality. A reporting test can pass while an explicitly requested
   bit-exact linear gate correctly fails; label these outcomes separately.
8. Modify materials only when the current source demonstrates drift. If intrinsic
   channels already match, report that result; do not compensate intentional
   lighting with per-theme repainting or manufacture a corrective code change.
9. Report separate limits: cross-theme identity, fidelity to supplied lit artwork,
   source texture resolution, alternate-view UV coverage and beauty readability.
   A 200MP render does not create detail absent from a small decal/source atlas.

## CPU-only critique and edit preparation

- When rendering is forbidden, establish the image baseline from exact shipped bytes, inspect matched full-frame/crop sheets, and probe the saved scene plus its final overrides in memory. Label proposed values as unrendered hypotheses; node read-back is not visual acceptance or shipped-recipe reproduction.
- Preserve ordered node input records with index and identifier as well as a first-match name lookup. Blender nodes can repeat names such as `Value`, `Shader`, or `To Min`; a name-keyed dict alone silently overwrites scalar sockets with later sockets and can misreport the effective graph.
- Validate an edits file using the actual consumer, reject every failed key, and read back each requested socket/property. Separately compare geometry hashes, object transforms, camera, material bindings and untouched material graphs; linked defaults are not the effective input value.
- For a system Blender that loads the wrong Python standard library from the agent environment, run a bounded probe with `--python-exit-code 1`, clear Python/library overrides and restrict PATH to the system binary directories. Clearing PYTHONHOME/PYTHONPATH alone may be insufficient when Python discovery follows PATH. Retain failed logs and require output receipts rather than trusting Blender's default exit status.
- Before reusing a theme-specific material hook, inspect its required nodes and texture/decal topology. A donor that expects an in-material decal mix cannot be applied unchanged to a scene whose decal is a separate object; unsupported JSON keys must not be presented as runnable edits.

## CPU-only scene/reference triage

- Separate saved-scene values from the effective recipe: load the preserved blend, apply each inherited layer once in memory, and inspect reachable node links before proposing a scalar edit. Connected roughness/albedo defaults are not effective values; procedural layer application may not be idempotent.
- Check each theme's occluders independently. Sample camera-visible receiver points and finite-area emitter points, name the actual first shadow blocker, then test a scoped geometric counterfactual. Do not copy another theme's sun/backdrop fix when the current theme has only area lights or a different camera-invisible blocker. Ray visibility is not rendered irradiance.
- Read the world Light Path graph before changing strength. Diffuse, glossy/transmission HDRI and camera-background branches can be different; reducing a reflection-only branch to fix a wall can make glass less readable.
- Compare donor graph links and texture mapping, not just shader numbers. A donor may restore artwork registration as well as saturation; an already matching emissive panel needs no generic diffuse-base fix.
- For CPU probes use background/factory startup, bounded threads, no render/save operators and `--python-exit-code` so Python failures cannot masquerade as success. If embedded Blender Python cannot import stdlib extension modules under an agent's PATH, retry the system binary with PATH=/usr/bin:/bin and unset PYTHONHOME/PYTHONPATH; preserve the failed log and record Blender-version compatibility warnings.
- Keep unsupported scene-linking operations out of active scene-match JSON keys. Prepare an explicit `apply(scene)` hook, state that underscore metadata is not executed, and read back its receiver/blocker collections plus geometry/camera guards before claiming configuration success.

## Projected eye/print registration audits

- Inspect live image paths and reachable Mapping inputs in every saved donor; a historical texture-round success does not prove that its atlas was ported to saved scenes or shipped plates. Separate retained identity/similarity registration from a missing later rim-color fix.
- Measure a lens-ring front separately from its cylinder wall. Brightness-threshold ellipses can include the wall under different theme lighting and falsely imply geometry changes; use the dominant front normal in a frozen G-buffer, verify its overlay, and compare geometry/UV/transform fingerprints across scenes.
- Treat a canonical material library as identity evidence, not cross-theme visual acceptance. A print can be straight and shader-identical yet wash out under saturated lighting; preserve unfavorable swapped A/B verdicts rather than promoting a one-theme improvement globally.
- Pass a copy of material-name lists into `bpy.data.libraries.load`: Blender replaces entries in `data_to.materials` with datablocks on exit. Retain the original strings separately when building the name-to-material lookup.

## Permanent eye-material repairs

- Inspect effective `object.material_slots` and each slot's `link`, not only `mesh.materials`. Photo3 ports can use OBJECT-linked CAL/POSTER overrides; replacing DATA materials passes a shallow check while rendering the old projected photo. Assign and reopen-check both effective slots and data bindings.
- Remove projected-photo shading from the complete eye assembly: lens/iris (`lens.stl`), outer ring/front/bore (`noenoeil.stl`), lens holder and recess (`face_part.stl`). Keep optical effects procedural in local/generated coordinates and verify no image/Artwork/validity nodes remain in those materials. Preserve geometry/UV/pose/camera independently.
- Keep already-approved cowl artwork outside the authorized rim scope. A broad clean rim replacement can eliminate blotches yet regress White/Dark reference color and wear, or strongly worsen Blue rim Lab while the eye becomes cleaner. Preserve the whole canonical Blue cowl when only the faceplate/eye needs repair. Use fresh swapped comparisons; retain failed broader repairs rather than treating all-theme cleanup as automatic improvement.
- Preserve already image-free native ring/lens graphs by private copying instead of retuning every theme to a generic early recipe. Verify copied graph equality and effective bindings after reopening. Calibrate a saturated Blue recess with an eroded geometry-owned mask: the early neutral charcoal recipe can become an inappropriately dark navy patch even though it removes all photo artifacts. Separate clean-eye votes from reference-fidelity votes in the report.
- Separate a hidden lens holder from the visible ivory ring when adding camera-only fill. Sharing the ring's bright emission with the holder can make a white stripe show through the separate faceplate aperture. Check this small hole in Blue/Night crops.

## Boundaries

- Use `blender --background`; keep the user's GUI/focus untouched.
- Do not rewrite adjacent stone, light, hosting or asset-publication work to make
  robot comparisons look better. Tests may configure diagnostic scenes in memory.
- Treat optional Night emission as additive only when the base material remains;
  report absent emission honestly instead of claiming an additive layer was tested.
- Dump node inputs by index and identifier as well as display name: Math and Map
  Range repeat display names, so a name-keyed JSON dump can silently discard the
  connected socket or effective scalar value. Before using scalar edit parsers,
  inspect whether they unlink inputs; reconnect a procedural emitter mask rather
  than replacing its strength with a constant solid glow.
- For an owner-approved glow lock, compare complete protected material graphs
  before/after a CPU-only candidate application. Relighting can still alter the
  composited glow appearance; exact shader equality is not pixel equivalence.
- When a target is known to be soft, normalize both target and candidate to the
  agreed comparison scale before masks/statistics/gates. Preserve sharp production
  textures. Label target-pixel discussion composites as unscored photomontages,
  never as render evidence or numerical improvement.
- Keep large references/renders outside Git and preserve evidence outside prunable
  scratch storage when delivering it. Leave source trees and branch ownership clear.
