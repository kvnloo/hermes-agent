---
name: browser-3d-asset-pipelines
description: Use when designing browser 3D asset and animation pipelines.
version: 1.13.0
---

# Browser 3D Asset Pipelines

Design evidence-backed, browser-compatible pipelines for procedural or DCC-authored 3D assets, rigs, animation, PBR materials, LODs, physics, destruction, compression, and deterministic capture.

## When to use

Use this skill when a task spans two or more of:

- procedural Three.js or image-to-3D source assets;
- Blender-to-glTF/GLB workflows;
- skeletal rigs, root motion, or animation state machines;
- runtime physics, fracture, or destruction;
- KTX2/geometry compression and browser delivery;
- numeric performance budgets and testable quality gates.

Do not use it for a one-off shader snippet or a purely offline render with no browser delivery requirement.

## Workflow

1. **Inspect the real source pipeline first.** Determine whether the source of truth is code, a DCC file, generated geometry, or a GLB. Inventory existing masters, exports, rendered media, verification receipts, quality audits, licenses, and rebuild scripts before choosing the browser format. Preserve stable component IDs, pivots, sockets, collider intent, and destruction groups through every conversion.
2. **Choose the portfolio modality from verified deliverables, not from the word “3D.”** If a trustworthy browser-ready GLB exists, build an interactive viewer around it. If only a heavy Blender master and a verified rendered flythrough exist, ship the real video as the first website slice and describe it honestly as a Blender study; do not imply interactivity, silently export an unverified GLB, or embed hundreds of megabytes of DCC source in the web repository. Keep the website in a separate repository, link or document the canonical source location, include only web delivery media, and retain checksum/revision lineage.
3. **Classify the asset before choosing the reconstruction lane.** Precision hard-surface props, armored/costumed humanoids, and organic creatures have different geometry laws. A single-image generated mesh may be a useful hypothesis, but reject it before texture/post work when manufactured circles, planes, repetition, or component construction are visibly wrong. Do not confuse a sharper render with a repaired asset; see `references/generated-mesh-runtime-derivation.md`.
3. **State the canonical contract.** Fix units, up/forward axes, board/ground contact, origin, node names, material slots, scale policy, and which transform owns gameplay motion.
3. **Separate source from derived artifacts.** For procedural sources, treat the code/spec as authoritative and Blender/glTF outputs as reproducible derivatives. Use an interchange GLB before DCC cleanup when practical.
4. **Define a minimal runtime hierarchy.** Keep gameplay/entity transform, extracted motion, visuals, fracture variant, colliders, and sockets separate. Do not merge movable or breakable parts into unrelated geometry.
5. **Design archetype rigs by required motion.** Export only baked deform bones; keep controls and constraints in Blender. Prefer rigid parenting or near-rigid weights for stone, concrete, metal, and mechanical subjects. Set explicit bone and influence caps.
6. **Use explicit animation contracts.** glTF clips do not provide a general event-marker standard. Pair clips with a versioned manifest containing semantic states, looping policy, fades, root-motion policy, and markers. Dispatch markers by playhead crossing so skipped frames do not lose events. For theatrical battle products (Battle Revolution floor modernized): **every move is S+ tier** — anticipation → travel → contact/impact → recoil → settle, readable silhouette through contact, weight, secondary motion, arena-reactive camera, material/VFX response, audio lock. Distinct moves need distinct choreography. HUD flashes and recycled generic particle puffs auto-fail. Move claims require dense sequential frames or video, not a single still.
7. **Assign root motion once.** Gameplay/entity transforms remain authoritative. Extract authored horizontal displacement/yaw from a motion node, subtract it from pose animation, apply deltas to the entity or kinematic body, and snap to the exact destination at completion. Never animate the same displacement at both entity and skeleton levels.
8. **Prefer offline fracture for hero destruction.** Swap an intact animated asset to pre-fractured rigid chunks at a canonical fracture pose. Give interior faces their own material, use convex colliders, cap dynamic chunks, and represent small debris with particles. Reserve runtime CSG for rare, non-critical effects.
9. **Author glTF-compatible PBR.** Base color is sRGB; normal, roughness, metallic, and AO are linear data. Use the glTF ORM convention (R=AO, G=roughness, B=metallic). Bake non-portable procedural shading and avoid aliasing one signal into several maps.
10. **Optimize after export.** Validate first, then prune/deduplicate/quantize, compress geometry/animation, and convert textures to KTX2. Favor a fast broadly supported geometry codec and use UASTC for normals/high-frequency data, ETC1S for forgiving color data.
11. **Budget from the target frame, not asset intuition.** Define baseline hardware and resolution, then set p95 frame-time, triangles, draw calls, resident texture memory, transfer size, dynamic-body, collider, bone, and per-frame-allocation gates. Use projected-size LOD thresholds with hysteresis.
12. **Verify deterministically.** Fix viewport, DPR, camera, lighting, exposure, animation time, and random seed. Test structural validity, state transitions, root-motion closure, marker timing, fracture continuity, physics settling, visual goldens, and p95/p99 performance.
13. **Treat visibility as a rendered claim.** Scene-graph counts and DOM assertions prove existence, not that a player can see the subject through production UI, fog, framing, or blur. Capture each critical state with real UI enabled, measure major overlay bounds, and inspect an unmasked diagnostic view when visibility is uncertain.
14. **Integrate in thin presentation slices.** Wire one world/UI/VFX subsystem, then typecheck, build, inspect the live browser, and check its console before expanding. Reserve the final third of the work budget for correction, required gates, review, and commit rather than leaving several uncompiled modules at the end.
15. **Certify first-use transitions, not only steady state.** Instrument the current and previous semantic state of long frames, prewarm exact asset-cache keys but only representative shader/depth variants, perform a hidden boot draw when `compile()` alone cannot warm GPU resources, and group high-cardinality visibility under one parent. In trusted-input evidence routes, release movement keys before snapshot RPCs so GPU-fence latency cannot cause uncontrolled overshoot. Quiet unrelated preview/browser processes before repeated certification, but never weaken the gate to excuse host contention.
16. **Treat renderer quality as a production contract.** Resolve requested and active tiers through pure tested capability gates; order linear HDR passes so tone mapping and sRGB output occur once; distinguish explicit benchmark presets from automatic constrained-device fallback; prewarm, resize, instrument, and dispose the complete active pipeline. Detect software rasterizers before enabling expensive post, aggregate `renderer.info` at the outer-frame boundary, and rerun browser evidence after the final gate change.
17. **Gauntlet every quality tier, not only the default.** Wire monotonic Performance→Cinematic settings into actual pixel, shadow, LOD, material, update, and debris costs while preserving gameplay legibility. Separate bounded non-certifying smoke from repeated real-GPU sustained certification, bind claims to named hardware/resolution rows, and require fresh non-builder performance plus visual reviews after final branch integration.
18. **Separate reconstruction evidence layers.** Keep inventory, discovery candidates, fetched-byte facts, visual/identity decisions, and the compiled handoff distinct. Bind reviews and any multiview set to byte hashes; a download, official page, or model smoke never grants Hunyuan eligibility.
19. **Prove multiview geometry, not isolated depth quality.** Plausible per-frame monocular depth maps can still merge into an incoherent flower/shell when scale, pose convention, masks, or camera transforms disagree. Evaluate per-view depth and merged-world novel views as separate gates; the latter fails on blank renders, repeated silhouettes, radial copies, holes, or no parallax.
20. **Prefer a matching official CUDA wheel before JIT compilation.** For gsplat and similar extensions, resolve an official wheel against the exact Python, PyTorch, and CUDA tuple before allowing source JIT. Import the real backend to prove it loaded. If source build is required, set the target architecture and bound parallel jobs against RAM/swap; do not mistake a long cache/undistort message for GPU training while compiler children are active.
21. **Deliver the actual preview.** A generated GLB, a runtime-loaded GLB, and a user-visible route are different milestones. When asked to preview, verify/open the live route and explain exact keys/content; if the latest artifact is not wired, say so and provide a dedicated viewer before calling it previewable.
22. **Verify the requested content profile before capture.** In products with private-canonical and public/distributable modes, route labels and story data do not prove that the visible asset profile is correct. Before presenting a preview, record the active build mode/profile, resolve each promised hero by stable canonical ID through the live registry, inspect the rendered pixels, and reject any capture showing fallback, placeholder, proxy, or distributable stand-in assets. Never present a chronology-correct scene as the requested canonical game when the visible characters are substitutions. If a required external source is genuinely unavailable, report that blocker explicitly rather than substituting a fake preview.
23. **Send content-bearing visual updates only.** When the user asks for pictures while a 3D build runs, screenshots are evidence of visual progress only when they visibly contain the requested character, asset, scene, or an actively useful DCC work view. Error pages, empty viewers, source-ledger prompts, manifests, test output, and generic status screens are diagnostics—not progress pictures. Do not send them as the promised preview. State the blocker in text and wait for the first content-bearing frame; label WIP renders honestly.
24. **Do not invent a human dependency for from-scratch authoring.** If the user authorized original-from-scratch procedural or DCC modeling, external source pixels are optional study inputs rather than a mandatory build prerequisite unless the product contract explicitly says otherwise. Record provenance by hashing the textual design specification, authoring code, tool versions, seeds, Blender master, and exported derivatives. Keep official bytes out of Git and public builds, but continue reversible private-local authoring instead of generating an owner-source-required page.
25. **Build transforming mechanical characters from two locked endpoints and one shared component manifest.** Decompose both forms into stable-ID rigid pieces with explicit endpoint transforms, meaningful pivots, assembly ownership, and dependency links; choreograph overlapping structural phases, then drive pistons/sliders from the primary motion. Validate the manifest and timeline numerically, but promote only after dense sequential frames prove recognizable endpoint silhouettes, continuous assembly, and no floating or explosive mid-transition pieces. A high piece count and a green Blender validator prove mechanism structure, not film-faithful identity or production-ready animation. See `references/mechanical-transformation-production.md`.

See `references/equirect-cube-face-psv-viewer.md` for cube-face vs equirect stitch UV, inside-sphere LTR brand, living 4D spin-off defaults, and Vite base-path capture servers. See `references/cinematic-world-ui-integration.md` for the state-by-state visibility, UI-occlusion, integration-cadence, reference-boundary, and evidence checklist. See `references/first-use-frame-hitches.md` for the exact-runtime prewarm, long-frame attribution, transition-splitting, visibility-grouping, and repeated-certification playbook. See `references/production-threejs-renderer-foundations.md` for a capability-gated Three.js composer/PMREM/shadow foundation, deterministic tier contracts, truthful aggregate telemetry, and final-revision browser certification. See `references/quality-tier-performance-gauntlet.md` for Performance→Cinematic runtime knobs, smoke-versus-certification evidence, cross-hardware claim boundaries, and independent performance/visual review loops.

## Original image-to-procedural creature lane

When replacing sphere/capsule stacks from private visual study:

- retain only private-source paths and form-level observations; keep all copied pixels out of shipping;
- author a rights-cleared original concept before invoking image-to-3D tools;
- run the actual intake/spec/evaluator commands against that original input and retain command/output evidence;
- build one dominant changing-cross-section macro loft, with tapered appendages authored in socket-local coordinates and overlapping their body attachments;
- gate the result numerically with core topology/plane/thickness/volume-share metrics and primitive-sphere volume share;
- finish the repository's static, gameplay, build, shipping-boundary, deterministic-browser, diff, and commit lanes before calling the work complete.

Use `set -o pipefail` when piping pipeline commands through `tee`; otherwise a successful logger can hide a failed generator. Generated assessment/spec scaffolds prove tool invocation, not visual fidelity.

See `references/original-creature-img2threejs-lane.md` for the evidence layout, command shapes, procedural geometry patterns, anti-placeholder QA metrics, negative fixtures, and completion matrix.

## Canonical catalog character lane

When the explicit product policy uses known catalog characters rather than original designs:

- classify candidate systems before ranking them: novel-view generator, single-image 3D prior, true same-object multi-image reconstructor, geometry/representation refiner, texture system, and rigger are different layers and must not share one demo-quality leaderboard;
- record VRAM per stage—view generation, shape, reconstruction, texture, and combined app—and label whether each number is first-party documentation, an owner/maintainer issue reply, a merged contributor implementation, or a community report; a checkpoint minimum does not prove a Gradio stack fits when segmentation, encoders, VAE, controls, and texture models remain resident;
- distinguish a runnable local release from a paper, project page, hosted Studio/service label, or roadmap mention: require a public first-party checkpoint plus an inference path before ranking it in a local bakeoff; repository mentions of newer versions are discovery evidence, not proof that local weights exist;
- treat low-VRAM flags and merged offload PRs as candidate execution paths, not official hardware floors, unless first-party documentation publishes a measured peak on named hardware; model-file size is never a VRAM estimate;
- optimize low-VRAM 3D inference in measured stage order: geometry-only baseline → release inactive models and conditioning → shorten tensor lifetimes before external mesh kernels → isolate remesh/export and texture in fresh processes → tile/chunk decoder work → quantize only the weight-heavy modules proven to dominate. LoRA is domain-adaptation/training machinery, not a general inference-memory fix, because it does not remove activation, sparse-voxel, remeshing, or texture-bake peaks;
- accept a low-memory route only after fixed-input structural and visual QA. A sparse backend, dtype change, or quantized kernel may cut peak VRAM while silently shattering geometry, changing topology, or blanking textures; compare connected components, largest-component share, boundaries/nonmanifold edges, texture ranges, and render-back identity against the unoptimized control;
- extract camera contracts from source when necessary: projection, coordinate system, absolute/relative angles, elevation, distance/FOV or orthographic bounds, ordering, crop/occupancy, and internal angle offsets must accompany every promoted view pack;
- audit licenses recursively across code, weights, base checkpoints, adapters, and vendored components, including whether territory, revenue/MAU, noncommercial, or output-use clauses affect the derived asset; never infer deployability from the root badge alone;
- bind every presentation asset to the stable canonical ID and provenance record before modeling; for from-scratch procedural/DCC work, the record may identify hashed textual design specifications, authoring code, tool versions, and seeds rather than external source pixels;
- treat hero catalog characters as studio experiment programs, not one-shot generations: compare native high-resolution references, classical resize controls, neural super-resolution, temporal/multi-frame inputs, multiple generated-view seeds, and several reconstruction routes before promotion;
- fail preprocessing closed: verify executable plus model-package completeness, pass model roots explicitly, reject degenerate or duplicate outputs even after exit zero, retain failed masks as negative controls, and require a visual contact sheet before source promotion;
- isolate variables in two sweeps—hold 3D seed/settings constant while comparing source recipes, then hold the winning source fixed while varying generator settings—so a visually stronger candidate has attributable lineage;
- treat generated angles as hidden-side hypotheses requiring canonical landmark review; never average contradictory views into a false consensus;
- for offline diffusers novel-view runs with a custom pipeline, resolve both the model repo and custom-pipeline repo to exact local snapshot directories—`local_files_only` can still trigger custom-pipeline metadata lookup—and record portable repo IDs plus revisions rather than only cache paths;
- fail metered-provider economics closed before calibration: calculate affordable outputs against the intended catalog × camera roles × retries while preserving a reserve; if coverage is structurally inadequate, demote the provider to sparse benchmark probes, stop broad spend, and route production to a local/offline lane. Only then discover live schemas/pricing, calibrate one cheapest eligible still, record balance and request provenance, and expand within the approved reserve; a successful browser sign-in is not proof that OAuth tokens or MCP registration persisted;
- migrate one complete character slice at a time—identity, builder, sockets, clip profile, structural gate, and fixed-view recognition—rather than implementing an unverified roster horizontally;
- treat roster integration as one linked schema across canonical ID/type lists, immutable source profiles, colors, aliases, dedicated builders, exports, registry dispatch, clip profiles, factory routing, and fail-closed tests; a builder alone is not an integrated character;
- canonicalize aliases before builder/color/animation dispatch, and test the exact active registry keyset;
- in dirty integration worktrees, record inherited state before editing and keep a separate task-owned file ledger; never clean, reset, commit, or report unrelated pre-existing changes as your own;
- when a conservative sum-of-component-AABBs gate reports a cube-like model, sort per-component AABB contributions before editing; taper the dominant core and reduce redundant overlap while allowing only identity-meaningful extremities to establish bounds—never weaken the threshold or add arbitrary QA spikes;
- keep authored species scale on an inner visual group when animation restores the gameplay root transform;
- distinguish metadata/sprite APIs from actual 3D asset sources—an API record or artwork URL is not a rigged mesh;
- preserve a per-character presentation manifest for mesh/factory, scale, forward axis, ground contact, rig profile, materials, clips, and binary provenance;
- do not rename an unrelated procedural model and call it the canonical character;
- use canonical reference views to audit silhouette, anatomy, palette landmarks, proportions, and characteristic appendages at gameplay distance;
- run topology/thickness/volume QA and a separate rendered identity audit: numeric mesh health cannot prove recognizable likeness;
- expose stable IDs/source in runtime evidence and capture starter, exploration, and battle views with production UI enabled;
- treat the generated img2threejs factory as evidence/source, not automatically as the shipping module: inspect imported look-dev helpers, postprocessing, DOM texture synthesis, source bytes, and bundle delta first;
- when the raw factory is too heavy, distill its validated component/material spec into a compact runtime builder while preserving canonical IDs, source/factory hashes, pivots, part names, and QA coverage;
- track provenance per derived artifact when promoting a better source plate. Never globally rewrite PBR logs, crops, maps, or factory lineage to the new source unless those artifacts were actually regenerated; mixed-source evidence is valid when labeled honestly;
- reconcile late background-process notifications against the exact command, current driver revision, artifact timestamps, report parameters, and hashes before rerunning. A superseded failed invocation can coexist with a later verified artifact; never overwrite frozen evidence merely because notifications arrived out of order;
- after a rendered identity failure, revise the authoritative sculpt spec/component tree first, rerun strict validation and factory generation, then redistill the runtime builder and pin the new factory hash. A runtime-only shape fix leaves the evidence chain divergent;
- when repeated local patches improve details but the whole character still reads lumpy, tubular, fused, or proportionally wrong, stop patching and switch to an authoritative whole-mesh Blender pass. Preserve the latest validated asset as rollback, then work silhouette and proportions across all views, primary/secondary forms, facial planes and attachments, deformation topology, and only afterward surfacing. Require matched before/after turntables and wireframes; procedural reproducibility must not become an excuse to avoid professional manual DCC craft;
- assign one writer to shared source/spec/factory roots during parallel work. Integration/review lanes consume those artifacts read-only and own separate files or worktrees.

If project instructions conflict over canonical versus original identity, stop asset proliferation, recover the source-of-truth decision from the latest user direction and original project/session source, then align data, presentation, tests, and ship boundaries together.

See `references/canonical-character-reconstruction.md` for the contract, migration audit, spec-to-runtime distillation, and recognition gates. See `references/private-canonical-preview-gates.md` for the identity × asset-profile × scene-state acceptance matrix that prevents stand-in builds from being shown as canonical previews. For API-resolved artwork → strict ObjectSculptSpec → pass-gated generated factory work, follow `references/canonical-img2threejs-reconstruction.md`; it includes the private-pixel boundary, real extractor commands, multi-view blockout rejection loop, and procedural-only production gate. For studio-style native-vs-super-resolution source bake-offs, multi-seed generated-view hypotheses, explicit camera-role subsets, matched single/multi-view 3D sweeps, manual sculpt convergence, Pareto promotion, and labels-hidden N-way review, use `references/experimental-canonical-creature-studio.md`. For a scalable local ComfyUI source-hypothesis lane—including Python-environment isolation, verified node installation, full-residency model selection, subscription-versus-API boundaries, and fixed-settings downstream reconstruction—use `references/local-comfyui-reconstruction-sources.md`. For dated 12 GB model selection, a verified FLUX.2 Klein baseline, Qwen/JoyAI capability triage, matched camera-role bake-offs, and queue-bounded resource measurement, use `references/local-12gb-image-edit-model-selection.md` with `scripts/comfy_resource_monitor.py`. For recognizable humanoid/costume heroes that must converge from generated hypotheses through manual DCC craft, deformation, cloth/hair, PBR, glTF optimization, Three.js animation, and labels-hidden promotion, use `references/aaa-browser-character-production.md`. For OAuth-backed or otherwise metered image/video providers, follow `references/metered-generation-provider-control.md` for state-safe auth, schema discovery, portfolio-coverage economics, no-spend cost preflights, signed-media handling, and one-request calibration before spending credits. For scoped additions to an existing code-authored roster—including dirty-worktree discipline, the full data/alias/builder/export/clip/test matrix, component-AABB cube diagnostics, and exact completion reporting—use `references/canonical-procedural-roster-integration.md`. For the dated 12 GB multiview/image-to-3D/reconstruction landscape—including per-stage VRAM evidence, exact camera contracts, recursive license-chain risks, controllable blockout choices, and a canonical creature production lane—use `references/local-12gb-canonical-creature-3d-stack-2026-08.md`; re-verify volatile model and license claims before execution. For adapting oversized image-to-3D inference to consumer GPUs, use `references/low-vram-3d-inference-engineering.md` for peak attribution, stage/process separation, tensor-lifetime surgery, cautious quantization, and geometry-validity gates.

## Default architecture

```text
procedural/spec source
  -> interchange GLB
  -> Blender master (UV, rig, clips, LOD, bake, fracture)
  -> glTF/GLB export
  -> validation + geometry/animation compression + KTX2
  -> browser loader + animation contract + fixed-step physics
  -> deterministic visual/performance harness
```

## Numeric-gate checklist

Always return numbers for the chosen target rather than saying only “optimize” or “keep it low”:

- p95 CPU/GPU frame times at named resolutions and hardware tiers;
- LOD triangle counts and projected-height switch thresholds;
- total visible triangles, draw calls, shadowed lights, and shadow-map size;
- texture dimensions, compressed resident-memory budget, and initial transfer budget;
- deform-bone and influences-per-vertex caps;
- dynamic chunk/body count, convex-hull complexity, fixed timestep, and settle deadline;
- root-motion final translation/yaw error;
- marker timing tolerance and loop seam error;
- glTF validator errors, required-node/clip coverage, visual-regression thresholds.

Treat recommendations as project gates, not universal limits. Label the hardware and scene assumptions that make each number meaningful.

## Pitfalls

- Do not apply distance-only LOD to cinematics; projected screen size is the meaningful variable.
- Do not claim Blender physics, arbitrary shader animation, or event markers automatically survive glTF export.
- Do not dynamically fracture a moving skinned mesh unless a canonical pose/snapshot and collider-generation strategy are defined.
- Do not create one unique uncompressed 4K material set per asset without calculating full mip-chain GPU memory.
- Do not bury a failed critical feature inside an average visual score.
- Do not send a blocker page, empty viewport, test console, or manifest as the visual update promised to a user; diagnostics belong in concise text, while pictures must show the requested subject or meaningful DCC work.
- Do not cite tool support from memory when authoritative current docs or source are reachable.
- Do not treat a catalog/API integration as visual identity proof: metadata and sprites do not supply a production-ready 3D model, and relabeling an unrelated mesh is not reconstruction.
- Do not modify project files when the user requested research-only output; use temporary retrieval locations and explicitly verify project scope.
- After adding a second full character + dual energy PointLights + soft shadows, expect ~10 FPS if settings are uncapped — ship live Performance/Balanced/Cinematic presets that cut shadows, blade lights, PR×scale, and `maxSimSteps` (see `references/quality-tier-performance-gauntlet.md` Three.js sink table once present; until then: shadows off / blade lights off / PR≤1×0.85 / maxSimSteps≤2 is the known recovery pack).
- Never HSL-tint additive `MeshBasicMaterial` blades when cloning a guard for a dummy — causes `refreshUniformsCommon` pageerrors.
- Retarget a lid hinge only after evaluating the **closed** rest pose. Moving the pivot while rest rotation is the old open angle leaves children in world-open space and the lid flies.
- Changing hinge **axis** does not convert a clamshell mesh into a book. Screen interiors, hinge barrels, and leaf splits stay authored for the old axis; inspect closed/mid/open stills before calling it a book open.
- On Blender 5.x layered actions, fcurves live at `action.layers[0].strips[0].channelbags[0].fcurves`, not `action.fcurves`.

## References

- See `references/concrete-chess-web-pipeline.md` for a worked concrete-statue/chess pipeline with archetype rigs, fracture strategy, animation contracts, 4K budgets, and test gates.
- See `references/original-creature-img2threejs-lane.md` for rights-cleared concept intake, real img2threejs evidence, continuous-loft creature construction, anti-sphere-stack QA, and completion gates.
- See `references/cinematic-world-ui-integration.md` for live-state visibility checks, non-obscuring UI composition, thin-slice integration cadence, private-reference boundaries, and browser evidence packets.
- See `references/first-use-frame-hitches.md` for diagnosing and eliminating first-transition hitches with exact-runtime prewarming, hidden boot draws, semantic long-frame attribution, grouped visibility, and clean-host repeated profiling.
- See `references/production-threejs-renderer-foundations.md` for deterministic medium/high/ultra tier resolution, color-correct composer ordering, PMREM lifecycle, stable shadows, software-renderer fallback, aggregate `renderer.info` telemetry, and final-revision browser evidence.
- See `references/quality-tier-performance-gauntlet.md` for a four-tier runtime contract, deterministic workload matrix, sustained real-GPU evidence, fail-closed baselines, cross-hardware honesty, separate performance/visual reviewers, and Three.js vertical-slice FPS sinks (dual characters, blade lights, soft shadows, sim catch-up).
- See `references/equirect-cube-face-psv-viewer.md` for photosphere cube-face/equirect viewer orientation, LTR neon, dual-path Sphere/Immersive demos, and host capture base-path serving.
- See `references/local-12gb-image-edit-model-selection.md` for dated 12 GB image-editor selection, empirically measured ComfyUI feasibility, matched camera-role bake-offs, and the `scripts/comfy_resource_monitor.py` measurement probe.
- See `references/metered-generation-provider-control.md` for state-safe OAuth/MCP setup, schema-first discovery, one-request credit calibration, provenance, and matched downstream source evaluation.
- See `references/canonical-procedural-roster-integration.md` for scoped canonical roster additions, immutable metadata and alias coverage, procedural recognition contracts, component-AABB cube diagnostics, dirty-worktree file ledgers, and exact final reporting.
- See `references/aaa-browser-character-production.md` for the full humanoid/costume hero lane: generated blockouts, DCC sculpt convergence, deformation topology, UV/PBR, hair/cloth, rig/skin/animation, collisions, LOD/KTX2/glTF, Three.js integration, 12 GB responsibility splits, and labels-hidden promotion gates.
- See `references/reconstruction-source-bakeoff-preview-gates.md` for byte-verified source ledgers, hash-bound same-design multiview, measured local-model bakeoffs, and the generated-vs-wired-vs-visible preview contract.
- See `references/generated-mesh-convergence.md` for asset-class routing, reject-before-repair QA, precision-prop reconstruction, geometry-vs-surfacing separation, fine-tuning order, and concise evidence-led iteration updates.
- See `references/local-explicit-world-prototype-recovery.md` for the verified gsplat wheel-selection pattern, runtime-state diagnostics, and the separate per-view-depth versus merged-world visual gate.
