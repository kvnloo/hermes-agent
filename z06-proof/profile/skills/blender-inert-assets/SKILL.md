---
name: blender-inert-assets
description: Use when building import-inert Blender assets.
version: 0.1.0
platforms: [linux, macos, windows]
---
# Import-inert Blender asset modules

## When to use
Use for procedural Blender modules intended for integration into another scene, especially when a parent handles rendering and visual review.

## Procedure
1. Expose `build(origin=(0,0,0), name='asset_id')` returning a root empty and a list of every created geometry object. Keep all bpy creation inside build or functions called by build so imports are inert.
2. Use the data API rather than operators. Parent every generated object directly to the root, author geometry in root-local coordinates, and put the requested origin only on the root. Do not clear a scene or change camera/world/render settings.
3. Keep an optional private geometry helper beside the entry modules. Load it by file-relative importlib path so standalone path imports require no sys.path modification.
4. Use lathed profiles for thick-walled pots, including a real inner wall and a soil surface below the lip. Start the outside bottom at z=0. Use single pole vertices at profile radius zero to avoid degenerate pole rings.
5. Use sampled curved blade meshes with cup, rise, twist and thin solidification for leaves; place curved midribs on the sampled blade centerline. Vary shoot height, orientation and maturity instead of uniformly repeating a radial rosette.
6. Write a structural smoke test before implementation. Snapshot bpy object/material/mesh/curve counts before import; execute each build at zero and nonzero XYZ origins; compare actual new objects against the returned set; require root parenting and materials.
7. Measure evaluated mesh vertices after dependency-graph update, including converted curves and unapplied modifiers. Subtract origin from world-space vertices before comparing translated bounds. Check ground z=0 and nominal heights.
8. Run with `terminal(command='blender --background --factory-startup --python-exit-code 1 --python <smoke.py>', timeout=120)`. Never render or request a GPU when only structural verification is authorized.
9. Record actual bounds, evaluated vertex/face counts, object totals including/excluding root, tool exit status, and visual-review limits in DESIGN.md plus machine-readable JSON.

## Pitfalls
- Object dimensions alone do not reliably account for all evaluated curves and modifiers; evaluate meshes for bounds.
- Treat startup extension tracebacks separately from smoke failures. A missing optional remote-library dependency may print an error while the asset test still succeeds; document both and do not modify the user's Blender installation to hide it.
- A successful structural test is not visual approval. Leave render judgment explicitly pending when delegated elsewhere.
- For large procedural scenes, invert collection membership in one pass over collection.objects instead of calling object.users_collection for every object; Blender's Python property repeatedly scans collection object membership and can turn ownership checks into a multi-minute bottleneck. Keep the same exact-ownership assertion, use bpy.data.batch_remove for repeated-build cleanup, and add phase/stack diagnostics before treating a timeout as a geometry failure.
- Test reusable closed primitive winding before lookdev: for an origin-centred unit box/sphere, every nondegenerate polygon must have normal.dot(center) > 0. Inward faces can leave opaque previews plausible while breaking glass/reflection behaviour; visual inspection alone is not a sufficient normals gate.

## Verification
Require inert imports, repeated successful builds, correct nonzero-origin translation, all created objects returned and root-parented, nonempty evaluated geometry, ground contact, plausible dimensions, and retention of pre-existing scene objects/camera/world. Report only executed checks.
