---
name: blender-frequency-split-projection-gates
description: Use when band-splitting reference textures on meshes.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [blender, projection, frequency-split, fidelity]
    related_skills: [blender-reference-match-loop, dream-loop]
---

# Mesh-bound frequency-split projection gates

Use the current owner contract and reference-match loop. This procedure qualifies a fixed-camera low-band texture experiment; it does not establish a relightable reconstruction or guarantee a visual win.

## When to Use

Use for a fixed-camera Blender experiment that transfers reference-scale tone through real mesh textures while preserving procedural or geometric detail at deep zoom.

## Procedure

1. Freeze the scene, camera/lens, target, display transform and protected print. Capture a matched no-change render with the candidate's engine, samples and seed; an older render at a different sample count is not a pixel-exact control.
2. Preflight the visible receiver and clone its mesh/material data before changing UVs or graphs. Bake the locked camera projection into a named UV layer without replacing existing artwork UVs. Record the receiving objects explicitly.
3. Low-pass the source before using it as a tone carrier. Keep mesh facets and metric-domain procedural grain in independent mid/high layers. Do not claim that a deliberately low-resolution tone carrier supplies final-density detail texels.
4. Segment non-receiver source content before filtering. Masking the receiving object alone does not remove mushrooms, lettering or other props already present in the projected source; direct low-radiance mixing can turn those into soft luminous ghosts.
5. Normalize tone transfer against the matching donor's own no-change appearance. An it14-like baseline ratio applied to another donor with a much darker shader can darken an already featureless front; that is not a conclusive test of the new donor mechanism.
6. Avoid independent channel division near black. Prefer a regularized luminance ratio and separately bounded colour correction; near-zero RGB denominators can amplify small colour differences into visible casts.
7. Apply label/print exclusions to every new branch, including bump strength, coat, roughness and emission mixing. Neutralizing only the base-colour ratio does not protect an existing printed layer from the other branches.
8. Test tone-only, geometry recombinations, target-conditioned coat placement and a distinct wildcard. Inspect isolated and integrated LOOK/CLEAR separately: removing the robot can expose a reflection that disappears under its real shadow.
9. Render actual fixed borders at the final master dimensions. Pair a low-band-on/off ablation with identical mesh/high-band sources, and measure high-pass correlation/contrast. Check that the crop actually lands on exposed stone; a top crop full of foliage cannot certify the stone shader.
10. Verify save/reopen and deterministic reapply using geometry, UV, material-graph and protected-state fingerprints. A local wrapper must be exercised too. If its recipe depends on canonical local paths, pin those dependencies and do not claim relocation support.
11. Keep technical validity, narrow blind preference and visual acceptance separate. Brighter top reflections can coexist with fewer front glints; report both. Crisp mesh boundaries alone do not prove a convincing gigapixel material finish.

## Operational pitfalls

- Exercise helper Python under the same sanitized environment used by Blender before scheduling a long render batch. A system-site-packages venv can appear functional in the interactive shell yet lose inherited numpy/Pillow paths under `env -i`; install required packages inside the owned environment.
- Serialize real render work with the project's shared lock and admit GPU work only under its free-memory/lock policy. Retained GPU context memory between sequential jobs is not evidence that another session is responsible.
- Preserve the first delivered candidate and its exact recipe/maps before replacing a provisional delivery. Append an explicit archive-location correction to the event ledger so old artifact hashes do not silently point at the new candidate.

## Verification

Require real paired renders, matched control, native/final-density crops, exclusion and protected-state checks, reapply/reopen evidence, fresh side-swapped judgments, decoded review-page images, immutable failed evidence and an explicit promotion/hold decision. Missing source segmentation or donor normalization is a limitation, not a fabricated pass.
