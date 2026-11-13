---
name: reconstruction-evidence-consumer-gates
description: "Use when preparing receipt-only reconstruction A/B gates."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [reconstruction, evidence, testing, parity]
    related_skills: [github, upstream-contribution, test-driven-development]
---

# Reconstruction evidence consumer gates

Prepare the consumer independently when a real producer bundle is not available. Do not poll, fabricate a replacement bundle, or implement scoring to fill the gap.

## When to Use

Use for independent consumer preparation, receipt-only fit parity, or trust-boundary checks before an external reconstruction evidence source receives scoring authority.

## Procedure

1. Locate the real checkout, inventory dirty state/refs/worktrees, and preserve it. Fetch the current PR/base into an isolated clone or authorized worktree. Bind receipts to the exact head plus every local delta hash.
2. Read the actual CI workflow and its pinned reusable workflow. Run requested focused tests, the full relevant suite, and CI's native runner on its Python version without site packages when the core claims stdlib-only operation.
3. Check test adoption as well as green output. A pytest function module imported by unittest may contribute zero tests; an unconditional pytest import may break clean CI entirely. Prefer a test-only conversion to unittest.TestCase over adding a new core dependency. Reproduce the failure, compare the unmodified base, retain assertions, and verify executed counts after conversion.
4. Inspect the real fitting callback/evaluator path. A quadratic CLI example is not a scene renderer, and a render-manifest controller is not pixel production. Identify the missing parameter-to-scene adapter plainly.
5. Freeze initial parameters, bounds, every FitConfig field, reference bytes, renderer command/settings/dependencies, and evaluator source. Determine whether the recorded seed actually drives the optimizer or is telemetry; freeze renderer randomness and clocks separately.
6. Require the caller's reference hash to match the bundle reference, not merely the manifest's internal hashes. Revalidate bundle, artifact, reference, source and renderer hashes around both arms.
7. Run baseline and receipt-only arms independently without render/evaluator replay. Use the same canonical candidate paths in both arms, archiving actual PNGs separately; otherwise path fields can legitimately fail exact comparison. Check repeated-parameter render byte hashes and actual call counts.
8. Send each result through its real to_json plus JSON disk/serialization boundary before comparison. In-memory tuples are not JSON arrays. Strip only the designated receipt key, never paths, scores, histories or timing fields added to evaluator output.
9. Check stable expected receipts in both candidate evaluations and nested correction history. Also check candidate sequence, evaluation budget/count, seed, chosen parameters, objective, raw fidelity and optimizer/history equality. Corrupt each field in unit controls and mutation-bypass the comparator to prove the controls fail.
10. Report receipt parity separately from visual acceptance. An all-rejected optimizer plateau can have perfect parity and no accepted raw fidelity. Preserve hard-gate authority and report-only/probe states.
11. If designing a later silhouette term, keep it opt-in/default-zero and held until real parity. Decode a white-is-one mask directly, preregister threshold/grid/framing, preserve multi-component ownership, and avoid silently applying a largest-component photograph heuristic to semantic masks. Do not turn inferred depth into metric geometry or masks into PBR authority.

## Real-producer continuation

- Verify the supplied manifest digest against both disk bytes and the producer's result, then verify every artifact hash. Preserve the distinction between a public generated reference, exact source alpha, inferred depth, and measured geometry.
- Build the smallest authored parameter-to-geometry adapter that exercises the real fitter. Freeze camera, lights, projection, framing, materials, seed and dimensions before evaluation; a recognizable parametric object is a mechanism study, not universal reconstruction.
- Use a fresh page for each renderer invocation in an owned hardware-backed headless compositor. Preserve actual canvas PNGs, compositor screenshots, hardware identity and browser errors; repeated parameter vectors must reproduce byte-identical PNGs. Do not reuse evaluator output or cached renders across arms.
- Re-run receipt-only parity on the final committed source as well as the pre-scoring source. Pin the exact head in the runner; independently compare full disk JSON, candidate/hash traces, correction history and optimizer outputs after stripping only the receipt.
- Keep one experimental silhouette penalty keyword-only and default-zero. Validate a bounded finite weight, require a hash-matched reference, decode the declared semantic mask directly, and require matching nondegenerate render alpha. Record threshold, fixed nearest-neighbor grid, all-component semantics, mask identity, penalty and actual objective; retain raw fidelity and rejected/probe objective authority.
- Treat an all-rejected equal-budget experiment as a useful negative mechanism result. Do not optimize through rejection, silently weaken gates, tune after seeing the result, or claim improvement without an untouched holdout.
- If the assigned output filesystem fills, relocate only the owned lane to authorized durable storage, verify every copied file before removing the old copy, and retain its requested logical path with a symlink. Keep runtime/cache files on the roomy filesystem and record the physical path; do not clean unrelated workers or put durable receipts in expiring scratch.

## Handoff

Leave an executable gate with immediate missing-input refusal, a deliberately unbound plan template, exact command/dependency requirements, source/delta hashes, raw receipts and an explicit real-run hold. No success-shaped synthetic data. Keep test fixes separate from any future scoring change and do not post a readiness claim while real-bundle/render gates remain unmet.
