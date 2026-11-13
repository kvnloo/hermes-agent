---
name: blender-inert-botanical-asset
description: "Use when making standalone scene-safe bpy plant assets."
---
# Standalone botanical bpy modules

- Keep Blender datablock creation inside `build(origin=(0,0,0), name=...)`; inert import lets parent scene scripts load many modules safely.
- Create an empty at the requested origin and directly parent all generated objects, with local ground contact at z=0; test a second nonzero-origin build to catch double translation.
- Use meshed skew-heart blades with surface relief and distinct reverse materials for begonias; do not substitute spheres for foliage.
- Sample short stem control paths as quadratic curves before generating tube meshes; three-point tubes look angular at garden-asset scales.
- Test blade winding in actual Blender against each blade's local longitudinal/cross-blade frame and shared-edge coherence; global +Z is not a valid per-face target for curled or drooping leaves. Coordinate-basis handedness is easy to misjudge by inspection.
- Run a headless no-render smoke test for import side effects, preserved existing objects, parentage, dimensions and repeat builds; report actual Blender version, bounds, base mesh counts and startup warnings separately.
- Leave cameras, lighting, rendering and scene cleanup to the parent composition task when the module only owns the asset.
