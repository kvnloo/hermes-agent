---
name: dream-loop
description: Use when iterating visuals toward an approved target.
version: 2.0.0
author: Anshu (achimala), Kevin (kvnloo), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [visual, iteration, reference-matching, evaluation]
    related_skills: []
---

# Dream-loop v2

Lock a visual target, build one attributable change, inspect real output, and retain only an evidenced improvement. Use this method for stills, Blender, games, Three.js, UI and interactive products; a beautiful screenshot does not prove working interaction or a reusable 3D asset.

## When to Use

- Match or refine a product against a reference; recover a stalled visual loop; review sibling variants; calibrate critics against owner decisions.
- Do not use image similarity as a substitute for functional, accessibility, performance, licensing or safety checks.
- For read-only critique, run the evidence/critic stages only: do not edit sources or invoke a renderer.

## Prerequisites

- Obtain the target, current artifact, authorized scope, owner preferences and a capture/viewer path. If missing, discover existing assets before regenerating.
- Use Python 3.10+, Pillow and NumPy for image helpers; Node 18+ for the retained optional Fal helper. Provision dependencies in an isolated environment. Judges need a verified vision-capable tool path; test actual image delivery.
- Resolve this skill directory and the product workspace independently. Keep product artifacts in its own gitignored `.dream-loop/` or assigned artifact directory, never in the installed skill.

## How to Run and Quick Reference

Invoke through `terminal(command="...", workdir=<product workspace>)`, resolving script paths from the skill root:

```text
python <skill>/scripts/overlay.py target.png capture.png rounds/r01/overlay
python <skill>/scripts/crop_gate.py target.png capture.png rounds/r01/crop
python <skill>/scripts/structure_gate.py target.png capture.png rounds/r01/structure --mask ui-mask.png
python <skill>/scripts/tile_splitter.py target.png capture.png tiles-r01 --semantic regions.json --cols 4 --rows 6 --padding 32
python <skill>/scripts/aggregate_verdicts.py tiles-r01/manifest.json verdicts critic-r01.json
python <skill>/scripts/compare_sheet.py compare-r01.png target.png parent.png candidate.png --labels TARGET PARENT CANDIDATE
python <skill>/scripts/ab_judge.py target.png parent.png candidate.png BRIEF.md judges-r01 --preferences OWNER-PREFERENCES.resolved.md --provider anthropic --model <available-model>
```

Read [script contracts](references/scripts.md) before invoking new helpers. Run tests with `terminal(command="python scripts/run_tests.py", workdir=<skill root>)`; tests prove helper behavior, not visual quality.

## Procedure

1. **Lock intent and evidence.** Save original target, hashes, camera/viewport/state, output density, ART STYLE and owner interpretation. Write per-element COPY versus INTENT rows, approved deviations and protected regions in [BRIEF](templates/BRIEF.md); resolve canonical scoped [OWNER-PREFERENCES](templates/OWNER-PREFERENCES.md) and paste applicable decisions verbatim into every brief/judge packet. A cleanup or re-dream is a new owner-approved target revision, never a silent replacement. See [target](references/target.md).
2. **Approve the language and reproduce the baseline.** Before full asset work require native target crop, structural reading, two distinct form hypotheses, one negative example, a real coupon and owner approval; see [exemplar gate](references/exemplar-and-preflight.md). Resolve the selected artifact from CURRENT, not newest filenames. Capture a no-change control under the same renderer/browser/settings; disclose drift. Freeze an owner-approved fixture before lanes diverge. See [provenance](references/provenance-and-ops.md).
3. **Scan breadth-first before going deep.** Each round, diff the whole frame against the target region by region (presence/absence of objects and growth, blur/bokeh maps, light sources, luminance, artifacts), rank differences by visible area x severity / cost, and fix the cheap large ones first; deep single-element lanes come after. Drive placement from the target itself where scope allows (camera-projected target masks as scatter/density maps). When a defect survives two trials, run the [Dream-RSI step](references/dream-step.md) over the archive (untried mechanism classes, recombinations of partial wins, recipes from other elements, prefix replay) to generate the next portfolio instead of another near-variant.
4. **Gate structure before polish.** Protect only explicitly locked attributes, not every property of a locked element. Additional exclusion masks need scoped approval. Alternate views without targets get baseline consistency/runtime checks, not hero-reference similarity gates. Compare equal-aspect full frames, overlay, inspect, then run the calibrated crop/structure gate. A failed hard gate permits camera/massing diagnosis, not material polish or a partial total score. Keep camera locked except an authorized camera trial. Mask UI identically for scene review; retain physical labels and judge the shipped UI separately. Owner-authorized local diagnostic exceptions must be explicit. See [loop and gates](references/loop-and-gates.md).
5. **Preflight and test one visual hypothesis.** Inspect actual receivers/effective materials or computed styles, light-link membership, exposure/view/glare before candidate renders; use [preflight](templates/receiver-preflight.md). Name the gap: FORM, MATERIAL RESPONSE, LIGHT, ALBEDO (or MAPPING/DISPLAY). Change one class; use an isolated component/coupon with a one-variable control when cause is uncertain. Name the physical cause, research primary sources, prove it, then apply under the integrated fixture. See [research first](references/research-first.md) and [component lanes](references/component-lanes.md).
6. **Self-review, judge fresh, then adjudicate.** Log [self-review](templates/self-review.md) and directive state before paid judging; keep history in diagnostics, not promotion prompts. Use two blind A/B sessions with sides swapped against the parent; list approved deviations in both. Calibrate native-crop rankers on scoped owner-labelled anchors and known failures, with held-out families and ties/abstention. Inspect native target/candidate crops and whole-frame hierarchy; audit delivered image dimensions. The image budget is a brief constraint, not a universal three-image platform cap. Judges are rankers, not rulers. Separate technical preservation, brief status and owner acceptance. A preference is not release approval. Use semantic + padded-grid critics and a framed panel for milestone diagnosis, not after every tweak. See [critics](references/critics.md).
7. **Gate final-density fidelity and checkpoint every batch.** For deep zoom/high-resolution delivery, audit >=1 effective source texel per final pixel in both directions, registered target-pyramid tiles and fixed full-final-density native crops each round; see [fidelity/style layers](references/fidelity-and-style.md). Separate grain/halftone/ink/cel/faceting from physical material cues. AI artwork may be projection-painted and baked into actual mesh textures when authorized, never substituted as a 2D paint-over of the render. Show TARGET | previous | candidate plus worked-region crops in the owner's viewer and verify it loaded. Render and review every candidate twice: a LOOK render with optics (DOF, softness, haze, bloom) tuned to the reference, judged for appearance against the target, and a CLEAR render without DOF, judged for craft and final-density fidelity; a crisp render can mismatch the target's look, and a blurred one can hide defects. A judge HOLD must not block this checkpoint. Freeze an owner “pretty close” frame; combine specifically chosen features rather than reverting later wins. Use the [stable defect ledger and dispatch guard](templates/defect-ledger.md); if two focused trials leave the same blocker, block dispatch before a third and present two different directions with cost/risk. Renaming a family does not reset this budget. See [owner loop](references/owner-loop.md).
8. **Integrate, propagate, record.** Apply selected lane versions in fixed order: exposure/lighting baseline, materials, geometry/props, dependent effects, one owned postprocess/bloom. Reopen/replay and check protected regions plus interfaces. Port approved shared quality with per-variant configuration; retain each variant's style/view transform. Append every round, including rejects and parked features, to the [ledger](templates/rounds.schema.json). CURRENT is explicit selection with status, never implicit approval. See [variants](references/variants.md).
9. **Finish with evidence.** Meet all three gates plus runtime requirements; retain source, capture, commands, settings, hashes, raw verdicts and owner decision. Report unresolved gaps honestly. Extract only replay-tested lessons into reusable recipes; evaluate changes on held-out projects. See [evals](references/evals.md).

## Reference index

- [Helper contracts](references/scripts.md) · [Discovery tree](references/discovery-tree.md) · [Meta-learning runner](references/meta-learning.md) · [Final-density fidelity/style](references/fidelity-and-style.md)
- [Compatibility, legacy schemas and tools](references/compatibility.md) · [Classic](references/classic/README.md) · [Image onboarding](references/onboarding.md) · [Fal](references/fal.md) · [Tiled mesh maps](references/tiled-mesh.md)
- [Target and style](references/target.md) · [Loop and gates](references/loop-and-gates.md) · [Critics](references/critics.md)
- [Owner loop](references/owner-loop.md) · [Component lanes](references/component-lanes.md) · [Research first](references/research-first.md)
- [Variants and history](references/variants.md) · [Provenance and operations](references/provenance-and-ops.md) · [Evaluation](references/evals.md)
- [Research synthesis](references/research-synthesis.md) · [Exemplar/preflight](references/exemplar-and-preflight.md) · [Domain packs](references/domain-packs.md) · [Quackles case study](case-studies/quackles-2026-10.md)
- Compatibility: [hard gates / historical rubric](references/hard-gates.md), [structure-gate algorithm](references/structure-gate.md), [legacy Pro](references/pro-mode/workflow.md), [legacy Plus](references/plus-mode/workflow.md). Do not mix the legacy Pro and Plus orchestration recipes. V2 scope/owner rules supersede their acceptance shortcuts.

## Pitfalls

- Do not reward gate-number decreases after PASS, extrapolate beauty from geometry counts, or hide regressions behind majority preference.
- Do not call upscaled detail native, inferred maps measured PBR, projection relightable reconstruction, or tests owner acceptance.
- Do not overwrite renders, share unowned global settings, drift from the approved fixture, or restart a failed worker before inspecting its saved artifacts.
- Do not replace owner-disallowed methods with a differently named equivalent. A no-paint-over preference still permits research and real craft, not a silent image-finishing branch.

## Verification

Before dispatch, audit the worker plan against the [handoff checklist](templates/worker-plan-checklist.md). Explicitly include owner-anchor calibration before using fresh rankers, final-density metrics plus delivered-crop audit, and representation permissions. Do not let a compressed plan silently omit these or convert absent evidence into factual deficiencies.

Require immutable input receipts; correct capture identity/density; calibrated gates and protected-state replay; validated fresh-judge evidence; owner checkpoint; explicit current/approval status; complete rejected history; and product-specific runtime checks. Missing evidence means incomplete, not an invented PASS.
