---
name: blender-owned-asset
description: "Use when building isolated Blender asset modules."
---

# Owned Blender asset modules

- Keep import inert; create objects and materials only inside `build(origin=(0,0,0), name='asset')`.
- Return `{'root': root, 'objects': objects}` including the root. Parent every other object directly to it, and set root.location to origin. Use local metre coordinates with ground contact at Z=0.
- Prefer bpy.data constructors to selection-sensitive operators, and a local seeded random generator to global random state.
- Write a headless integration check before implementation. Run `blender --factory-startup -b -Y --python-exit-code 1 --python test_path.py` so script failures propagate.
- Assert import creates no objects or materials; compare the exact post-build object-set delta with the returned list and check every parent.
- Snapshot camera, world, render engine, and output dimensions and assert they remain unchanged. Never reset the scene in a composable factory.
- Measure evaluated geometry via `evaluated_get(depsgraph).to_mesh()` so curve bevels and modifiers count. Transform vertices by matrix_world, aggregate bounds and topology, then call `to_mesh_clear()`.
- Exercise a second build with a distinct name and nonzero origin; assert disjoint ownership and matching counts.
- Clamp fractional-power curve bases at zero near contact offsets; slightly negative values otherwise produce complex numbers rejected by mathutils.
- Distinguish environmental add-on startup warnings from asset failures using script assertions and the process exit code; do not change shared installations solely to silence unrelated warnings.
- If rendering is delegated or forbidden, perform CPU-only geometry checks and explicitly leave visual critique pending.
- For transform-only scene adjustments, resolve stable IDs on authored roots rather than assuming children carry generation metadata; preflight every placement before mutation, measure evaluated descendant meshes, preserve child-local transforms, and verify repeat application plus the source-file hash without saving the baseline.
- For surgical saved-scene reconciliation, freeze exact object ownership and source digests, inspect donor/control/baseline coordinate anchors read-only before transplanting, and transfer only selected raw meshes or transforms. Never copy a whole host wall when it contains unrelated opening/material edits; stage a source-authored local repair separately and disclose unwelded contact limits. Keep image-space trace proposals distinct from saved world-space meshes, preserve existing bevel/normal stacks explicitly, and require before/after plus save/reopen signatures and a new-output-only path gate.
- For an exact shared terrain boundary, preserve its top ring verbatim and cap deeper-ring drift by available inboard clearance; shallow offsets can cross the envelope even when each ring radius shrinks. Test every boundary vertex and all interior vertices against the shared footprint.
- For CPU-cheap surface clouds, extract one blended ellipsoid field into a static mesh instead of overlapping puff objects or volume shaders. Check manifold edges, consistent winding, positive signed volume, and evaluated bounds; surface-cloud shading still requires parent-rendered visual review.
- When a surface cloud reads as wax, separate boundary-opacity, material-response and shape ablations before adding geometry or volume. Keep an opaque support core and test both bright and dark sky views; grazing transparency on a closed shell can expose backfaces or create halos, so analytic opacity tests are not rendered-alpha proof.
- For delegated presentation experiments, freeze recorded camera matrices instead of recomputing framing from changed bounds. Pair pure-stdlib math checks with explicitly unexecuted parent Blender socket/rollback tickets when workers are forbidden to launch Blender.
- Triangulate known-convex half-plane-clipped polygons with an indexed fan; avoid exact Vector-equality lookups into tessellator outputs, which can fail when returned coordinates differ from input coordinates.
- Measure contact against evaluated loop triangles rather than fitting one plane to each bevel polygon; rounded corner quads can be nonplanar, and a planar-top test can miss a separate blade crossing the slab's side bevel. Preserve the failed preflight evidence instead of relaxing a convexity threshold.
- Distinguish surface crossings from fully buried volume overlap when adjusting existing grass coordinates; pin exact affected vertex IDs, preserve every other coordinate and all topology, and never describe a surface-clear result as zero volumetric intersection.
- Establish whether wall-ray origins lie inside retained solids before treating tangential travel as an opening gap; compare bounded through-wall rays for the retained wall alone and the separate infill, and disclose unexecuted continuous-coverage or coplanar-face checks.
- Export terrain exclusion polygons alongside shallow water geometry so a separately owned lawn module can avoid covering it without either builder modifying the other's data.
