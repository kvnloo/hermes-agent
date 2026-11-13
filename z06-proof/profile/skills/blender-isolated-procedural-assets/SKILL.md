---
name: blender-isolated-procedural-assets
description: "Use when making isolated procedural Blender assets."
---

# Isolated procedural Blender assets

- Keep module import inert; create bpy datablocks only inside `build(origin=(0,0,0), name='asset')` and return `{'root': root, 'objects': objects}`.
- Use direct bpy data APIs instead of operators to preserve selection, mode, active object, cameras and lights in the integrating scene.
- Parent every created object directly to an empty root, include the root in `objects`, and put the origin transform only on that root.
- Namespace objects, meshes, curves and materials with the caller's name. Use a local seeded random generator for repeatable variation without changing global randomness.
- Keep local ground at Z=0 and construct dimensions in metres; do not change the source scene's units or render settings.
- Write the integration smoke gate first and run it headlessly in a separate Blender process. Factory startup is allowed only in that isolated smoke invocation, never in the asset builder.
- Evaluate mesh and curve objects through the dependency graph and `to_mesh()` when measuring bounds/counts; object bounding boxes can miss modifier results. Call `to_mesh_clear()` afterward.
- Test inert import, all-object parenting, ground height, requested dimensions, a second translated instance and preservation of preexisting objects.
- Save exact Blender version, evaluated bounds and object/geometry counts in a JSON report. State explicitly when no visual rendering was performed.
- Treat startup addon errors separately from the asset result: an unrelated missing addon dependency may coexist with a successful smoke gate and exit code 0. Report it rather than modifying global Blender dependencies without authorization.
- Frame detail reviews from explicitly selected evaluated polygons and actual object references; fit their world-space vertices rather than a scene-wide AABB or name-based proxy, so archives and whole canopies cannot shrink the intended subject.
- Keep overview, whole-asset and single-surface proofs separate; record pixel extents and safe borders without calling a projected rectangle visible surface area, because occlusion and semantic selection still require pixel review.
- Pin evaluated geometry fingerprints when persisting face indices, and keep source lighting/context fixed across matched detail comparisons; stale topology or per-view exposure changes invalidate the comparison.
- Cache evaluated Geometry Nodes instance meshes by datablock identity (`as_pointer()` within one dependency-graph evaluation), not mesh name: anonymous meshes from Split to Instances can share names while containing different geometry.
- Retain any displaced source material needed for repeat application with `use_fake_user=True` before replacing its last user; otherwise save/reopen drops it and breaks restoration. Test idempotence after reopening, not just twice in memory.
- Distinguish physical label/print clearance from extra screen-space placement reservations. Audit actual instance vertices or conservative transformed bounds against the full protected rectangles/BVH; report screen-mask crossings separately rather than silently treating a root filter as full-geometry clearance.
- For lathed profiles and sampled spheres, inspect winding separately: the direction of radial/profile progression determines outward normals.
