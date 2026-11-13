---
name: blender-reference-derived-relief
description: Use when deriving relief from reference images.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [blender, relief, depth, verification]
    related_skills: [blender-reference-match-loop, comfy-da3-producer-gate]
---

# Reference-derived relief qualification

## When to Use
Use for reference-derived depth or inverse-shading geometry experiments, especially when anatomy must be evaluated independently of ink/material changes.

## Controls
- Freeze camera transform/lens, UVs, ink graph, lights, growth, and unrelated objects. Keep a fixed-ink control distinct from the original-scene control.
- Treat monocular depth as relative inference, not recovered metric anatomy. Save raw float arrays, confidence, model/input hashes, and normalization receipts. Label super-resolution as inferred detail.
- If ComfyUI HTTP is unavailable, inspect installed model-node code before invoking its implementation directly. Use explicit CPU mode and bounded threads; do not implicitly download models or disturb another session's service.

## Geometry portfolio
- Register reference crops through the actual camera projection. Displace existing front vertices along camera rays and measure screen-space drift.
- Remove arbitrary camera-plane trend from relative depth before mapping it to bounded relief. Use zero-boundary masks and preserve unobserved/attachment regions.
- Compare native depth, descreened/upscaled-input depth, a large-plane hybrid retaining existing detail, and a luminance wildcard against a real-render inverse-shading family.
- Feed each inverse-shading update the preceding actual render. Bound and regularize updates; describe a linear light-slope approximation honestly rather than claiming a differentiable physical optimizer.
- Reject lower RMSE when it produces nasal lumps, inflated eyes, doubled cheeks, or pigment-shaped geometry. Shaded drawings do not uniquely determine geometry.

## Verification and judgement
- Make application import-inert and idempotent. Restore frozen source geometry before applying a variant; stabilize owned datablock names. Test twice in memory and after reopening the delivered scene.
- Compare normalized digests after save/reopen: JSON tuple-to-list conversion can falsely fail direct structure equality. Write substantive differences rather than suppressing them.
- Require identical ink graph, UVs, topology, smoothing, and protected scene state across geometry conditions. Snapshot application code and displacement hashes at execution time.
- Treat template matches as correspondence proxies. Mark low correlation and search-boundary hits unreliable; never report recovery of an anatomical point outside the source frame.
- Render LOOK/CLEAR pairs and actual master-density border crops. Record canvas, crop, dimensions, device, samples, seed, and hash. Crops are not whole gigapixel renders or whole-face fidelity passes.
- Use fresh blinded side-swapped reviewers with owner preferences and phone/native/deep/full evidence. Both choosing the same display side after a swap is an underlying split, not consensus.
- CPU/GPU renders may differ through sampling and indirect shading. Use state invariants for ownership; pixel deltas are diagnostic. Byte equality applies to copies of the same render.
- Label the least-destructive experiment HOLD when identity remains unresolved; preserve production pointers.

## Evidence hygiene
- Register local JSON schemas under their declared IDs to prevent accidental network resolution. Do not repair foreign event records silently; use explicitly scoped archives for lane diagnostics.
- Record unavailable host-focus observations as null, not success from `None == None`. Prefer an owned headless profile with display variables removed for local review QA.
