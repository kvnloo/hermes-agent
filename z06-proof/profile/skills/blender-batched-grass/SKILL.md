---
name: blender-batched-grass
description: "Use when building batched Blender grass modules."
---

# Batched grass modules

- Keep import inert and expose a `build(origin, name, width, depth, seed)` function returning a root empty plus an explicit object list; preserve cameras, world, existing objects and selection.
- Use a private seeded random generator and combine broad spatial fertility variation with small root clusters; independent uniform height and color noise reads as a synthetic rug.
- Represent each blade as three cross-sections of three vertices plus one tip. Four quads plus two tip triangles yield ten triangles per blade; a slight center ridge catches light without thickness modifiers.
- Batch all blades into one mesh and use point-domain vertex color for per-blade hue and root-to-tip gradients; do not create an object or material per blade.
- Limit wind displacement using distance from the rectangular boundary before building blade tips; clipping completed tips produces unnatural cut silhouettes.
- Keep low trefoil accents in a second mesh; omit earth by default for host-ground integration so the lawn never adds a rectangular rug-like ground tile.
- For continuous short lawn, distribute candidates across jittered equal-population spatial strata and vary height/color rather than rejecting broad low-fertility regions; this avoids sparse islands. Bound the complete candidate budget before masking.
- When dissolving an existing rectangular density edge into a wider island, redistribute a fixed pre-mask budget with a smooth garden-centered Gaussian plus broad island scatter; do not simply expand the dense rectangle or multiply blades globally. Preserve continuous sod independently of blades and assert continuity at the former rectangle edges.
- Discover plant exclusions from current root ID properties rather than root names, because independently authored assets may use different naming conventions. Recompute world-space masks after layout adjustments and retain exact mask object names and root coordinates in the receipt.
- Apply a callable exclusion mask to both blade and clover bases using build-time world XY, and check emitted vertices if overhang onto hardscape is forbidden. Consume candidate randomness independently of rejection so an all-True mask matches an unmasked build. Document that moving the root invalidates world-space exclusions and that vertex checks are not exact clipping against arbitrarily tiny holes.
- Smoke-test all-False, all-True and partial masks at nonzero origins, assert blade/clover exclusion and deterministic output, and exercise the actual maximum blade count rather than only a reduced test cap.
- Test the executable build through `blender --background --factory-startup --python-exit-code 1 --python test_asset.py`; assert inert import, origin, bounds, preserved scene, triangle budget, nonzero polygon area and upward ground-cover leaf normals.
- Check leaf normals explicitly: translating a 2D outline from lateral/longitudinal coordinates into world XY can reverse its winding even when every face has nonzero area.
- Report actual Blender stdout and geometry counts separately from visual approval. A successful headless geometry test does not establish that the scene has been rendered or artistically approved.
- Treat Blender extension-registration errors separately from the tested script exit status; a missing unrelated extension dependency can log a traceback while the requested module still executes successfully. Never invent a clean run or change global packages merely to hide that warning.
