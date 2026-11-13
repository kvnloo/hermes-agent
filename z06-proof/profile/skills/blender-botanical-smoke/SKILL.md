---
name: blender-botanical-smoke
description: "Use when smoke-testing procedural Blender plant assets."
---

# Procedural plant smoke checks

- Keep imports inert; create materials and objects only inside `build(origin, name)`, returning a root and complete visual-object list.
- Test headlessly with `--factory-startup --python-exit-code 1 --python smoke.py`; preserve preexisting object sets and camera/world identities.
- Build at a nonzero origin to catch double translation and missing parents; measure bounds relative to that origin.
- Use evaluated `to_mesh()` vertices transformed by the evaluated matrix for accurate bounds, then `to_mesh_clear()`. Curve bounding boxes can overexpand by point radius and falsely fail size/ground checks.
- Verify leaf winding against its transported local longitudinal/cross-blade frame and require opposite shared-edge traversal; never flip each curved face toward global +Z, which can reverse a valid drooping section. Check fruit skins outward separately because descending radial strips can invert normals.
- Check inverted-face area per lamina, not only the mean normal: a mostly upward sheet can hide overlapping fan strips at narrow sinuses. Keep the outline angle monotonic around the venation hub and interpolate radius rather than a Cartesian contour spline when radial topology backtracks.
- Test procedural petiole/midrib tube skin normals against the vector from adjacent ring centers to each face center; frame handedness can invert every tube while foliage checks still pass.
- Use shared longitudinal samples and weld coincident inner seam vertices when splitting a thin lamina into panels; otherwise Solidify creates hidden internal rims along intact tissue.
- Check shared-edge orientation on radial leaf and petal meshes: centre fans and annular quads can have opposite winding even when the averaged normal points upward. Every interior edge must occur twice with opposite directions.
- Measure leaf relief against a best-fit plane rather than world-Z range to distinguish truly curved blades from rotated flat plates; this is a geometry guard, not a visual-quality verdict.
- Verify the petiole endpoint meets the blade attachment vertex geometrically; metadata naming alone does not prove contact.
- Distinguish anchors inside a supporting tube from detached anchors: unsigned nearest-surface distance at a valid centerline anchor equals the stem radius. Combine original-anchor equality with signed closest-surface or solid-containment checks rather than relaxing a gap tolerance.
- Export a named collection with `bpy.data.libraries.write(path, {collection}, fake_user=True)`, setting root to zero after offset tests. Reopen and assert member count and saved root origin.
- Label a collection-only file appendable, not a ready-open scene. A library opening into an empty scene is expected; append its collection.
- If exporting a newly created Scene crashes Blender, use a Collection library instead. Never clear an existing user scene as an export workaround.
- Report missing bundled add-on dependencies separately from asset assertion failures. Use explicit exit codes and sentinel pass output.
- Keep structural checks separate from visual claims: bounds and counts do not verify canopy beauty or fruit visibility.
