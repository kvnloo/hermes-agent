# Independent runtime-evidence review

Reviewed 2026-10-14. Verdict: **credible failing native-component reproduction** of the requested streaming-to-settled timestamp discontinuity on the materialized owner head `0b58039b7c1f77dd54fa0cd080f794a11002bd49`. This is an evidence-only result, not a repaired implementation, full-repository qualification, E2E result, or maintainer approval.

## Executed outcome

Only this runtime command was executed during this review:

```sh
bash <evidence>/run-targeted.sh > <evidence>/logs/independent-review.log 2>&1
```

- Exit status: **1**. Vitest 4.1.10 started at 12:22:15 UTC; reported duration 1.12 s.
- Five explicit test files: **4 passed, 1 failed; 26 tests passed, 1 failed**.
- Same-minute control: live `[12:59]`, settled `[12:59]`; passed.
- Minute-boundary case: live `[12:59]`, settled `[13:00]`; failed the continuity assertion at `streamingTimestampContinuity.test.tsx:110`.
- Existing streaming timestamps-on/off, persisted timestamps, supplied-time preservation, append-time fallback, and controller-neighbor controls passed.
- Offline guard remained unchanged and enabled. No `OFFLINE_GUARD` diagnostic appeared. No denial or network attempt was observed. This JavaScript guard is not an OS-wide network audit.

## Test credibility

The new test imports the real controller, stores, append helper, streaming component, settled row component, and built Hermes Ink renderer. Only `Date` is faked; controller scheduling, React/Ink rendering, and polling use real timers. The test resets state, advances the clock with the live component still mounted, verifies the second streamed text and stable live label, completes through the controller, appends its actual output, and compares the rendered settled label with the captured live label. The same-minute control distinguishes the boundary-sensitive failure from a general render/setup failure.

The source explains the observed result: `StreamingAssistant` owns a render-local start-time ref; `recordMessageComplete` creates the final assistant message without `createdAt`; `appendTranscriptMessage` supplies the later append-time clock. `createGatewayEventHandler` forwards those final messages, and `useMainApp` wires its append callback to the tested helper. Thus manually composing the completion-to-append seam matches the inspected normal production path.

## Provenance checks

- Recomputed Git blob hashes for all **589** manifest files: **zero mismatches or missing files**. Recomputed the SHA-256 entries in `materialization.json`: zero mismatches.
- Materialization records 586 existing Git blobs and 3 connector exact-ref blobs. This review checked local bytes against that recorded manifest; it did not independently reacquire the remote commit/tree.
- The timestamp tree and prior paste tree root lockfiles are byte-identical, SHA-256 `9934677654ce672900b0946898cc28c73671f75896862b5768c24cca84776ccd`.
- All **1,338** installed hidden-lock entries match the root lock for version/resolved/integrity metadata, with no extra entries. Spot-checked installed package versions for React, React reconciler, Vitest, Vite, TypeScript, esbuild, nanostores, and the React nanostores binding all match.
- Relevant `@hermes/ink` and `@hermes/shared` workspace symlinks resolve inside this timestamp tree. The root dependency directory is a reused copy, not a fresh install, and installed package contents were not revalidated against registry tarballs.
- The only nonmanifest nondependency files under `head/` are the new continuity test and generated Ink bundle. The existing build log records a successful Ink esbuild invocation; this reviewer did not rerun the build.
- New test SHA-256: `5c1db1c8fc44eb46aba145b55d8340d397556f42fc5d7d397f353f8dcc9e53f2`.
- Executed Ink bundle SHA-256: `20a00e874ac7145c88ed358c3db33150dfcc865df7767e2fc07106ce837ea9fd`.
- Independent log SHA-256: `052bc693b9f0b82d4d14c492fad35cdea6c5926a3ef3529857a97cd199d8323e`.

## Limits and actionable concerns

1. Label this **partial-tree/native-component failing evidence at the owner head**. The test does not mount the full app, invoke the gateway event dispatcher, run a backend/provider, exercise a real TTY, validate persistence end-to-end, or compare base behavior. It proves the requested invariant fails at this head; it does not establish when that behavior was introduced.
2. The fixture covers one uninterrupted single-text reply. Multi-burst/tool/interim boundaries, interrupt/error paths, subsequent turns, remounts, timestamp settings propagation, and persisted reload continuity remain outside the demonstrated result. Existing off/persisted controls are separate tests, not cross-boundary versions of this flow.
3. Preserve the intentional append-time fallback and supplied/persisted `createdAt` semantics when designing a repair. The smallest repair boundary is shared ownership/propagation of the streaming reply timestamp through completion, rather than changing the global append helper's meaning. No repair was made or evaluated here.
4. Keep the earlier `qualification.json`/`.md` clearly identified as a historical source-only checkpoint, or supersede it with a separate dated execution receipt. Its statements that tests, build, and claim creation have not occurred are stale relative to the new logs and `claim-confirmation.json` for issue #500.
5. Kevin's linked request is author self-review, not maintainer agreement. Preserve kvnloo/Muse-assisted original implementation credit. The failing test is additional evidence and does not transfer implementation ownership or imply merge readiness.

No source/test edits, installation, full-suite run, i18n IPC, network access, GitHub writes, or frozen-file changes were performed by this reviewer. The review file and distinct rerun log are this review's outputs.
