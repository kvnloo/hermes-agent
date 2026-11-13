---
name: comparative-visual-build-audits
description: Use when auditing visual builds against target evidence.
version: 1.6.2
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [visual-qa, ui, cinematics, games, threejs, evidence, critique]
    related_skills: [dogfood, adversarial-ux-test, multi-agent-release-readiness]
---

# Comparative Visual Build Audits

Use this skill for evidence-driven criticism of an integrated visual build: game worlds, cinematics, interactive 3D, motion-heavy product UI, or other presentation work that must be compared with prior captures and a target reference bar.

The job is not to reward effort. It is to determine whether the candidate improved, whether it meets the target, why it misses, and which exact changes have the highest expected visual value.

## Core Rules

1. **Candidate-vs-prior and candidate-vs-target are separate questions.** A build can decisively beat a weak baseline and still fail the target bar.
2. **Technical green is not visual green.** E2E checks, latency budgets, console cleanliness, non-black frames, and state persistence establish functionality, not composition or cinematic quality.
3. **Transitions require motion evidence.** Do not infer camera continuity, locomotion weight, anticipation, impact, or payoff from a settled still.
4. **Inspect the active integration source.** A visible problem may be structural, timing-related, or caused by dead/unwired presentation code. Verify which module is actually called.
5. **Compare craft principles, not protected asset identity.** Use external/private references for hierarchy, value, depth, pacing, staging, and motion grammar. Never recommend copying pixels, characters, or proprietary designs. When Kevin asks to copy a **live demo URL**, lock the **technique the page actually uses** (inspect network + shaders + renderer, not a tweet caption). Do not retarget GOAL.md to a different paper because it looks similar (volumetric LUTs vs Gaussian splat LOD). A substitute that matches sky color still fails the copy request.
6. **Honor read-only scope.** If asked only to inspect and return a verdict, do not create contact sheets, reports, patches, or repository artifacts.
7. **Be direct when strictness is requested.** No courtesy credit, hedged pass, or praise padding before the verdict.
8. **Quarantine origin in blind A/B judging.** In an anonymous or allowlisted jury, this rule overrides the normal source-inspection and candidate/reference cross-check steps. Inspect only the explicitly permitted neutral evidence; do not read source, history, parent folders, provenance maps, or neighboring runs. Use only the visible labels A and B; do not name or infer source, identity, expected winner, baseline, candidate, or reference. Freeze and hash the neutral pack before dispatch, never regenerate it while judges are in flight, and unblind panel-by-panel only after ballots are final. Keep absolute scores invariant when the same artifact recurs, unless the crop or surrounding evidence materially changes what can be judged. Verify scoped session tool traces and successful image-load results before accepting a ballot; a process exit or self-reported evidence list is insufficient. Disclose process separation versus OS sandboxing, check residual MCP/profile capability exposure, and never promote dense still inspection to real-time playback acceptance. Validate actual manifest/ballot field names and independently assert expected lane counts so a mismatched folder glob cannot yield a vacuous green result.
9. **Preserve motion evidence in read-only fallbacks.** If direct video analysis is unavailable but the browser decodes the clip, inspect deterministic timestamped frames through ephemeral in-page canvas filmstrips. Otherwise extract frames to `/tmp` only. Cover the full duration plus side-isolated close-ups, and remove every temporary artifact when finished.
10. **Treat panel letters as local unless stable mapping is explicit.** Aggregate votes and scores within each stable-mapped set. Cross-set A/B totals must be labeled as raw letter counts and must never be translated into an underlying-source verdict.
11. **Preserve evidence when composing neutral panels.** Default to aspect-preserving contain/letterbox layouts, verify every expected row/view survives composition, and version rather than overwrite a frozen pack when a layout defect is found. A square crop that silently removes a turntable row invalidates the ballot.
12. **Enlarge anonymous still grids without creating evidence artifacts.** Analyze the authorized original first; if fit-to-window presentation is too small, enlarge deterministic source rectangles from that same image in an ephemeral in-page canvas. Preserve label/view indexing, never save the crops during a read-only jury, and distinguish geometric continuity from an appendage whose anatomical role changes across views.
13. **Identity vs samples for owned-product photoreal.** Judge against the owner's photographs and confirmed SKUs, not manufacturer catalog cleanliness. Huge Cycles resolution and visible microdetail do not pass if layout, furniture, cables, or product IDs do not match. Catalog images support SKU identity only after the SKU is confirmed; they never prove the owner's scene. Public photoreal stills of third-party IP are look-dev for craft principles only—never copy meshes or characters.
14. **Multi-scale still critique: full frame is mandatory; tiles are supplemental.** Never judge a still from crops alone. Run coarse-to-fine on matching poster/candidate pairs: (1) full frame for composition, value, pose, and silhouette; (2) halves or quadrants for region hierarchy; (3) small matching tiles (~1/20 or a salvage bbox) for stone, type, fingers, contact. A tile FAIL cannot override a full-frame FAIL on layout/pose; a tile PASS cannot certify the whole still. See `references/multi-scale-still-critique.md`.

See `references/blind-ab-motion-jury.md` for a reusable neutral-panel and side-by-side-video protocol, including the multi-panel **ballots-only JSON envelope**, sealed-map quarantine, absolute theatrical floor scoring, and combat/route defect vocabulary. For tested FFmpeg recipes covering 6 fps full-duration overviews, vertical A/B half-strips for vision models, separately listed A/B clip synchronization, full-resolution subject crops, source-frame-rate ambiguity windows, timestamp preservation, and cleanup, use `references/ffmpeg-blind-motion-contact-sheets.md`. For anonymous canonical-creature turntables, exact view-index defect citations, semantic-versus-geometric consistency, non-dominated ranking, and no-artifact enlargement, use `references/blind-turntable-anatomy-juries.md`.

## Evidence Matrix

Before judging, inventory the available evidence:

| Evidence | What it can prove |
|---|---|
| Candidate stills at a named viewport | Composition, value hierarchy, silhouettes, UI overlap, text legibility |
| Prior stills at the same viewport | Direction and magnitude of visual improvement |
| Motion/video | Cuts, camera continuity, locomotion, parallax, event timing and payoff |
| Target/reference frames | High-level craft principles and target bar |
| Active rendering/presentation source | Structural causes, timing windows, active vs dead systems |
| Verification reports | Functional state, performance, latency, capture honesty |

If the viewport differs, call that out before making direct scale or legibility comparisons.

## Revision and Evidence Integrity

Before treating archived screenshots, traces, reports, audio telemetry, or profiles as current-product proof:

1. Distinguish the **captured revision**, **current live candidate**, and **ship artifact**; issue separate verdicts when they differ.
2. Record commit/branch, tracked and untracked state, evidence/source/harness timestamps, and a served-runtime or build fingerprint. Recheck them before finalizing.
3. If HEAD, dirty state, or the served runtime changes during review, classify the target as moving. Scope old evidence to its captured revision and require a frozen rerun for current certification.
4. Audit every harness-side browser evaluation and exposed global. Do not trust hard-coded integrity flags or unconditional passing checks.
5. Say whether a run was trusted-input driven, telemetry-guided, outcome-controlled, or state-mutated; these are different evidence strengths.
6. Treat audio scheduler state as integration proof, not audible-output proof, and reconcile documented performance thresholds with executable gates and field semantics.
7. If HMR, a reload, or a served-script fingerprint change occurs during a sequence, stop that sequence and scope every earlier frame to the old fingerprint. Re-establish the current runtime with a clean load before continuing; never mix pre- and post-reload frames into one motion or score claim, and do not promote a transient hot-reload crash into a stable-product verdict without reproducing it on the clean load.
8. Reconcile visible destination/arena promises with gameplay ownership: compare presentation coordinates to traversable bounds, collision solids, interaction radii, and an input-driven runtime position. A beautifully framed threshold beyond the player clamp is an unreachable set extension, not route clarity.
9. Sanity-check WebGL metrics against visible complexity and the post stack. With composers or automatic renderer-info resets, a final full-screen pass can make `calls` or `triangles` describe only the compositor rather than the 3D scene; require pass-aware sampling or an explicitly accumulated scene interval before using those counters as performance evidence.

Use `references/product-evidence-integrity.md` for the detailed revision ledger, harness classification, claim/evidence matrix, audio checks, performance consistency checks, and fail-closed verdict language. Use `references/live-interactive-runtime-audits.md` for sustained-input capture, moving-target recovery, reachability reconciliation, and post-processing counter sanity checks.

## Workflow

### 1. Lock scope and constraints

- Record the candidate folders/files, prior evidence, reference corpus, source areas, viewport, and requested tone.
- Note whether the audit is read-only.
- Do not widen into mechanics, code architecture, or asset provenance unless those directly explain presentation quality.

### 2. Inspect candidate frames by scene role

For each frame, identify:

- primary focal subject;
- foreground, midground, and background planes;
- dominant value/color path;
- silhouette and eyeline readability;
- landmarks and route/destination logic;
- repeated geometry or procedural pattern exposure;
- contact grounding and material response;
- UI-safe regions, overlaps, contrast, and minimum text size;
- what the frame communicates with all explanatory text mentally removed.

Record concrete screen-position evidence rather than adjectives alone.

### 3. Compare prior evidence

When Kevin requests every visual iteration, deliver the actual chronological image gallery, not selected examples or a prose progress report. Inventory saved revisions first into a machine-readable manifest; retain a row for rejected, duplicate, partial and unavailable versions. Record source geometry, author/harness, capture conditions and render path; reconcile rendered plus explicitly missing entries against the discovered inventory in code. Separate whole subjects, isolated part studies and incomplete integrations so a local pass cannot masquerade as a finished model.

For a straight-on facial comparison, use a camera at face height looking directly toward the nose, with consistent framing, lighting and material across versions. Inspect native images to verify orientation rather than trusting a filename containing 'front'. Compare against a genuinely frontal reference; label near-front, open-mouth, pose and style mismatches. Generated supplemental part studies may guide design but must remain labeled interpretations, never canonical evidence of unseen anatomy. Render saved geometry without repairing it for the gallery; mark inaccessible versions rather than substituting the newest mesh. Supply zoomable images/contact sheets and a working local gallery, inspect the output, and state coverage gaps before claiming completeness.

Use the same rubric and viewport. State explicitly:

- what materially improved;
- what merely became more populated;
- which weaknesses survived unchanged;
- whether the improvement comes from a low baseline rather than target-level execution.

### 4. Extract principles from target references

Group target evidence by craft class:

- world/route composition;
- twilight or GI/value grouping;
- action staging and VFX direction;
- emotional close-ups or ceremonies;
- HUD-safe negative space.

Translate each into original-build principles such as asymmetric framing, layered occlusion, localized warm rim over cool shadow fields, anticipation-contact-recoil, or a single readable face. Do not ask the candidate to mimic protected content.

### 4a. Build a cross-generation benchmark ladder

When the target deliberately spans eras or media, assign each comparator one job before scoring:

- legacy interactive reference = motion, staging, impact, and event-audio floor;
- latest shipped franchise title = current production bar the candidate must visibly beat;
- modern real-time reference and technical documentation = geometry, materials, lighting, animation, audio, and performance outcomes;
- cinematic or 2D reference = composition, acting, value grouping, escalation, and aftermath only.

Verify title currency and release claims from first-party sources. Extract exact timestamps with a coarse-to-dense footage pass, and label every source limitation: an upscaled legacy capture cannot establish native texture fidelity, an edited trailer cannot establish uninterrupted gameplay or performance, and an offline cinematic cannot establish real-time feasibility. Treat engine features as outcome references rather than implementation mandates.

Convert each observation into a transferable principle, a numeric or observable exit condition, and the exact evidence class required—still, uninterrupted motion, telemetry, or audible output. Bound superiority claims to the tested corpus; “better than every released title” requires an exhaustive role-matched corpus and cannot be inferred from one legacy and one current comparator.

See `references/cross-generation-visual-benchmark-research.md` for the timestamp workflow, source caveats, evidence matrix recipe, blind-preference gate, and a worked Pokémon source bank.

### 5. Inspect motion and transitions

Check:

- hard cuts versus motivated bridges;
- screen-position continuity across mode changes;
- camera match, easing, horizon stability, and yaw lag;
- locomotion synchronized to speed and foot plants;
- parallax across depth planes;
- action phases: anticipation, launch, apex, contact, recoil, settle;
- whether catch/heal/reward beats are visually authored or only text-confirmed;
- when HUD disappears and returns relative to the visual event.

If a local video is not accepted by a video-analysis path, use a read-only fallback: open the file in the browser, inspect `video.duration`, pause, set `video.currentTime` to deterministic timestamps, and capture key frames. For gait, turns, or settling, prefer ephemeral timestamped canvas filmstrips in the page DOM: sample event-specific windows at equal intervals, retain terrain markers around the feet, and compare candidate/baseline with the same crop and cadence. This is a fallback pattern, not a permanent claim that any tool is broken. See `references/browser-ephemeral-video-filmstrips.md` for the DOM-only recipe, prompts, interpretation safeguards, and cleanup rules.

#### Matched regression triangulation

For candidate-versus-prior regression claims, do not let a full-video summary stand alone:

- use summaries to locate intervals, then inspect contact sheets and directly seek both actual videos at matched timestamps or matched gameplay phases;
- privilege directly inspected pixels when a summary and contact sheet disagree, without converting one disagreement into a permanent negative claim about the tool;
- score hard occlusion, silhouette crowding, camera stability, route look-ahead, landmark continuity, and avatar self-occlusion separately;
- distinguish certified runtime state from visible communication—a report can prove success while the named frame still fails to show it;
- timestamp blockers and give observable exit conditions, such as preserving one route edge and one landmark through turn onset and camera settle.

See `references/matched-motion-and-visible-state-verification.md` for the complete matched-video and functional-state-versus-visible-state protocol.

### 5a. Build an authored cinematic evidence contract

When the task includes implementation—not only criticism—turn the desired motion grammar into a fail-closed contract before wiring the active flow:

- keep phase timings and the elapsed-time phase resolver in the production presentation module, then import them into tests;
- assert perceptual timing ranges and phase relationships rather than maintaining a test-only timing mirror;
- expose read-only runtime phase, attacker, target, sequence, payoff, and projected subject rectangles for temporal browser evidence;
- capture anticipation through settle and HUD return from one uninterrupted sequence; a pack stitched from different attackers, targets, or encounters cannot prove causal continuity;
- prove directional effect creation and cleanup cheaply, then prove scale, occlusion, HUD safety, and phase order in the real browser;
- rerun canonical typecheck after the final call-site integration, not merely after defining the contract;
- stop expanding scope if verification/commit budget is at risk—the artifact is incomplete until the final runtime gate and commit exist.

See `references/authored-cinematic-evidence-contracts.md` for the TDD sequence, same-action phase-pack rule, rendered-channel and true-hit-stop audits, flash-washout measurements, Three.js effect probe, 3D-to-screen HUD overlap method, runtime snapshot shape, and completion gate.

### 5b. Build an authored world-structure contract

When implementation replaces procedural-looking world repetition, make authored intent both executable and visually auditable:

- define one production blueprint for route control points, irregular terrain masses, foliage cluster envelopes/silhouettes, destination opening, and lighting strategy;
- write a failing deterministic gate against that production blueprint before rendering changes;
- assert meaningful route reversals, endpoint-to-threshold alignment, non-concentric terrain centroids and contour variety, asymmetric foliage footprints, gameplay-zone compatibility, and bounded passive emissive fill;
- preserve collision and encounter ownership in gameplay modules—presentation data must align with those coordinates rather than quietly redefining mechanics;
- capture spawn, mid-route, and destination approach at the shipping viewport, because data-level asymmetry can still collapse into bilateral walls and mathematical bends can still look straight;
- after structural green, inspect for faceted terrain seams, cable-like continuous borders, merged foliage strips, crushed cool shadows, and landmarks that provide direction but no readable arrival;
- establish a completion lock before browser iteration: use the minimum role-complete frame set and one final production preview, then protect enough execution budget for all requested gates, owned-diff review, commit, and post-commit status;
- rerun the structural gate and canonical build/profile suite after the final pixel-driven refinement.

See `references/authored-world-structure-gates.md` for the blueprint schema, TDD slices, deterministic invariants, Three.js rendering techniques, pixel-level failure modes, bounded-run completion lock, and frozen verification loop.

### 5c. Build an authored creature-and-locomotion contract

When a critic identifies primitive anatomy and root-motion puppet behavior, treat construction, rigging, gait state, and evidence as one integrated upgrade:

- translate each visual blocker into an executable mesh or motion invariant before production edits;
- preserve the shell's ownership of world placement and existing clip APIs, while deriving gait only from observed root XZ displacement and frame delta;
- model contact, down, passing, and up explicitly, couple phase to distance/stride, and compensate stance feet in local space so support is testable rather than implied;
- build semantic pivots for shoulders/hips, intermediate joints, paws, spine, neck/head, ears/tail, and species-specific appendages; idle must not advance grounded feet;
- gate primitive assembly across all obvious analytic families, not spheres alone, and pair volume metrics with semantic socket/joint, face-plane, wing-layer, and continuity checks;
- verify timestep invariance, teleport handling, speed/cadence response, turn counter-motion, attack/faint preservation, and planted-foot error numerically;
- capture honest integrated runtime motion on an isolated port plus fixed-side or dense source-frame-rate views that expose support and slip; rear follow-camera footage alone is insufficient;
- reserve the final execution budget for owned-diff review, commit, and a post-commit clean-revision browser rerun.

See `references/authored-creature-locomotion-contracts.md` for the gait math, two-link IK pattern, mesh-QA measurements, honest encounter capture, visual evidence protocol, and completion checkpoints.

### 5d. Build a cross-hardware quality-preset contract

When a real-time browser build needs Performance/Balanced/Quality/Cinematic-like tiers, treat preset labels, runtime selection, gameplay invariants, and release evidence as one fail-closed system:

- trace the active preset type, default, UI, renderer creation, DPR/buffer sizing, shadows, LODs, lights, simulation cadence, effects pools, responsive settings access, and diagnostics before proposing tier values;
- distinguish actual tier knobs from cosmetic labels, and flag renderer options such as default-framebuffer antialiasing that cannot vary after context creation without a different rendering path;
- specify `Auto` separately from manual overrides, benchmark the representative scene rather than trusting vendor strings, use hysteresis for resolution/tier changes, and never switch discrete quality during an authored contact sequence;
- define scalable channels separately from non-negotiable state, interaction, silhouette, attacker/victim, contact, camera, audio, HUD, aftermath, and accessibility invariants;
- publish target-specific frame budgets for normal 60–120 FPS and any intentionally lower Cinematic mode, plus first-use hitch, sustained thermal/load, memory-plateau, and real-hardware/resolution gates;
- compare every tier against its own prior baseline and all tiers side-by-side, recording actual drawing-buffer pixels and revision/harness fingerprints; authored-time motion cannot certify host FPS.

Use `references/cross-hardware-quality-preset-contracts.md` for the source-audit checklist, automatic/manual selection model, monotonic profile schema, frame-budget formula, cold-use and thermal protocol, visual regression matrix, and fail-closed ship verdict.

### 6. Cross-check active source

Search for the visible system and its call sites. High-value checks include:

- active world module versus orphaned alternate scenery;
- repeated primitive loops and small archetype sets;
- fixed camera bases or declared-but-unused camera controls;
- authored phase channels that are declared, reset, and assigned but never consumed by the production render tick;
- a claimed contact hit-stop while creature or camera animation clocks still advance unconditionally;
- generic radial particles where direction should matter;
- VFX lifetimes shorter than the evidence capture window;
- transition elements queried but absent from DOM or never invoked;
- event feedback implemented only as toast text, a scale bump, or an always-on ambient effect;
- animation clips driven by wall time instead of movement speed.

Use source evidence to distinguish:

- **capture miss:** a good event happened outside the selected frame;
- **timing weakness:** the event exists but is too brief or poorly sequenced;
- **structural weakness:** the system cannot produce the target staging.

### 7. Separate technical and artistic verdicts

Acknowledge technical evidence tersely, then keep it in its lane. Example:

> The transition meets its latency budget, but the visual change is still a hard cut with no authored bridge.

Do not inflate the visual score because the complete loop passed.

### 8. Score and rank

Use a 0–10 rubric appropriate to the build. For interactive 3D, default categories are:

- world composition/depth;
- route/destination clarity;
- terrain/foliage variety;
- lighting/GI/material response;
- emotional or starter ceremony;
- battle/action staging;
- VFX clarity;
- HUD hierarchy and viewport legibility;
- transitions and event payoff.

If computing a weighted total, use a calculation tool rather than mental arithmetic.

Rank blockers by how much fixing them changes the viewer's read, not by implementation ease or file count.

### 9. Prescribe exact high-EV fixes

Good fixes specify observable outcomes and timing/layout constraints, for example:

- hide combat menus during action;
- add a 100–140 ms anticipation, contact-tied hit-stop, directional origin-to-target trail, recoil, then settle before HUD returns;
- preserve a selected subject's screen position through a ceremony-to-chase transition;
- replace regular terrain rings with irregular masses and a visible destination entrance;
- move HUD out of subject silhouettes and bright sky regions;
- make healing visible through event-specific light, motion, and bar refill rather than a toast.

Avoid vague advice such as “add polish,” “make it cinematic,” or “use more particles.”

## Required Verdict Shape

When the user asks for a strict comparative verdict, lead with:

1. **Candidate beats prior?** Yes/no and one sentence why.
2. **Strict target-bar verdict:** PASS, FIX-FIRST, or FAIL.
3. **Overall score** plus rubric table.
4. **Concrete evidence** from candidate, prior, references, motion, and source.
5. **Ranked blockers.**
6. **Highest-EV exact fixes.**
7. **Read-only note:** files changed and any evidence limitations.

Use `templates/strict-visual-verdict.md` as a compact output scaffold.
For labels-hidden multi-panel motion juries that request ballots only, use `templates/labels-hidden-motion-ballot.json` and the envelope in `references/blind-ab-motion-jury.md`.

## Pitfalls

- Giving courtesy credit because the team produced a large diff.
- Calling a build target-quality because it is much better than an empty baseline.
- Treating passed automation as aesthetic certification.
- Treating a named phase interval as rendered behavior without tracing its pose/camera channels, or calling it hit-stop while clip time still advances.
- Accepting a phase pack stitched from different actions as proof of one causal motion sequence.
- Judging transitions from before/after stills only.
- Mistaking dead or duplicate source for the active implementation.
- Reporting generic opinions without screen-position or source evidence.
- Overfitting recommendations to protected reference assets.
- Shipping a look-alike renderer (Takram-style atmosphere LUTs, full `devicePixelRatio`) when the named reference is a different path (splat viewer, 75% res, phone LOD/touch). Viewport meta does not make that a mobile copy.
- Creating files during a read-only critic pass.
- Spending the report on process narration rather than the verdict.
- Opening `_sealed_maps` / secret provenance during a labels-hidden jury.
- Wrapping “ballots only” JSON in markdown fences, parent summaries, or identity guesses.
- Inflating impact scores for particle beams or HP text when body contact craft is absent.
- Feeding only combined half-res tiles to vision without side-isolated or vertical half-strips.
- Judging a robot/plinth still from crops only (Telegram critic protocol): skip full-frame and half-frame steps.
- Calling a huge still photoreal because tiles show grain or logos while the scene is a different room or a proxy SKU.

## Verification Before Finalizing

- Every requested frame and comparison set was inspected.
- Motion claims are backed by video or active timing/source evidence.
- Source claims identify active call sites or confirmed absence of wiring.
- Technical and visual outcomes are not conflated.
- The score matches the written severity.
- Fixes are ordered by expected visual impact.
- No repository artifacts were written under read-only scope.

See `references/3d-cinematics-ui-checklist.md` for a detailed scene-by-scene checklist.
Hermes Desktop Spatial vs get-spatial.com stills: `references/hermes-desktop-spatial-ui.md`.
