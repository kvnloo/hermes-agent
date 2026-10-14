# Independent review: gateway-handler timestamp continuity

## Verdict

**CHECK / LIMITED: the two added cases are valid focused evidence. No blocking defect found in their claimed timestamp-continuity result.** Independent executions reproduced **base 0 PASS / 2 FAIL and repair 2 PASS / 0 FAIL in both UTC and America/New_York**. The real handler applies the normal append and the late interrupted-row replacement. The repaired rows retain the intended two burst timestamps in those sequences.

This verdict covers the actual imported handler/controller/store/helper/component path with a synchronous test-owned transcript sink and stubbed context/transport. It does not establish a full React App, keyboard, TTY, transport, backend, persistence, full-suite, hosted-CI, current-main, or merge qualification.

## Identity and integrity

- Owner base: `0b58039b7c1f77dd54fa0cd080f794a11002bd49`.
- Published repair under review: `d41adfda966bcb55d8144533804681ac33ef4312`, declared root tree `ef15327789059d4d4732ef946faa0f4adcd9d351`.
- Tracker: https://github.com/kvnloo/hermes-agent/issues/500#issuecomment-6169460081.
- Final expanded manifest SHA-256 inspected: `2ff614e2c60a953c22b42ec3528811ca06baac37197c702794f8c58d04e8d9ac`.
- Test overlay SHA-256: `60d46f5225c90c5476833099788308fbf797c8e9718a7baff02ad1360e12793d`.
- Runner SHA-256: `fc080ecdf1492f842770003891d74adb520495b8d838aabeb66ea618404ac971`.
- Unchanged guard SHA-256: `b27d5d69fbd8140e5c51eb91f918476191617d6a17b0e2bd199cb957488926ac`.

Before and after execution, a byte comparison of all 591 existing non-node_modules regular files in each frozen variant found no differences in its execution copy. This is a broader local-file inventory than the manifest's declared 589-file source/config inventory. The only additional non-node_modules file was the new identical test overlay. All 12 critical source hashes and both root lock hashes in the expanded manifest matched. `@hermes/ink` and `@hermes/shared` workspace links resolve inside each respective copy. These checks validate correspondence to the supplied frozen variants; they are not a new remote commit-tree or registry/dependency audit.

The checkout root AGENTS.md and CONTRIBUTING.md were inspected. The partial copies omit the routed `tui_gateway/AGENTS.md`; the available pristine-review copy of that area guide was also read. No source, test, runner, guard, dependency, or frozen artifact was edited by this review. Only the four authorized focused runs were performed; no install, build, lint, typecheck, full suite, CLI, backend, provider, public write, or network operation was requested.

## Independent executions

Each command used the unchanged `run-focused.sh`, whose environment scrub, fresh disposable HOME/HERMES_HOME/runtime/cache, offline npm setting, and Node guard stayed intact. Each variant/timezone was run once; there were no retries.

| Variant | Zone | Exit | Passed | Failed |
|---|---|---:|---:|---:|
| base | UTC | 1 | 0 | 2 |
| base | America/New_York | 1 | 0 | 2 |
| head | UTC | 0 | 2 | 0 |
| head | America/New_York | 0 | 2 | 0 |

The independent structured observations exactly match the author's four logs. Author log hashes match `results.json`. No `OFFLINE_GUARD`, permission-denial, EPERM, or EACCES diagnostic appeared. Base failures are the five intended timestamp assertions across two tests, not setup failures. The guard intercepts selected Node networking APIs; this is not a kernel-level isolation certification.

Normal append:

- Base `createdAt=1791982801`, although the live burst was at `1791982795`; UTC label changes `[12:59]` to `[13:00]`, New York `[08:59]` to `[09:00]`.
- Repair `createdAt=1791982795`; both live and settled labels remain `[12:59]` in UTC and `[08:59]` in New York.

Late interrupted replacement:

- Base successfully replaces the row text, but both preserved burst rows carry interruption-time `1791982861`. The tail changes `[13:00]` to `[13:01]` in UTC, `[09:00]` to `[09:01]` in New York.
- Repair keeps the first row at `1791982795` and the replaced tail at `1791982801`; tail live and settled labels remain `[13:00]` in UTC and `[09:00]` in New York. Late completion occurs still later, at `1791982921`, so replacement-time stamping would also fail.

Machine-readable results: `independent-results.json`. Raw independent logs and exit records are alongside this report. `integrity-before.json` and `integrity-after.json` record byte/hash checks.

## Why this exercises the actual application path

1. The overlay imports `createGatewayEventHandler` directly; it does not reimplement the event switch or replace production modules. Handler `message.start`, `message.delta`, and `message.interim` branches call the production controller. `publish()` waits for the real batched update to reach the turn store.
2. Normal completion reaches `recordMessageComplete`, takes `finalMessages`, and calls the handler's `msgs.forEach(appendMessage)` path. The injected callback invokes the real `appendTranscriptMessage` and `capTranscriptHistory`, matching the updater composition in `useMainApp.ts:209–215,480–483`. Exact call counts, history length, text, empty streaming state, and numeric timestamp prove more than inspection of a returned controller object.
3. The interrupt uses the real `turnController.interruptTurn` seam. That drains interim segments and seals the tail; it does not synthesize the rows in the fixture. The handler then receives a late interrupted completion and executes its actual `setHistoryItems` functional updater (`createGatewayEventHandler.ts:1553–1560`). The harness applies that function to the real accumulated history. Assertions require one additional updater, zero additional appends, two rows, unchanged first-row identity, a new tail object, and the expected extended interrupted text.
4. Head `turnController.ts:1037–1046` owns the published-burst time in the store; its normal completion, interim flush, and interruption paths propagate that value. The append helper preserves defined `createdAt`. The handler's replacement spreads the existing row and changes only text. The handler and helper source are identical across base and head; the behavior improvement comes from the previously published shared-burst repair.
5. Native `StreamingAssistant` and a separately mounted native `MessageLine` consume the resulting state/row. They render through existing Ink into non-TTY PassThrough streams. Full `useMainApp`, its actual React state setter, and one continuous live-to-history component tree are not mounted.

## Assertion review and possible blind spots

The assertions do not mask the timestamp failures demonstrated here. Timestamps are neither supplied to history by the fixture nor patched into the controller. Completion/interruption are deliberately later than publication. Exact numeric equality catches append-time or replacement-time fallback even if the display oracle is weak. Required live-label checks prevent absent labels from passing as `undefined === undefined`; the late case's two bursts occupy distinct minutes. Fixture body text contains no timestamp-shaped substring. `expect.soft` records failures and produces exit 1, as independently observed.

The replacement preconditions are hard assertions before timestamp comparisons, so a no-op updater, an extra append, or unchanged tail text cannot masquerade as successful replacement. The external `toHaveBeenCalledExactlyOnceWith` assertion also checks the interrupt request even though the production cancellation path catches rejected request promises.

Nonblocking limits:

- `lastLabel` searches accumulated stripped output, not a final-screen snapshot. A prior matching label could remain in that buffer after a later render removed it. These cases establish emitted labels and numeric row continuity, not an enduring final paint.
- The expected live label uses the production formatter shared by the renderer. This does not independently validate general timezone conversion or formatting behavior; a shared formatting defect could agree with itself. The two-zone observed offsets and independent numeric checks support the narrower continuity claim.
- Start, first delta, publication, and initial component mount occur under the same frozen Date within a burst. These cases do not distinguish competing timestamp origins among those instants, nor prove first-physical-paint timing. Real timer APIs still drive batching and Ink scheduling.
- The history sink is synchronous and test-owned. React scheduling, batching, Strict Mode behavior, full-App wiring, history generation, and concurrent update races remain untested.
- The spread-based tail comparison proves equality for the fields present in this fixture. It is not a general immutability test for arbitrary nested fields/tools; the fixture does not populate those. The independent numeric checks protect the timestamp claim.

No test/harness mutation was performed to probe these limits because only the frozen focused executions were authorized.

## Exact remaining scope and README assessment

The reviewed README correctly describes this as an evidence-only follow-up and explicitly excludes full-App, physical TTY, transport/backend/provider, persistence/reload, wire-contract, current-main, full-suite, new lint/typecheck, hosted-CI, and merge-readiness conclusions. The README includes the recommended accumulated-output and shared-formatter cautions and clarifies that Date alone is faked among timer APIs.

Uncovered paths include pending-timer resurrection, start/delta/publication timing separation, remounts during an active burst, intermediate repaint continuity, timestamp-disabled/config propagation, multiple subsequent turns, tools-only or unpublished interruption, no-match replacement, duplicate-text identity selection, interrupted append-from-null, normal no-visible-delta/fallback completion, error/failure completion, cumulative/interim preview dedupe, hydration, out-of-order/repeated completion, backend persistence and reload. Existing earlier evidence may address some of these, but this review does not requalify it or infer coverage.

Preserve kvnloo's contribution and original Muse-assisted implementation credit. Sahil-SS9's adjacent #55602 cleanup-order work remains separately owned and untouched. No origin action or maintainer approval is implied by this review.
