---
name: blender-campus-interior-breadth-gates
description: Use when adding many Blender campus room interiors.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [blender, interiors, cameras, evidence]
---

# Campus interior breadth gates

## When to Use

Use for multi-room Blender-as-code fit-outs, interior-camera coverage audits, or evidence delivery across independently owned campus lanes.

## Scope and establishment

- Read the canonical program and enumerate every room before detailing one. Label inferred rooms VISION; do not turn conceptual equipment or bathing suites into clinical or engineering claims.
- Respect per-module/worktree ownership. Put shared envelope, world, render and site changes in a shared-change request rather than mutating another lane's objects from an owned detail module.
- A closed massing cube is a surface mesh, not volumetric fill. An interior camera can see a locally fitted hollow inside it; however real openings, public connectivity and daylight still require an envelope pass. Do not describe emissive wall panels as real daylight windows.
- Preserve the original image baseline and source variants before queuing long renders. If only an exterior APEX baseline exists, label it as such in BEFORE/AFTER sheets; never imply a per-room same-camera control existed.

## Construction and scale

- Construct repeated cylinders and bars with direct mesh/object data APIs, and share meshes by radius/depth/material. Hundreds of `bpy.ops.mesh.primitive_*_add` calls force repeated whole-scene dependency updates and can make builds take minutes before rendering.
- Place each camera below its actual ceiling and above its actual floor. Use `scene.ray_cast` upward/downward/forward against an evaluated dependency graph, record object names and hit locations, and assert a nonzero free forward distance. Camera Z alone does not prove interior membership.
- Establish every distinct room view before polishing. Use recognizable functional mechanisms: round plates and racks, mocap camera volume and force plates, teaching islands and extractors, warm/cold suites around ordinary neutral rest, lane floats/starting blocks, lounge/book/coffee furniture, specimen racks and analysis benches.
- Model visible support contacts, not just cushions. Assert pedestal/leg bottom bounds meet the local floor and support tops intersect the seat/frame. Soft contact shadows can conceal small support gaps at review size.

## Critique and collision isolation

- Render, LOOK, name one biggest visible defect, change one class, and rerender the same camera. Treat the first comprehensive fit-out as an establishment pass, not a controlled one-variable improvement.
- If an unexplained dark pillar or slab appears, ray-probe the exact rendered pixel before changing materials. Campus site props can intersect room volumes; request relocation of a shared site tree rather than disguising it as interior furniture.
- A reframed camera may remove a collision from the selected image, but it does not repair the scene collision. Report both selected-frame cleanliness and unresolved geometry separately.
- Check that function-defining props and titles actually fall inside each frame. A modeled reaction wall, technician or turf strip outside the crop cannot support a visible-readability claim.

## Render supervision and delivery

- Use the owner's one host-wide render lock and mandated wrapper. Run sequentially and wait. If a foreground tool times out, inspect its process and log before retrying: the underlying renderer may still be running. Never launch a second owned render while an earlier one survives.
- Diagnose the renderer's actual worker cgroup before treating a long build as GPU slowness. Read `/proc/<pid>/cgroup`, `memory.high`, `memory.max`, swap limits, `memory.events`, `memory.pressure`, process CPU time and a bounded unit journal. A process pinned at MemoryHigh with unchanged CPU time and huge disk reads is thrashing; reducing SPP/resolution does not reduce full-scene build RAM. A native no-render pass is not proof the later Cycles render fits. Keep hard/parent resource policy intact unless separately authorized; distinguish scoped transient soft-limit adjustments from global policy changes, and never change another lane's worker.
- Keep immutable archives by pass, record samples per selected image, and disclose which are exploration quality versus high-sample picks. Sample count does not establish AAA quality.
- Persist a machine-readable per-room manifest and verify counts in Python: expected rooms, unique cameras, unique image hashes, dimensions, render-log success markers, and equality between selected archived PNG and delivered PNG.
- Make an honest all-room contact sheet and inspect it plus native defect crops. Preserve a per-room status/remaining-defect matrix and a ranked shared-change list.
- Commit only scoped source and selected images, not regenerated blend backups, scenes, or incidental export files. Rebuild/export/native runtime and simulation acceptance remain separate gates.
