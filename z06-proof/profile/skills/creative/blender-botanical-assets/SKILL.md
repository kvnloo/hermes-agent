---
name: blender-botanical-assets
description: "Use when building procedural Blender plant assets."
---
# Procedural botanical assets

- Export `build(origin=(0,0,0), name='plant')` returning root and every created object; include the root in the list and parent all other objects directly to it. Set only the root translation to preserve local pot-base coordinates.
- Keep import side-effect free and create fresh namespaced datablocks instead of looking up and modifying shared materials.
- Form leaves from longitudinal center curves and lateral width profiles; vary cup, twist, taper and elevation per blade. Use thin Solidify with a reverse material for bronze undersides rather than sphere foliage.
- Weld a blade's base and pointed tip to single vertices, taper lateral roll and edge waves to zero at both ends, and check evaluated reverse-material normals; a grid can otherwise leave split tips or loose petiole joins despite passing mesh validation.
- Isolate new substrate-detail randomness from the canopy RNG and compare protected pot/primary-stem vertex and topology tuples against the baseline; closeup detail should not silently reshuffle a strong silhouette.
- Use unequal stem heights and asymmetric leaf tiers to preserve a readable upward silhouette. Do not confuse total blade length with vertical height: measure evaluated vertices in Blender.
- Evaluate stem paths and their leaf/branch attachment points with the same parametric function. Interpolating leaf nodes independently from a curved stem creates floating petioles; sample the shared path densely for smooth CPU-safe curves, and check attachment distances against the actual sampled centerline.
- Evaluate petiole, secondary-shoot and fruit-peduncle anchors from the exact same centerline functions that generate their parent stems; linear proxy anchors can float off visibly curved Bezier branches. Likewise derive veins from the actual lamina surface rather than a separate approximation.
- Write a smoke test before implementation; test import isolation, all-created-object coverage, direct root parenting, actual evaluated geometry bounds, preservation of existing objects and a translated second build.
- Run headlessly with `--factory-startup -b -Y --python-exit-code 1`; testing geometry does not require GPU work or rendering.
- For a clean demonstration blend, create a separate asset-only scene in the test harness and make it active before saving. Preserve the startup scene instead of deleting its objects or saving a default cube that occludes the plant.
- Distinguish startup addon dependency warnings from asset failures using the Python exit code and explicit behavioral assertions; report unrelated environment warnings rather than changing the shared Blender installation.
- Re-seat ground spores and plant bases onto the highest allowed rendered surface, not only the original support mesh; later decorative stone caps can bury correctly raycast microgeometry. Keep an explicit receiver allowlist and exclude protected artwork/hero objects.
- Put luminous mushroom rims and gills outside the cap's closing faces. A bright internal underside disc can be completely occluded; use a thin outer rolled lip and an externally visible undercap before raising emission power.
- Do not trust hidden anchors' cached `matrix_world` after reopening Blender. For unparented immutable placement anchors, assert the no-parent contract and use `matrix_basis`; test idempotence across a real save/reopen, not only twice in one process.
- Anchor branch, compound-leaf and fruit-pedicel attachments on the same sampled centerline used to generate the stem tube. Interpolating only between original control points can place children off a curved parent even when root-parenting and bounds checks pass; keep geometric attachment checks separate from ownership tests.
