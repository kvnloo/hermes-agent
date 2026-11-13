---
name: blender-ai-projection-texture-paint
description: Use when baking AI camera images into Blender UV textures.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [blender, textures, udim, projection, ai]
    related_skills: [chatgpt-image-generation, blender-reference-match-loop]
---

# AI camera projection into real mesh textures

## When to Use
Use for headless multi-view image projection, AI texture-paint coupons, UV/UDIM resolution budgets and max-zoom evidence.

## Scope
Use AI images only where the owner permits actual UV/UDIM material textures. A camera-space image is an intermediate observation, never a finished-render paint-over. Preserve production scenes and conduct isolated coupons first.

## Procedure
1. Read the project's scoped owner preferences, source fixture and locked camera. Preserve source checksums. Load `chatgpt-image-generation` before using the subscription route; set a hard generation cap.
2. Separate **storage density**, **generated source density**, and **semantic fidelity**. A large upscaled texture does not prove new detail. Compute the UV-to-final-screen Jacobian per triangle, include UV stretch, and budget for the actual requested final canvas. A 201 MP canvas is not a 1 GP canvas.
3. Keep authored UVs when valid; clone a separate paint UV layer before scaling to UDIM space. Bind existing image nodes explicitly to their original UV layer so new active paint UVs cannot silently break the old shader.
4. Render real hero, close-up and off-axis conditioning: beauty, position, depth, normals and alpha. On Blender 5.2 set `image_settings.media_type='MULTI_LAYER_IMAGE'` before `file_format='OPEN_EXR_MULTILAYER'`. Read **all OpenEXR parts**: `OpenEXR.File(...).channels()` only returns the first part and can falsely suggest depth/normal passes are absent. Use 32-bit EXR for position precision.
5. Rasterize UV triangles into world position and face normal per tile. Cull triangles by UV bounds before entering the raster loop; scanning a million relief triangles with per-triangle temporary arrays for every UDIM is needlessly expensive. Process tiles sequentially to bound RAM.
6. Project world points with the exact view matrix and border coordinates. Reject occluded points by comparing the position buffer, reject rear-facing surfaces, feather view edges, and prefer higher-density observations. Record raw overlap disagreement; blending does not establish consistent anatomy or facet boundaries.
7. Treat generated illumination and new geometry-looking marks as failures. Retain procedural normal and roughness branches. Do not convert arbitrary RGB beauty into asserted PBR normal maps. For frequency-split vegetation, inspect the low band for surviving bead glows and coloured illumination before mapping it: low-pass filtering alone does not isolate plant albedo. Judge native geometry contrast after projection; emission-carrying colour can leave physically present fibres reading as sparse dark marks on smooth glowing bodies. More fibres is not a demonstrated repair for that shading failure.
8. Fill only bounded holes with clearly labelled interpolation; keep large unseen regions on the original material through alpha. Semantic UV inpainting across separate islands requires surface adjacency/position conditioning, not merely nearest UV pixels.
9. Save conventional `paint.<UDIM>.png` files and a real Blender `TILED` image node driven by the paint UV. Reopen the saved scene, verify mesh checksum and graph connections, and render native border crops at the full final canvas resolution plus held-out off-axis views.
10. Report native crops, texture/GPU cost, source-pixel coverage, seam/ghosting evidence and limitations separately. Scope single-view crop pixel-density formulas to cameras with matching projection; a different lens/off-axis camera needs its own surface differential for an exact density claim.

## Evidence
The Quackles prototype lives at `/mnt/zer0models/project-artifacts/quackles/process/ai-texture-paint/`. It is an experimental coupon, not production approval. Read its current REPORT and verification files before adopting results.

## Safety
Use the project's shared GPU lock and sanitized headless environment. Do not unload another worker's diffusion model or alter its Python environment. Install CPU projection helpers in a lane-owned venv. Persist checkpoints with source/config/image hashes before allowing cache reuse after inputs change.
