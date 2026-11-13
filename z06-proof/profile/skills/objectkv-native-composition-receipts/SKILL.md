---
name: objectkv-native-composition-receipts
description: "Use when qualifying objectKV native composition gates."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [rust, objectkv, regression, receipts]
    related_skills: [upstream-contribution, test-driven-development, github]
---

# objectKV native composition receipts

## When to Use

Use for exact-head receipt-only qualification of count-conversion and concurrent route-refresh carriers. Preserve existing owner branches; publication and formal review are separate gates.

## Dependency and containment

- Refresh exact PR heads/base, policies, complete comments/reviews, and exact-head runs/jobs. Empty rollups and action-required runs with zero jobs are not executed CI.
- Read the pinned Rust toolchain and Cargo.lock. Reuse the exact installed toolchain. When explicitly authorized, run `cargo +VERSION fetch --locked` in an owned CARGO_HOME; use normal public transport and stop the denied read after auth/403. Do not change credentials, locks or global toolchains.
- Hash locks before/after every gate and verify the Cargo git checkout's full pinned SlateDB SHA. Cargo's untracked `.cargo-ok` marker is not a production edit.
- Hold the shared native-build flock; cap Cargo jobs at two and check free disk/available RAM before heavy work. Verify the **actual process cgroup** rather than trusting a successful systemd-run scope creation: a host supervisor can relocate the process. If its effective limits differ, correct only within explicit resource-owner authority, otherwise pause and report. Retain the deviation and repeat affected gates under verified limits.
- Inspect every ancestor of the actual process cgroup: `max` on the leaf can still inherit the approved CPU/memory envelope from `agent.slice`. Capture the runner, active Cargo/rustc/linker descendants and effective ancestor limits; do not change a shared scope merely because its leaf is unlimited.
- Use private targets per checkout. To reuse compiled dependencies, copy/reflink a completed target, then `cargo clean --offline -p ...` for every workspace package before building the new checkout. Never accept another checkout's identically named test binary.

## Native gates

Run actual owning manifests, not extracted substitutes: focused binary count fixtures, route-client module tests, full owning crates, workspace tests, `cargo fmt --all -- --check`, strict all-target workspace Clippy, smoke and supported adjacent official suites. Use `--locked --offline` after authorized dependency acquisition. Report overlapping suite counts per command, never as unique totals.

Make matching-base test-only overlays using the author's unchanged fixtures. Require assertion RED, not dependency/compiler failures. Preserve their explicit overlay tree hashes and checksummed patches.

## Composition

Apply one exact component delta onto a detached checkout of the other without merging branches. Record HEAD and uncommitted tree separately; a tree hash is not a commit. Keep an uninstrumented union identity separate from any supplemental test overlay.

A meaningful supplemental test can exercise two overlapping public `KvReadClient::point_at` calls against the real router/TCP listener and pinned SlateDB fixture. Hold the first source refresh, allow the second reader to publish the newer cache, then return a stale source map to the first. Do not mutate the private cache to claim public-call coverage.

Feed the successful payload's actual byte length into the owning eval binary's real `bounded_count` with an explicitly disclosed prior counter near u32::MAX. This joins routing and numeric reporting on one assertion path **without allocating a multi-GiB payload**. Label the prior counter as seeded; never claim a measured multi-GiB transfer or production performance.

Run that same single test with only count conversion reverted, only route refresh reverted, then both restored. Require the expected distinct assertion failure at each component and a final pass; verify Cargo lists the test and restoration matches the recorded tree. Check method visibility before using private introspection in a cross-crate fixture.

Keep the fixture's limits explicit: a scheduled in-process source is not a replicated authority, a direct reporting-helper call is not a naturally accumulated CLI telemetry stream, and successful listener abort/join is not cancellation qualification. Audit Arc snapshot retention, locks across awaits, source deadlines and timeout/panic cleanup separately; do not invent a production leak or claim disposal coverage without a corresponding probe.

## Delivery

Preserve exact commands, cwd, environments, exits, log hashes, source trees and current CI/review snapshots. Deliver original commits in an incremental bundle with explicit base prerequisite; fresh-restore and verify both trees, ancestry, clean status and connectivity. Bundle integrity is not independent correctness review. Keep local-path receipts private unless separately sanitized and publication-authorized.
