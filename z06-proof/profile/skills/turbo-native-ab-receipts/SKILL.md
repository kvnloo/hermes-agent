---
name: turbo-native-ab-receipts
description: "Use when proving Turbo research/code A/B runs."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [turbo, benchmarking, hermes, receipts]
---

# Turbo native A/B receipts

## When to Use
Use for matched Turbo/reference research or code proofs, especially native nonzero exits and screenshot quality verdicts.

## Procedure

- Inspect each native `prompt.receipt` result before diagnosing an adapter exit: `completed=false` with `max_iterations_reached` is an exhausted tool budget, not proof that the authored test failed. Preserve the failed cell and require independent verification; never convert an incomplete turn to success based on prose.
- Give tool-using authors and independent verifiers a bounded iteration allowance sufficient for repo discovery, implementation, browser diagnosis and reruns. Keep the task wall deadline, exact-session cancellation and false-on-incomplete semantics unchanged. Regression-test the emitted session policy.
- Freeze both code cells to the same exact source revision in an owned baseline worktree. A live checkout can move during a long serialized proof. Never run code authors in the live checkout.
- Pass deterministic owner argv checks for syntax and actual test execution into the integration worktree. A verifier's self-report is not the final executable oracle. Inspect the test source, JSON outcomes and actual dark/light-control PNGs, then rerun the test independently.
- Run long proof drivers as tracked background jobs rather than relying on a foreground tool's requested timeout. A transport timeout may kill the CLI viewer/driver without cancelling accepted native gateway work. Resume the exact owned session, fence interruption to its recorded execution generation, and read terminal receipt before starting another cell.
- Respect host heavy-lock and memory admission. Do not acquire the same lock again inside an author/browser child while the parent holds it. Never kill peer jobs to get admission.
- Report end-to-end external wall time separately from runtime ledger wall and per-request decode speed. Compute output-token/full-external-wall throughput programmatically. Peak adapter overlap is measured execution concurrency, not the configured worker cap.
- Distinguish catalog-free provider calls from native subscription calls. Sum actual provider input/output counters; do not call a receipt's entire `free_tier_usage` array free when it includes subscription/unknown billing rows. Catalog eligibility is not a confirmed zero-dollar invoice.
- Expose truncated helper outputs, unsupported claims corrected by verifier, retries and interrupted attempts. A successful final synthesis does not prove helpers were useful or quality improved. Single matched trials are exploratory, not statistically reliable speed claims.
- Preserve private source/transcripts locally. Publish only a scrubbed method, aggregate metrics, revision bindings and scoped verdicts; never cloud-share private screenshots/source for an extra judge.
- Preserve a flaky reference's failures even when a retry passes: translucent backgrounds, unsettled fonts and overly broad text bounding boxes can change sampled contrast without source changes. Keep fixed readability gates; verify repeated executions and never label a failed reference as a successful-vs-successful speed comparison.
- After updating a PR body, read back exact bytes and bind its evidence receipt to current head. Do not call all checks green based on an earlier commit.
- Execute both sides of a native comparison even when the first fails; accumulate exits instead of letting `set -e` skip the challenger. Label a selected-file base overlay as an overlay, not a pristine checkout. Keep the overlay manifest, source hashes, and daemon logs with the result.
- When native tests fail during signal cleanup, preserve RPC replies and observe the spawned PID, parent chain and creation times before diagnosing a runtime regression. Do not bypass a live-system guard or mock process ownership to obtain green. A later passing run does not explain or erase an intermittent refusal.
- Refresh reusable qualification scripts when adding integration seams. Stage and hash every changed runtime module and new test, and disable automatic retries while investigating flakes; a script that omits the new boundary cannot qualify it.
