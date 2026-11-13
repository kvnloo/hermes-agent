---
name: lpy-headless-growth-export
description: "Use when exporting real LPy growth stages headlessly."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [lpy, plantgl, simulation, geometry, provenance]
    related_skills: [blender-inert-botanical-asset, test-driven-development]
---
# Real LPy growth to OBJ

## When to Use

Use for an authorized headless LPy/PlantGL execution that must export actual model-derived plant geometry with deterministic replay and honest provenance.

- Audit reasonable project/local interpreter and Conda roots before installing. Probe module specs without importing unreviewed package initializers; do not read credentials or modify global Python.
- Put the worker environment, micromamba root/cache, HOME, XDG paths, temp files, downloads and artifacts inside the user-authorized root. Set numerical threads to one, limit CPU affinity, and bound worker time/address space. Never launch a viewer or render for a geometry task.
- Pin LPy, PlantGL, Python and a reviewed upstream model commit. Preserve source unchanged; Python in `.lpy` files is executable code. Record native imports, package URLs/builds/hashes, model digest and component license notices.
- Distinguish a generic architectural proxy from a species-specific model. Do not claim that a generic leafy axis supplies species biology. Record the existing creative key without inventing specimen IDs, environmental responses or calendar-time semantics.
- Call the actual `Lsystem`, `derive(state, start_index, count)` and `sceneInterpretation` APIs. Use PlantGL's OBJ codec rather than a replacement L-system interpreter. Define presentation stage labels as explicit derivation indices.
- Validate native scene meshes and exported OBJ vertices, normals, face indices, finite bounds and positive surface area. Compare exported counts against native discretization, and round-trip with a real OBJ reader.
- Set stable shape transport names before export. PlantGL's OBJ writer includes wall time in its first comment; retain raw files and canonicalize only that comment before comparing byte hashes. Do not alter numeric geometry to manufacture deterministic evidence.
- Test replay in fresh processes and interleaved native contexts, comparing both L-strings and geometry. Treat L-string serialization as evidence, not a full context checkpoint; replay from the axiom unless complete checkpointing is separately proven.
- Verify the actual explicit environment lock consumer. Some micromamba `list --explicit` outputs have a human-readable header without `@EXPLICIT`; convert to the proper explicit format and run an offline create dry-run. Keep cryptographic package digests alongside the lock.
- Preserve upstream licensing discrepancies rather than silently resolving them. A model's GPL notice, native source headers, package metadata and empty root license can disagree; keep evidence and flag redistribution clarification separately.
- Hand Blender one fixed coordinate/scale convention for all stages. Per-stage normalization can erase visible growth. Keep material adaptation, scene ownership, original assets and final visual acceptance with the Blender adapter owner.
