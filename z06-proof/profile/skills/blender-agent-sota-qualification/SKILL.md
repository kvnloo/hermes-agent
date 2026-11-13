---
name: blender-agent-sota-qualification
description: Use when qualifying Blender-agent research for adoption.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [blender, research, agents, materials, evaluation]
    related_skills: [grounded-citations, blender-reference-match-loop, blender-lookdev-recipes]
---

# Qualify Blender-agent research for production

## When to Use

Use for research surveys or adoption decisions involving Blender agents, procedural material synthesis, 3D code generation, visual critics, and executable skill libraries.

## Procedure

1. Separate the evaluated task: scene arrangement, code validity, geometric reconstruction, procedural material matching, visual quality, or complete editable deliverable. Never relabel a benchmark gain as AAA production quality.
2. Read the primary paper's evaluation protocol and limitations before recording headline results. Record candidate/search budgets, baselines, target access, renderer, and model version; distinguish best-of-N results from one-shot generation.
3. Read the actual repository license and README, then pin its commit. Check code, weights, training data, preview scenes, and imported assets separately. Public source is not a reuse license. Small adapter size is not inference memory.
4. Check installed Blender versus the implementation's exact bpy/Python/render-engine requirements. An abstract API may be valuable even when the released package cannot run on the production version.
5. For material plateaus, compare representation families before numerical tuning. Shader search cannot supply missing silhouette, fiber geometry, anatomical relief, or canopy mass. Use intermediate masks/AOVs and scene inspection to separate appearance complaints from implementation facts.
6. Prefer typed, compact, inspectable authoring interfaces; retain an incumbent across structural changes and fit numerical parameters only within plausible families. Measure candidate-selection quality before increasing generation or verifier budgets.
7. Treat VLMs as fallible rankers. Use blind/swapped pairs, explicit ties/unknowns, original-resolution crops plus whole-frame context, owner-approved anchors, and known bad controls. More sessions of one model are not independent human evidence.
8. Promote reusable skills only with callable code, parameter units/ranges, render examples, failure cases, version assumptions, rights, and a held-out transfer check. Keep API-valid, mechanism-proven, appearance-approved, and owner/integration-approved as distinct levels.
9. Preserve all discovery sources separately from the cited subset. Normal citation verification checks mappings; strict modes may reject intentionally unused discovery links. Validate document sections with anchored heading boundaries, not substring splits that match deeper heading levels.

## Relevant research patterns

- BlenderAlchemy: balance structural leaps and parameter tweaks, preserve best-so-far, compare real renders.
- LL3M: version-specific retrieval can prevent agents from deleting complex operations to fix errors; its software licensing must be checked before reuse.
- ProcFunc: compact functional abstractions can improve generation; package version pins can block adoption even when the paper is relevant.
- VLMaterial / ShaderAgent: graph structure proposal and numerical fitting are different jobs; restricted scorer/assets may coexist with permissive code.
- MultiMat: inspect intermediate graph outputs, not only final beauty.
- MatLoom: shared spatial fields can keep channels coherent; unmatched seed-search budgets limit comparative conclusions.
- BlenderGym / BlenderWorld / 3DHarnessBench: evaluate the harness, artifact, and evidence access, not just the model name. Full target-geometry access is unavailable when reconstructing a single reference still.

## Verification

Report what was retrieved, tested, and not tested. Never claim local GPU fit, Blender compatibility, visual improvement, or commercial clearance from paper claims alone. Preserve the owner's no-paint-over and protected-scene contracts when translating research into experiments.
