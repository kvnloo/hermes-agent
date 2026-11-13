---
name: creative-plant-scene
description: Use when building creative plants and garden scenes.
version: 0.1.0
author: Kevin Rajan (kvnloo), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [blender, plants, garden, dream-loop, creative]
---

# Creative plant scene

## When to use
Use for authored plant/pot collections, creative garden blockouts, and their visual critic loops. Do not treat this as a survey or dated reconstruction workflow.

## User direction
The user prefers a complete creative scene basis before reference accuracy: use loose plant/pot descriptions, build every individual specimen, then refine through actual rendered criticism. Excessive photo-matching constraints too early have reduced quality. Explicit creative freedom overrides old reference-target gates for the new botanical work, not unrelated house/walkway authorization.

## Observation-calibrated digital-twin work

When the user requests a biological digital twin rather than creative asset authoring, do not apply creative-first shortcuts to model selection. Start with dated observations and identity/uncertainty, compare reusable whole-plant FSPM backbones (including CPlantBox, OpenAlea and GroIMP), and fit one evolving parameterized trajectory across multiple dates. Separate engine, parameterization, observed state, inferred state, simulated state and environment. A generic LPy leafy-axis demo proves execution/export only; never substitute it for a calibrated identified plant or ask permission to call that the requested architecture. Use Blender assets downstream for appearance after structural fitting is demonstrated. Preserve camera/scale ambiguity, visible-count lower bounds and withheld dates; an in-sample morphology fit does not validate future biological prediction.

## Procedure
1. Preserve existing source and candidate files before changing them. Build a new creative candidate, not an overwrite of the protected scene.
2. Enumerate every requested specimen and grass separately. Derive simple plant/container descriptions; leave unknown species unnamed rather than invent identities.
3. Parallelize independent authored assets. Each lane owns its module, helper files and output directory. Export `build(origin=(0,0,0), name=...) -> {'root': object, 'objects': list}`. Keep import inert and root-parent every created object; prohibit scene resets, existing material mutation and camera/world edits inside asset modules.
4. Prioritize readable silhouette, natural variation and coherent pot/leaf materials. Use curved authored leaf geometry when the user requests imagination rather than private-image reconstruction. Do not enforce photograph-overlay gates against nonexistent references. Do not TDD artistic appearance; smoke-test the executable integration contract.
5. Exercise each module in headless Blender: import isolation, repeat build, translated origin, ground contact, parenting, finite geometry and existing-object preservation. Cap concurrent heavy renders separately from reasoning workers.
6. Integrate through one scene writer. Ray-test the CURRENT building/ground before placing plants: old slot coordinates can be inside a revised house. Distinguish creative locations from recovered metric coordinates.
7. Render the complete scene and an individually labelled specimen contact sheet. Inspect actual pixels with `vision_analyze`; test pass and a builder's praise are not visual acceptance.
8. Fresh independent critics review each specimen plus the scene. Use composition, lighting, materials and details, interpreted against the creative brief rather than photo identity. Choose one high-leverage change class per round and compare from the same camera. Preserve the stronger candidate.
9. Save/reopen the final candidate, enumerate every plant ID programmatically, verify visible geometry, preserve original house data and expose output paths. Report a creative basis as such; do not claim botanical or survey accuracy.

## Pitfalls
- When launching system Blender from an agent environment, isolate Python discovery with `env -u PYTHONPATH -u PYTHONHOME PATH=/usr/bin:/bin /usr/bin/blender`. A bundled agent Python earlier on PATH can redirect embedded Python even after PYTHONPATH is cleared, causing missing `math`/`_socket`, unregistered UI operators and GUI crashes. Verify imports plus `bpy.ops.wm.tool_set_by_id.get_rna_type()` headlessly before opening a user scene; do not alter global Python or reinstall Blender to mask this launch-environment fault.
- Audit maintained OSS growth engines before adding custom simulation equations; separate a developmental engine (such as LPy or GroIMP), its model, a geometry toolkit, and provenance glue. Verify package availability, exact release/model licenses and a real headless model run before promising integration; dependency discovery and deterministic JSON are not simulation or biological validation.
- Avoid authored grass rectangles that read as three separate rugs. Cohesive ground coverage and intentional paths matter more than extra blade detail.
- Check the substrate beneath short blades before increasing density: an exposed yellow ground can make an adequate lawn read as stubble. Use a reversible muted sod material/underlay while preserving hardscape and protected source data.
- Let fresh visual comparison reject a revision even when its geometric tests pass; altered leaf tilt can become an origami-like regression. Retain the stronger original rather than treating every technically valid iteration as progress.
- Do not assume a headless render used the intended camera. Set the scene camera, update the view layer, disable inherited sequencer/compositor overrides when not required, then inspect the image. A wall-filling image may be actual occlusion from stale coordinates rather than a render-setting problem.
- Blender 5.x legacy curve bounds can be inflated; use evaluated bounds or bake only owned curves when sizing/framing assets.
- For a time-boxed multi-agent build, let independent workers return separately. A single all-worker completion unit can hide finished assets behind the slowest worker; integrate ready, tested components instead of waiting for every lane.
- Separate reasoning concurrency from Blender/render concurrency. Give one owner the integrated scene and render queue, prioritize previews by the decisions they unblock, and reserve time for save/reopen verification rather than new features until the deadline.
- Treat free VRAM and GPU availability as different signals. Graphics can occupy the device even when the compute-process list is empty; sample utilization and memory, cooperate with other owners, and retain a CPU-only critical path. An advisory lock coordinates only workers that honor it.
- Keep original blades/foliage reusable as sources; do not append multiple copies just to fake plant completeness.
- Recompute lawn/pot exclusion masks after changing root positions; otherwise new pots acquire blade intersections while their old positions retain misleading bare holes. Compare root-only placement first, then remasked ground as a separate reversible pass.
- Separate whole-house read hierarchy from specimen coverage: an island hero should show a coherent garden gesture, while cluster details must visibly account for every retained ID and pot. Frustum inclusion and root counts do not establish pixel visibility.
- When workers cannot run Blender, keep a pure root-translation planner and transactional apply/rollback testable in stdlib, label old-bound projections as offline, and stage a parent-only live-bounds/ground/immutable-state smoke ticket rather than claiming a new scene was verified.
- Maintain private source imagery locally. No external image service is needed for purely creative bpy assets.

## Verification
Confirm all requested IDs, asset-module smoke results, saved/reopened scene visibility, unchanged source-file hashes, inspected hero/catalog renders, and at least one independent visual critique. Record unresolved refinements without blocking delivery of the requested initial scene basis.
