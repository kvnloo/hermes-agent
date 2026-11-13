---
name: blender-recessed-optics
description: Use when building recessed glass eyes in Cycles.
---
# Recessed optical assemblies

- Inspect native target pixels and the actual receiving assembly's local radial/depth profile before constructing a cornea. A legacy lens may already be curved but shaded with camera-only radial emission; mechanical rear geometry can make it unsuitable as a hollow dielectric.
- Separate reflection sources, recessed emissive geometry, physical internal light and bore receivers. Use a cornea-only receiver collection for reflection lamps; linking those lamps to the bezel can bleach its paint despite reducing albedo and neutral fill.
- Prove internal-light appearance separately from glass appearance. Sharp specular highlights and dark blue depth can improve while internal glow and rim spill regress. Enabling MNEE's caster/receiver/light flags is not proof of a visible caustic gain.
- Weld lathe pole duplicates and coincident closing seams on newly authored optical meshes, then assert zero boundary edges before calling a dielectric closed/manifold. Zero geometric boundary length is not the same as welded topology.
- Keep old locked geometry and camera unchanged; place additions in a separate collection and parent them to the head with verified world transforms. Setting a parented light's local location to a world point is incorrect; assign a full world matrix.
- Judge native border probes, then a reopened saved-scene full render, and preserve the explicit round-stop rule. Report better glass but failed illumination as a working preview rather than full acceptance.
- Compare retained material graphs directly when save/reopen changes an unused material's user count. A `users>0` filter can falsely report a shader change; inspect bindings, user counts and actual graphs before granting an exemption.
- Hash large mesh buffers with foreach_get into typed arrays instead of expanding all vertices/polygons into nested Python lists. Keep scene-object and robot/camera guards distinct, and include emitted vertex-color attributes in idempotence checks.
