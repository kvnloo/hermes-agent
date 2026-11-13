---
name: gev-ci-reliability-receipts
description: "Use when qualifying GEV CI and QA owner fixes."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [ci, qa, github, receipts]
    related_skills: [github, upstream-contribution, systematic-debugging]
---

# GEV CI reliability receipts

## When to Use

Use for God's Eye View CI admission audits and independent qualification of existing QA fixes; keep preparation-only and native-platform evidence boundaries explicit.

## Procedure

- Audit GitHub Actions by immutable current PR head. Fetch every page of runs, then each run's latest `run_attempt` jobs endpoint; reconcile `total_count` and preserve raw payloads. Separate `action_required` with zero jobs, no runs, and actually executed failed steps. Deduplicate admission proposals by repository/head/workflow ID/path, not by display title or run count. Never approve or rerun merely to investigate.
- Keep historical parent receipts separate from latest main and owner-head execution. Existing mutation-anchor repairs should be independently run on their actual parent and actual owner head; do not reimplement them. Verify all mutated files restore after each gate, and run the unmutated affected tests to guard against a harness counting unrelated failures as successful mutation catches.
- GEV's official unit runner runs ordinary tests first, then Node24-only allocation files sequentially with `--expose-gc`. Run Node24 with `GEV_REQUIRE_ALLOCATION_GATE=1`; allow the runner's documented Node26 skip with `0`. Parse every summary block: ordinary results and allocation results are separate; a Windows-only test skip is distinct from the allocation skip. Long allocation workers may buffer output until a workload finishes; inspect owned process liveness before calling them hung.
- Use a loopback HTTP fixture with reachable no-key, reachable HTTP404 and unreachable cases to qualify early QA gate exits without provider keys. An optional `--import` observer can distinguish explicit `process.exit(2)` from natural `beforeExit(2)` while preserving original exit behavior. Linux drain observations do not reproduce Windows libuv crashes.
- A `path.win32` predicate fixture establishes separator semantics only. Never call it native Windows execution. Run the original unmodified test on supported local Node versions separately and retain any cited native Windows evidence under its original author's attribution and exact SHA.
- Verify browser coverage from `.github/workflows/ci.yml`, not stale CONTRIBUTING prose. GEV's Street Level and portable-panel job uses a built preview with dummy `MLY|0|qa-fixture`, intercepted Mapillary fixtures, strict skip policy and `QA_FAIL_ON_RETRY=1`; tracking remains a local real-app dev-server gate. Provider skips must remain explicit.
- Share installed dependencies only when both package.json and package-lock.json match exactly. Equal locks with different manifests do not meet an exact-manifest reuse constraint; install in the owned checkout instead.
- Keep Chromium headless, disable cores, use a short scratch TMPDIR and private profiles, and run only on an explicitly checked owned port. Preserve raw failures before retrying; distinguish source regressions, external provider failures, resource contention and profile-startup failures.
- For independent bundle restores, compare complete base/head Git tree entries (blob and mode), preserve owner test-name changes, and verify moved source assertions individually on the actual scheduler owner. Replay behavioral mutations with only the added cases selected and retain every runtime's named failures plus restored production hash. Audit full-suite owner logs as owner execution unless independently rerun, parsing all serialized allocation summary blocks.
- When reusing locked JS dependencies for an owned Vite replay, keep the checkout's node_modules directory and .vite/.vite-temp caches private; symlink dependency entries rather than the entire directory. Otherwise --force can mutate another worker's optimized cache despite unchanged source. An initial browser failure followed by baseline/candidate passes remains an unexplained intermittent observation, not deterministic full-browser green or a reproduced baseline failure.
- Diagnose selected-action gate failures with timestamped application selection, camera handoff and accessible-mirror samples. A fixed post-click delay can precede mirror publication even when selection is correct; use a bounded state wait and retain the original selection/flight assertions. Cover late publication, permanent absence and the original aggregate-count behavior independently; helper controls alone do not lock their browser call site.
- Lock selected-action wiring with a review-only full-browser control that delays the real selected button's `aria-pressed` publication after the actual click, then compare identical assertions with only the post-click wait reverted. Keep click, flight, navigation generation and selected identity real; retain a hold beyond the timeout as the fail-closed control. Record the injected delay and timestamps, and do not relabel mutation sensitivity as a naturally reproduced historical flake when unchanged baseline runs pass.
- Qualify polling bounds precisely: a Date.now deadline may overshoot by one polling interval plus evaluation latency, and it does not cancel an in-flight browser evaluation. Use independent clock tapes for zero/non-multiple/default budgets and propagate snapshot/render/sleep errors unchanged; a timeout returning the last snapshot is safe only when the consumer's original failure assertions remain intact.
- Report panel retries precisely: the strict helper can allow a provable miss explained by the panel's own movement. A passing run with that warning is not a no-retry run. Preserve built-preview Street Level provider skips rather than treating strict mode as proof of unavailable Google 3D behavior.
