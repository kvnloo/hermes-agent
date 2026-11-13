---
name: render-cache-provenance
description: Use when caching render evidence. Reject stale lineage.
version: 0.1.0
platforms: [linux, macos, windows]
---

# Conservative render cache provenance

## When to use

Use for local render/asset caching, partial rebuild design, resumed frame evidence, or review invalidation. This is an integrity workflow, not a renderer implementation or proof of visual quality.

## Procedure

1. Read the existing producer, resume and review metadata paths with `read_file`; identify which dependencies are actually captured. Inspect bounded JSON sidecars before opening heavyweight artifacts. Label old hash values as quoted metadata unless bytes were reverified.
2. Separate asset-input, render-input and review-evidence identities. Domain-separate versioned canonical hashes; reject missing/unknown schema fields, unpinned values and nonfinite numbers. Preserve literal dependency identifiers; never silently normalize a malformed digest.
3. Include the transitive builder/helper/material/external-input closure, geometry parameters/seed/detail tier and pinned builder environment in asset keys. Treat materials as geometry-affecting until a pure rebinding contract is proven.
4. Include resolved camera, illumination, engine/build, sampling tier, render seed, color management, scope, frame, composition and device/driver settings in render keys. Include actual built-asset artifact digests so nondeterministic outputs cannot alias by input recipe alone.
5. Resolve shared A/B framing and illumination before reusing either side. A candidate-bound change can alter the baseline camera, floor and light power even when baseline geometry is unchanged.
6. Bind reviews to every exact image digest, semantic slot, rubric, reviewer/model/prompt and presentation mapping. A rubric-only change invalidates the review, not the pixels. Different bytes under the same render recipe also invalidate reviews.
7. Validate expected slots exactly once, complete status, source/render identity, immutable input snapshot and output byte integrity. Compare each intended baseline/candidate source against its own expected slot rather than requiring all sources to be identical.
8. Exercise rejection using tiny, explicitly labeled synthetic fixtures through the public validator. Cover stale helpers, wrong-source slots, duplicate/missing records, interrupted publication, source changes, payload corruption and obsolete review policy. Never call these fixture bytes render proof.
9. Keep source snapshots immutable; matching start/end hashes alone cannot detect mutations that revert in between. Publish a completed receipt atomically after output validation, under existing job ownership/locking.
10. Prefer verified selected-frame resume and rereviewing stored images, then owned-asset checkpoints. Use existing local directories and queues before adding remote stores or services. Do not attribute earlier persistent-render-data or scene-scoping savings to a new cache without matched measurements.

## Pitfalls

- Hash Blender `Image.pixels` through `foreach_get` into a float32 buffer instead of retaining Python float lists for every texture; generic writable-RNA serialization can silently allocate gigabytes and duplicate them during JSON encoding. Hash the entire buffer and preserve packed bytes/settings separately; do not sample or cache across mutation snapshots.
- Profile saved-scene verification with bounded stage timings and timed stack dumps before retrying a long timeout; distinguish diagnostic faulthandler “Timeout” dumps from the scheduler's actual job outcome.
- Admit preserved modifier stacks according to the owned operation, not a blanket raw-mesh gate: a local thickness modifier may remain intact under translation, while visibility-only retirement does not require baking subdivision. Keep exact source-stack equality and before/after component signatures mandatory.
- A seed and key describe declared inputs; neither proves geometric reproducibility. Measure topology, transforms, bindings and vertex tolerances in independently rebuilt assets when that claim matters.
- Share a Cycles sample set between LOOK and CLEAR only after proving both optics paths have identical physical camera/radiometry and CLEAR is raw RenderLayers output. Bind the exact compositor/helper closure, compare a raw File Output against a separately rendered CLEAR at identical seed/settings, and retain the actual pixel-equality receipt before reusing the paired-output route. This proves that fixture's output equivalence, not general optical equivalence or artistic quality.
- A stored image digest identifies exact bytes, not cross-hardware pixel determinism. Partition conservatively by runtime/device; even equal fingerprints are not a determinism theorem.
- Unknown dependency closure means a cache miss. A nonempty generic descriptor is not proof that all effective Blender settings were captured.
- Do not upgrade incomplete historical provenance by hashing current sources; preserve old evidence under its original scope.
- Trusted local receipts provide consistency, not authentication against someone who can rewrite both metadata and artifacts.
- Do not scan or hash an entire large corpus for each request. Reuse original digest receipts only under an explicit immutable-artifact policy; mutable or untrusted restored files need bounded admission verification.
- For a read-only saved-version inventory, prune dependencies/environments before recursive enumeration, retain backups and negative fixtures as distinct roles, and distinguish same-size candidates, same-inode aliases, historical copy receipts and fresh byte verification. Attribute completed audits instead of repeating large hashes; none of these identities grants feature or visual acceptance.
- Bind receipt digests by their actual schema. A generic `sha256` beside `source` can identify the new output, not the source input; require an explicit `source_sha256` or a documented source/copy receipt contract. Check impossible same-digest/different-size groups before publishing a duplicate index.
- Trace saved-scene builder inputs independently of Git ancestry. Compare existing render alternatives with exact path/slot provenance and aspect-preserving thumbnails, label unmatched cameras and historical approval scope, and keep source-only prototypes separate from rendered or integrated improvements.
- Recover render histories from all reachable Git refs with full-history merge-parent diffs, plus live artifact/worktree roots. Extract old blobs with `git show COMMIT:PATH` into an owned cache and verify their Git object hashes; never checkout/reset the source repository. Distinguish the owner-facing default theme's origin from the earliest preserved production test.
- Do not let the current hero aspect ratio erase first-generation history. Inspect early shipped plates before applying ratio gates; record narrowly scoped legacy-aspect exceptions and preserve their uncropped dimensions. Inspect thumbnail contact sheets because portrait masks, texture atlases, isolated objects and border renders can share the hero aspect.
- Deduplicate dated renders chronologically using full-byte SHA256 and a conservative tiny-RGB-thumbnail difference, while preserving every occurrence's original path, hash, date basis and decision. A later current/kept status may annotate the earliest representative but must not overwrite its capture date; show the exact CURRENT capture separately. Give owning theme lanes precedence over nested donor names such as pre-day-stone.
- Verify offline history pages with every local src/href target, fresh source hashes, every decoded browser thumbnail, ordering toggles and a real original-image popup in isolated headless Chromium. Bind the verification receipt to both manifest and HTML hashes; leave unavailable dates/statuses explicit instead of inferring acceptance from filenames or round order.

- Validate LOOK/CLEAR against the frozen optics contract, not the physical camera DOF flag alone: a depth-pass compositor defocus can require physical DOF=false in both modes. Keep graph/recipe identity and actual image evidence separate from that boolean.
- Audit decoded border dimensions before writing fidelity claims. Fractional Blender border coordinates can deliver a one-row-short crop at a large master; record the actual dimensions and master sampling instead of upscaling it to the nominal coupon size.

## Verification

Use `terminal` to run a focused stdlib test command under the workspace's resource policy. Record actual failures before implementation and passing results after. Report source-code inspection, metadata reconciliation, synthetic fixture checks, real producer integration and actual renders as separate evidence levels. Do not claim operational cache hits, measured savings or artistic acceptance until those paths were exercised.
