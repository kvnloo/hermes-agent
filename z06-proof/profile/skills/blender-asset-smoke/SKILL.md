---
name: blender-asset-smoke
description: Use when testing procedural Blender asset modules.
---
# Procedural Blender asset smoke

## When to use
Use for side-effect-free, root-parented asset builders and CPU-only verification. This does not replace rendered visual review.

## Procedure
1. Write the contract smoke before the asset. Import via importlib and assert import does not add objects.
2. Build geometry in root-local coordinates using data API meshes; place only the root at the supplied origin. Return the root and complete object list.
3. Preserve existing objects, scene camera, and world. Do not clear the scene or set renderer state in an asset module.
4. Run with `terminal(command='blender --background --factory-startup --python-exit-code 1 --python <smoke.py>')`. Do not render or initialize GPU when smoke-only is requested.
5. Call `view_layer.update()`, obtain the dependency graph, and compute world-space min/max from each evaluated object's bound_box so Solidify and other modifiers are included.
6. Validate topology with `mesh.validate()` and fail if Blender corrected it. Assert expected anatomical counts, scale, grounding, root parenting, and repeated builds at nonzero origin.
7. Report base mesh vertices/polygons separately from evaluated bounds. Write measurements to JSON and document limitations.

## Pitfalls
- An outward/side leaf coordinate basis can invert the normal: test area-weighted polygon normal direction on the resulting geometry, then reverse face winding where required.
- For closed procedural tubes, assert that each undirected edge has two opposite directed uses and that signed volume is positive; valid polygons alone cannot detect inward sides or cap/side winding disagreement.
- Rebase vertices to a nearby reference point before signed-volume accumulation for submillimetre veins; float32 mathutils cross products on metre-offset coordinates can cancel enough to report a negative volume for a correctly wound tube. Keep the positive-volume assertion rather than relaxing it.
- For full-perimeter flowing assets, test a connected closed analytic spill boundary separately from downstream azimuth coverage; intentional downstream gaps must not be mistaken for a missing perimeter sector.
- A missing bundled extension dependency may print a startup traceback even when the asset smoke passes. Report it separately; do not modify host Blender without authorization.
- For lightweight raw-mesh diagnostic plans, avoid requiring host Pillow in Blender's Python: use a stdlib RGB buffer, embedded bitmap labels and zlib/struct PNG writer. Exercise projection, depth ordering, labels, chunk CRCs and decoded pixels under Python `-B -S` without bpy, then run the real saved candidate only through the admitted headless runner. Preserve source hashes before/after and keep diagnostic success separate from visual approval.
- For millimetre-scale edits in a plan diagnostic, read numbered locator positions from the pinned saved vertex IDs and compare their world coordinates with the pinned edit receipt. Label symbols as occlusion-overriding, not-to-scale overlays; XY cannot establish vertical tuck depth, evaluated clearance or contact acceptance.
- Do not claim visual approval from mesh validity or successful headless execution.
- For a one-class geometry revision, build preserved and revised modules together and compare non-target meshes by vertex/topology signatures and local transforms; preserve random-number consumption so untouched fruit and branch geometry remains identical.
- Measure single-sided blade surface area as well as evaluated whole-asset bounds for foliage-width revisions; internal canopy coverage can increase substantially while tip-controlled outer bounds barely change.
- For material-only adjustments, copy materials and use OBJECT-linked slot overrides to preserve both original material graphs and shared mesh material arrays; test a non-target object sharing the same mesh, exact old/new slot mappings, original graph fingerprints and repeat-call no-op behavior.
- When evaluated legacy-curve bounds are inflated, measure evaluated to_mesh() vertices and always release them with to_mesh_clear(); report those geometric extents rather than accepting broad boxes as measured plant size.

## Camera/lighting adjustment smoke

- Reacquire each evaluated object immediately before `to_mesh()` rather than retaining evaluated RNA references across dependency-graph instance iteration and mesh conversion; otherwise later references can become stale even when the original object is valid.
- Inspect extremal objects before fitting a whole-scene camera: render-enabled offsite archives can dominate the AABB. Use an explicit measured subject root/collection, retain all-scene bounds and exclusion names in the receipt, and never silently substitute old contract dimensions.
- Fit orbit radius from the entire trajectory even for frame subsets so independent chunks keep a common target, radius and angular phase. Keep render chunks bounded, preserve Cycles data within each process, and release the process between higher-priority asset reviews.
- Distinguish planned projections from actual frame proof. Create completed receipts only after Blender finishes and the written image dimensions/hash verify; refuse MP4 proof from missing frames, repeated stills or incomplete trajectories.

When the assigned asset is a camera/lighting rig, substitute projection checks for mesh topology: project every conservative scene-AABB corner through each camera at the declared resolution and pixel aspect, assert finite NDC coordinates with a safe border, positive depth, and clip-plane clearance. Frame the waterfall bottom and house top together rather than aiming at an old garden closeup. Preserve original camera/world/light data and return explicit activation overrides; a copied world can share existing environment images without editing them. Keep original comparison aspect ratio and view settings in the receipt, and make old-light muting an explicit assembler decision to avoid doubled illumination. Test repeat application before activation and document whether rebuilding an active rig is supported.

## Saved-scene integrity and export fixtures
- Test visibility-only candidate saves with a translated hidden object. After reopening, hidden objects can expose a stale identity `matrix_world`; compare saved `matrix_basis` and `matrix_parent_inverse` through the parent chain instead of treating unevaluated world matrices as geometry drift. State that this does not establish evaluated constraint parity.
- Exercise a real beveled curve and a procedural material in GLB fixture smoke, not only cubes. Parse the actual GLB JSON/BIN chunks and compare expected mesh-node membership so export selection failures cannot pass as a valid header.
- Hash only protected raw data blocks once and fail at an explicit element cap rather than silently sampling. Allow creative plant replacement separately from protected house identity; verify unique plant roots and visible recursive geometry independently.

## Verification
Require a real success sentinel and exit code zero, grounded measured bounds, and a second successful build with independent objects. Leave camera/render review to the owning visual loop when delegated.
