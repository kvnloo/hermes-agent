# Gateway-handler timestamp evidence

**CHECK / LIMITED.** Evidence-only follow-up to the [published shared-burst repair](https://github.com/kvnloo/hermes-agent/commit/d41adfda966bcb55d8144533804681ac33ef4312), tracked in [the separate claim on #500](https://github.com/kvnloo/hermes-agent/issues/500#issuecomment-6169460081). No production code was changed for this follow-up.

## Executed result

Two unique invariant tests were exercised with the same overlay on the owner base and published repair, in UTC and America/New_York. Each zone produced **base: 0 PASS / 2 FAIL; repair: 2 PASS / 0 FAIL**. Four executions do not mean eight distinct tests.

| Path | UTC base live → settled | UTC repair live → settled | New York base | New York repair |
|---|---|---|---|---|
| Handler normal append | [12:59] → [13:00] | [12:59] → [12:59] | [08:59] → [09:00] | [08:59] → [08:59] |
| Handler late interrupted replacement | [13:00] → [13:01] | [13:00] → [13:00] | [09:00] → [09:01] | [09:00] → [09:00] |

The base's late replacement succeeds as a text update too; the failure is that its row was stamped at the later interruption time. The repaired row retains the earlier visible-burst time through both interruption and the late update. The already sealed earlier burst retains its own distinct timestamp on the repair.

## What this adds

The previous 41-test repair receipt covered direct controller/store/append/native components and only source-inspected the late handler update. These two tests import and invoke the real `createGatewayEventHandler`:

1. `message.start`, `message.delta` and normal `message.complete` reach the real controller and the handler's normal append branch. The injected transcript callback executes the production `appendTranscriptMessage` and `capTranscriptHistory` helpers, as `useMainApp` does.
2. After a real `message.interim` boundary and a second published burst, the production local interrupt seam seals both rows. A late `message.complete(status=interrupted)` then executes the handler's actual functional history updater. Assertions prove that this updater is called, the tail row is replaced with extended text, no extra append occurs, every other tail field is retained, and the earlier row remains the same object. These checks execute before timestamp comparisons, on both the red and green variants.

Both cases compare actual native-Ink `StreamingAssistant` and separately rendered `MessageLine` output. Timestamp ownership is neither mocked nor supplied by the fixture. Only Date is faked among timer APIs; controller batching and Ink scheduling remain real. The expected initial display uses the existing formatter and thus follows the process timezone. This does not independently validate the formatter or timezone conversion. Soft assertions collect multiple timestamp failures but still fail the test and process.

The transport boundary is in-memory. The normal case asserts no request/RPC call. The interruption case asserts precisely one `session.interrupt` request for its fixture session and no other RPC. No gateway.ready, provider, network or backend process is involved. No production-module mocks are installed.

## Identity and environment

- Owner base: `0b58039b7c1f77dd54fa0cd080f794a11002bd49`.
- Repair tested: `d41adfda966bcb55d8144533804681ac33ef4312`, root tree `ef15327789059d4d4732ef946faa0f4adcd9d351`.
- Publication branch is a separate descendant of that repair. Original owner, repair and earlier evidence branches are unchanged.
- Execution uses fresh copies of the existing 589-file partial exact-source trees, not a full repository checkout. All 589 source/config files in each copy were compared byte-for-byte against its frozen variant. The two-case overlay is identical on both variants. Prior test overlays remain present but are not selected by this command.
- Existing Node 26.7.0, npm 11.19.0, Vitest 4.1.10, React 19.2.7, nanostores 1.4.2 and built Ink were reused; no install or build occurred. Root lock SHA-256: `9934677654ce672900b0946898cc28c73671f75896862b5768c24cca84776ccd`. Existing dependency provenance is inherited from the accepted repair, not a fresh registry-tarball audit.
- The unchanged fail-closed Node API guard has SHA-256 `b27d5d69fbd8140e5c51eb91f918476191617d6a17b0e2bd199cb957488926ac`. Each invocation uses a fresh disposable HOME/HERMES_HOME/runtime/cache, a scrubbed environment, offline npm mode and disabled npm update notifier. No guard diagnostic appeared. This is a Node API guard, not kernel-level network isolation.

## Reproduction

Use disposable exact-source copies of the owner base and published repair with the same locked dependencies and existing built Ink. Overlay `ui-tui/src/__tests__/gatewayTimestampContinuity.test.tsx` identically in both. Do not copy timestamp production changes onto the red side.

`run-focused.sh` records the actual wrapper. Its `base` and `head` directories are execution copies; its Node PATH is specific to the recorded sandbox and should point to the equivalent existing Node 26.7.0 installation when reproduced elsewhere. For each variant and timezone, the selected command is only:

```sh
npm run test --prefix ui-tui -- src/__tests__/gatewayTimestampContinuity.test.tsx --reporter=verbose
```

Keep the recorded guard and disposable configuration. Do not remove a guard or widen the selected files to obtain a pass. The base exits 1 for timestamp assertions; the repair exits 0. `results.json`, raw logs, `manifest.json` and `SHA256SUMS` record the execution evidence.

## Independent review

An [independent critical review](independent/review.md) accepted this focused evidence as **CHECK / LIMITED**, with no blocking defect. It independently reproduced all four runs using the unchanged wrapper, verified source/test/guard identities before and after execution, and confirmed that the actual handler updater changes the existing interrupted row. Its four logs and structured observations are included under `independent/`. The two unique tests remain two tests across all repeated executions.

## Remaining limits and ownership

This closes only the focused normal handler-append and late interrupted-row replacement boundary. Local Ctrl+C itself is invoked through `turnController.interruptTurn`, not keyboard input. The React full-App state setter, physical TTY paint, actual transport/backend/provider, wire contract, database persistence/reload, current-main compatibility, full suite, new lint/typecheck run and hosted CI are not established. Native components render to non-TTY in-memory streams; `lastLabel` reads accumulated stripped output rather than a final-screen snapshot. Direct numeric `createdAt` assertions separately establish timestamp continuity. No merge-readiness, origin acceptance or product-requirement approval is implied.

Pending-timer resurrection, cumulative/interim response-preview dedupe, tools-only/unpublished interruption, no-matching-row behavior, duplicate-text identity selection, hydration/out-of-order events and other lifecycle neighbors remain outside these two cases. A first-published timestamp is not a physical terminal-paint guarantee.

Preserve kvnloo's existing contribution and original Muse-assisted implementation credit. [Kevin's request](https://github.com/NousResearch/hermes-agent/pull/111511#issuecomment-5853446302) remains author self-review, not maintainer direction. Sahil-SS9's adjacent [#55602 cleanup-order work](https://github.com/NousResearch/hermes-agent/pull/55602) is separate; this follow-up does not edit or absorb it. No origin action was taken.
