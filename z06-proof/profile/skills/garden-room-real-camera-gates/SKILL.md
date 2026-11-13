---
name: garden-room-real-camera-gates
description: Use when changing Garden Room photoreal Real views.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [garden-room, threejs, gaussian-splatting, camera, calibration]
    related_skills: [garden-room-core-planner, chatgpt-image-generation, threejs-real-gpu-receipts]
---

# Garden Room Real camera gates

## When to Use

Use when implementing or qualifying exact-camera generated views, depth capture,
SHARP alignment, Spark fusion/playback, or viewpoint cache invalidation in Garden Room.

## Procedure

- Treat `docs/REAL.md` in the Garden Room repository as the implementation/evidence map. The camera default is a deterministic procedural-depth Gaussian shell with no learned lift weights; SHARP requires explicit `GARDEN_REAL_BACKEND=sharp-research`, and the local preview is research-only opt-in. Keep the experience a bounded photo/parallax prototype: SHARP AMLR weights explicitly exclude product development, and the SD2.1 depth ControlNet model card has unclear production rights.
- Freeze the actual owner plan into the artifact directory before generating. Use that immutable fixture through localStorage while routing GET `/api/state` to `{}` and intercepting writes. Assert both camera matrices AND layout equality before reusing an HQ image with recaptured depth. Other agents or the owner can change the plan during a run; do not overwrite their new bytes or silently mix old images with new geometry.
- A custom depth/ID shader must multiply `instanceMatrix` for `InstancedMesh`, respect alpha tests/maps and sidedness, and hide non-procedural roots. Missing instancing produces giant invisible sheets that look like a calibration failure. Zen/care sprites outside the procedural roots can encode nonsensical metres when drawn with their ordinary material into a packed-depth pass.
- Prove the depth pass with an instanced cube whose front face is a known camera-Z distance, and an unrelated foreground overlay that must not contaminate it. Preserve the actual camera FOV/aspect; do not replace them with rounded capture dimensions.
- Run SHARP at known capture intrinsics. Use robust positive depth scale/shift fitting, refine only the RANSAC consensus, and report outliers as well as the median. A Huber fit over all samples still collapses under high-leverage background depths. Exclude the flat procedural window proxy from fitting to generated outdoor trees.
- Transform Gaussian covariances/quaternions along with centres. Record any procedural depth anchoring separately; a post-anchor residual is not independent reconstruction accuracy. Keep rejected fits out of scene manifests.
- Low-step SD-Turbo plus a depth ControlNet is not automatically faithful. High img2img strength can replace plants with chairs/railings. Inspect the exact preview images, not just whether the pipeline returned pixels; a foliage-colour guard does not certify counts, species or furniture identity.
- Separate model inference, cold loading, GPU queue, worker startup and download/decode timings. A warm subsecond preview does not clear a cold two-second target. Do not label a desktop RTX phone-viewport trace as physical Samsung performance or loopback transfer as Tailscale transfer.
- Bind fusion artifact names to their content, not merely source view IDs; recalibration changes bytes without changing those IDs. Cap Gaussians and render DPR explicitly. In novel-view tests assert image overlay opacity zero and procedural roots hidden before capturing actual live Spark frames.
- Guard live image-generation tests behind explicit opt-in and state a subscription-turn budget. Normal test sweeps must not spend image turns. Prefer cached `--views-only` evidence for rendered regression.
- Preserve early failures and final evidence separately. If the owner changes the plan after qualification, report the qualified snapshot hash and the later owner hash; never claim prior splats qualify a new revision.
- Isolate geometry/playback comparisons with `tools/replay_real_shell.py BEFORE AFTER`, then `REAL_STAGE=after REAL_OUT=AFTER node tests/real_visual.mjs --cached`. This reuses all six HQ images without new image turns or owner-job writes. Score both cohorts with `tools/score_real_visual.py`; cached replay's millisecond `hqElapsedMs` is receipt reuse, not image generation latency.
- Keep the pinned photo and raw Spark captures separate: pinned SSIM 1/LPIPS 0 only proves overlay integrity. Force overlay off and procedural roots hidden for raw diagnostic captures, and report worsening large offsets rather than averaging them away.
- Report shell depth residual as procedural-prior consistency, not recovered accuracy. Project centres with exact aspect/FOV and pixel-centre raster conventions (floor projected n+.5 coordinates); rounding can halve coverage and fabricate millimetre-to-centimetre residuals at silhouettes.
- Treat 5°/15°/30° plus 0.3 m diagnostic offsets as boundary/outside-validity stress tests when production requires distance <0.3 m and angle <15°. Do not present forced diagnostic visibility as supported navigation or a phone benchmark.
