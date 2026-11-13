---
name: dash-memory-retention-qualification
description: Use when diagnosing Dash Android memory growth.
version: 0.1.0
author: Kevin Rajan (kvnloo), Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [dash, android, memory, chrome, qualification]
    related_skills: [dash-native-dev-build, systematic-debugging]
---

# Dash memory retention qualification

## When to use
- Investigate growing memory, freezes, or Android persistence/hydration failures in Dash.
- Qualify reply-store lifecycle cleanup without disturbing the daily phone.

## Client/host data boundary
- Treat host-backed session history as host-authoritative and the phone transcript as a bounded, reconstructible cache. Verify the actual history/refetch path before declaring a particular cache disposable; local-only conversations are not automatically host-backed.
- Inventory phone-only drafts, queued sends, not-yet-uploaded shares, credentials and preferences separately before choosing recovery. Distinguish clearing a transcript cache from clearing all app data: the latter can remove pairing and unsent work.
- Do not frame preserving an oversized transcript cache as preserving authoritative history. Prefer cache invalidation/refetch when proven safe, and require storage/hydration failures to leave the client usable rather than blocking startup. This is an acceptance contract, not evidence that recovery is already implemented.

For CursorWindow failures and private database inspection, use [Android persistence diagnosis](references/android-persistence.md).

## Procedure
1. Re-observe the served source and phone PID before attributing evidence. On an actively used phone, obey the current authorization: read-only `dumpsys meminfo -d`, `dumpsys gfxinfo`, `top -H`, and logcat do not authorize heap dumps, GC requests, taps, launches, installs or service restarts.
2. Save timestamped meminfo samples outside Git. Compare native heap allocated bytes, resident category PSS, Graphics, Java, Unknown and swap separately. Verify the printed TOTAL PSS arithmetic: Samsung builds may include SwapPss in that total. Native plus Unknown does not prove Hermes retention; Hermes and C++ need separate attribution.
3. Reproduce lifecycle retention through real store interfaces. Check completion, error, Stop, lost turns, deletion, ended-chat cleanup and forgetting. Assert both preserved checkpoint content and released working copies. Preserve final-text consumption by settlement observers. Do not evict on-demand details when a stale completion is replayed.
4. Use Dash's `scripts/build-retention-probe.ts` and `scripts/reply-retention-proof.mjs` when available. The Chromium harness bundles the real app stores, stubs only storage/identity adapters, completes/deletes synthetic replies, forces browser GC, records `Runtime.getHeapUsage` and saves a heap snapshot. Label it a store-lifecycle reproduction, not complete Expo or Android acceptance.
5. Run installation, tests, typechecks, mutation and exports through `fleet-build --node mbp`. Use an owned cache and lock. Exclude `node_modules` without a trailing slash: an absolute dependency symlink can otherwise survive rsync and break worker installation. Never install into the served dependency tree.
6. Require the intended behavioral failure on the baseline. Missing React/dependencies and browser import-resolution timeouts are setup failures, not red regression evidence. Bundle a safe identity adapter when a standalone browser-store harness otherwise hoists external Expo native imports.
7. Inspect native logcat for repeated Fabric synchronous-props failures. Reanimated animatedProps on an SVG G can target a child with no SurfaceMountingManager entry. Prefer native View transforms around an independent SVG eye layer; renderer proofs must inspect that computed View transform. Web success alone cannot prove the Android exception or memory growth is gone.
8. Bind receipts to source hashes and distinguish candidate-only reruns from baseline reruns. Publish phone-observed, browser-reproduced and unverified-native outcomes separately.

## CursorWindow and cache boundaries

- Measure AsyncStorage value sizes from a private, read-only RKStorage copy before diagnosing `Row too big to fit into CursorWindow`. An intact SQLite database can still have an unreadable large value. Never treat Android's Clear cache as removing values stored in that database.
- Separate registered host-backed history from durable local-only conversations, routing and unsent state. Use Expo's native cacheDirectory for bounded text-history projections, documentDirectory for durable per-chat records, and independent tiny credential/settings reads. Omit host tool payloads from the offline projection and bound the recent suffix before JSON allocation.
- Exercise real recovery counts before rollout. Legacy client IDs can collide across different host routes; preserve both through deterministic recovered IDs rather than overwriting one file. Compare supported local-only records after roundtrip and leave an unreadable legacy row intact until explicit recovery commits.
- For binary phone transfers, prefer `adb shell -T` with an explicit completion sentinel and verify every target file by hash. `adb exec-in` plus cross-directory moves can return before a complete recovery is observable. A successful exit is not a file-count receipt; commit migration markers only after the full record set is present.
- Apply a targeted patch to the exact installed release instead of promoting an unrelated turbo stack. Re-observe the live turbo head before composing its equivalent fix, and qualify both compositions separately. Do not foreground or reload the daily phone after a UI-approval prompt times out; background source deployment is distinct from native interaction acceptance.

## Pitfalls
- Keep Bun module mocks complete for the combined suite: an app-store AsyncStorage stub without getItem can break composer-draft imports in a different test file. Repair the test adapter, not production persistence, for this failure.
- Avoid nested asymmetric matchers in Bun 1.4.3 `toMatchObject` when later inspecting the same object: the matcher can replace the actual nested array with its matcher object. A minimal `bun -e` probe confirms this mutation. Capture the expected parts before completion and use exact `toEqual` instead.
- Replacing a keyed value does not retain every delta by itself. Prove a surviving reference or unbounded queue rather than inferring one from allocation churn.
- Long transcripts may be retained by both checkpointed messages and process-global streaming stores. Deleting the visible chat is not proof that those global stores released its strings.
- A quiet Expo export can be doing Babel/Terser work. For an owned admitted worker only, inspect its CPU activity/profile before calling it hung; never instrument or restart the owner's Metro to debug a worker.
- Memory rate from synthetic loop throughput is not phone MB/min. Do not normalize it into a claimed on-device improvement.

## Verification
- Behavioral red and green receipts name the same lifecycle contract.
- After GC, retained cache characters are zero for deleted replies and browser heap growth is bounded; saved transcript content remains correct.
- Native memory correction remains pending until an authorized post-rollout same-workload Android series exists. Never call a JavaScript-only reproduction proof of a multi-gigabyte native leak's full cause.
