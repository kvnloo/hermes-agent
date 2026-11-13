---
name: comfy-da3-producer-gate
description: "Use when proving real ComfyUI DA3 evidence export."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [comfyui, depth, inference, evidence, provenance]
    related_skills: [upstream-contribution, github, systematic-debugging]
---

# Real ComfyUI DA3 producer gate

## When to Use

Use for real DA3 inference producer acceptance gates, bounded reconstruction-evidence bundles, or CPU/GPU provenance validation in ComfyUI.

## Scope

Prove an actual loopback ComfyUI API execution, not fabricated tensors, and leave consumer A/B parity as a separate gate. Preserve dirty install checkouts and all downstream commits. Do not post PR evidence while a consumer gate is held.

## Procedure

1. Locate repositories with depth-capped Git-remote discovery under supplied roots. Resolve relevant symlink roots explicitly. If missing, read a bounded existing project receipt for the actual install path instead of recursively scanning disks or immediately cloning.
2. Snapshot install status, refs, and every worktree. Read PR body, comments, reviews, review threads and entire diff. Fetch the current PR branch and default into fresh refs; detach a dedicated worktree at the exact head. Never reset the installed checkout.
3. Reuse installed PyTorch/CUDA packages. For missing test or current pinned runtime dependencies, make a separate venv with a `.pth` pointing to the installed ComfyUI venv's site-packages. Install only necessary overlay packages there; a venv made from another venv does not automatically inherit that venv's packages. Clear inherited PYTHONPATH/PYTHONHOME. Do not upgrade the live install's dependencies.
4. Inspect existing `geometry_estimation` paths first. If authorized and missing, use the official `Comfy-Org/Depth-Anything-3` model card/API, pin its revision, and retrieve `geometry_estimation/depth_anything_3_small.safetensors`. Stream into a partial file in the existing model directory and verify byte size plus official LFS SHA256 before renaming. Preserve model card, tree metadata and source URL receipts, excluding signed download query credentials.
5. Pin and download a public RGBA demo image. Record repository revision, path, SHA256 and provenance. A stylized/rendered demo must not be labelled a measured photograph. Preserve source bytes, not an invented segmentation fixture.
6. Launch the exact PR tree on loopback with explicit private input/output/user/temp paths, disable auto-launch/API nodes, disable all custom nodes except `reconstruction_evidence`, and use an extra-model-path YAML to reuse installed weights. Create the user directory first: CLI validation requires it to exist. Check readiness in a later call; startup can exceed tens of seconds. Never claim a GUI/display check from an API run.
7. Read `/object_info` for the real node schemas. Use `LoadImage` IMAGE -> `DA3Inference`, `LoadDA3Model` -> `DA3Inference`, `LoadImage` MASK -> `InvertMask` -> `ReconstructionEvidenceBundle`. LoadImage's mask is **one minus alpha**; invert exactly once to recover foreground alpha. The API dynamic combo uses `mode: "mono"`; resolution 504 is model process resolution while output returns to input dimensions. Specify dtype, reference state and filename-only model label explicitly.
8. Submit `/prompt`, retain exact request and `/history/<id>`, require completed success and empty execution-cached nodes. For stronger proof, use a read-only profile observer to capture actual `_run_da3` return device/dtype and raw exporter-input tensors. Never replace model outputs or add synthetic nodes. Record instrumentation separately from shipped code.
9. Validate manifest strict finite JSON, relative filenames, all artifact SHA256 values and equal dimensions. Read PNG IHDR to prove bit depth 16 and color type 0 for depth. Require exact source RGB and alpha-mask pixel parity; compare saved u16 depth against normalization of the **observed real raw** depth and verify sourceRange and monotonicity. Inspect PNG chunks for unwanted text metadata. Assert modelLabel contains only the filename and bundle contains no local paths, raw prompt literals or secrets.
10. Compare the workflow shape against the **executed hidden PROMPT**, not blindly against submitted JSON. ComfyUI adds `LoadImage.is_changed` fingerprint data during execution; the exporter hashes its redacted type shape. Record submitted workflow SHA separately and capture redacted executed shape. Do not patch product code merely to make a receipt's incorrect assumption pass.
11. Run focused exporter/path tests and the full unit suite. If broad tests fail, run the exact base in another detached worktree with the same environment and compare failure identities. Some model tests can pass alone but fail in whole-suite order; preserve both receipts and report baseline-red rather than broadening an unrelated exporter patch.
12. Restart the server for a second uncached run if reproducibility is requested. Compare raw/output byte hashes, keep first-run logs, and stop only the server this gate started before final hashing. Preserve separate first-run raw/output bytes when possible; if only its contemporaneous hash record survives, say final bytes were compared against that record rather than claiming independent access to both payload copies. Re-read remote branch/default heads with `git ls-remote` when API quota is exhausted. No code delta means no push.

## Receipts

Save a durable manifest pointer, exact workflow, source/model metadata, observed raw tensors, actual runtime/device evidence, source-file hashes, test XML/logs, base comparison, final remote-head readback, preserved install status and a scoped SHA256 file index. Calculate counts from receipts. State API-only execution, any older optional docs/templates warnings, baseline suite failures and consumer parity hold plainly.
