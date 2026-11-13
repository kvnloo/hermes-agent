---
name: blender-volumetric-growth-gates
description: Use when moss reads as paint despite dense scatter.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [blender, moss, geometry, evaluation]
    related_skills: [blender-reference-match-loop, dream-loop]
---

# Volumetric growth gates

## When to Use

Use for a foliage target whose growth projects off a receiver while repeated leaf/dot density changes still read as paint. Separate the supporting mass from its botanical surface. This workflow is mechanism-tested, not an approved moss appearance family.

## Procedure

1. Trace a semantic growth envelope and exposed substrate islands from the target. Use it only for placement, never silently as albedo. Raycast the evaluated receiver and retain actual roots/normals.
2. Compare distinct mass constructions before tuning density: metaball unions; a closed inflated shell with voxel remesh/displacement; overlapping deformed cushions; actual Geometry Nodes points-to-volume-to-mesh. Keep camera, lighting and surface treatment fixed during the representation comparison.
3. Measure volume depth by casting the same camera rays against the new mass and original receiver. Report depth distributions separately from visual success. A centimeter-thick mass can still look flat when dark fine detail hides its lobe contrast.
4. Surface the *new volume*, not the original slab. Short clumped shoots or licensed botanical cards should follow visible volume normals; sparse leaves and bead paths are secondary. Preserve real gaps, asymmetric banks and protruding silhouette rather than extruding a uniform strip.
5. Render native LOOK/CLEAR coupons and inspect before full frames. Smooth green balloons, periodic shell waves and very dark fine carpets are negative examples. More geometry, greater thickness and valid texture sampling do not establish target similarity.
6. Include an anonymous unchanged control and unblind every reviewer result. If a reviewer says the winning option improves on control but the winner decodes to control, retain only the ranking—not the invented improvement claim. Do not promote a new family merely because a candidate had to be delivered.
7. Guard original geometry, UVs, shader graphs, transforms, camera, lights and visibility. Keep same-input no-op idempotence distinct from deterministic destructive regeneration. Metaball conversion may rename the generated mesh with a suffix: find owned recipe markers rather than assuming an exact output name. Include recipe/receiver keys and disclose the contract.
8. Inspect installed RNA/sockets before volume-node configuration. In tested Blender 5.2, Points to Volume has a Voxel Size socket but no old `resolution_mode` property. Converted volume meshes can include empty material slots; remove only the new object's unused empty slots, never relax original-state guards.
9. Preserve provisional scenes/renders when review changes the pick. A rejected portfolio is useful evidence; archive its native images, methods, implementation failures and reason for HOLD rather than relabeling it as a win.
10. Recombine coverage and volume with literal approved botanical prototypes when the owner locks the existing look. Extract disconnected leaf islands from the accepted mesh, retain topology, smoothing and material bindings, rigidly normalize their basis, and measure reconstruction error before instancing. Regenerating a vaguely similar leaf from fewer vertices can silently replace the approved morphology. Use existing darker material variants for interior tiers, surface the actual supporting volume, and retain light-link membership.
11. Compare final LOOK crops derived from matched full frames when inherited compositor masks use screen-space windows. Cropped-border rendering can shift those masks and alter background strands even when the canopy code never touched optics. Use real high-density borders for local craft, disclose their limited scope, and never count an incidental border-compositing difference as a foliage win.
12. Treat native wire kinks, even bead spacing and over-regular canopy edges as explicit watch items after a preferred recombination. Preserve the exact judged artifact; adjudicate any claimed protected-region regression with native comparisons and measured pixel deltas rather than assuming unchanged datablocks imply unchanged transport.

Do not certify an entire high-resolution scene from one small final-density crop. Newly added scan assets need their own sampling/license checks. Respect the project's shared render/GPU admission locks and leave unrelated jobs untouched.
