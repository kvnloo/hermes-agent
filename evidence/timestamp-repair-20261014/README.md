# Shared displayed-burst timestamp candidate

Fork-local candidate for [PR #111511](https://github.com/NousResearch/hermes-agent/pull/111511), pinned to owner commit `0b58039b7c1f77dd54fa0cd080f794a11002bd49` (root tree `a2efc59fc2ca61ca5436fbc5d8486461d035f5d2`).

Classification: **CHECK / LIMITED**. This implements Kevin's [author self-review request](https://github.com/NousResearch/hermes-agent/pull/111511#issuecomment-5853446302), not a maintainer requirement or approval. Preserve kvnloo's existing contribution and original Muse-assisted implementation credit. The separate [evidence commit](https://github.com/kvnloo/hermes-agent/commit/a2bc7c310166037efe92ab4052a32925892b51d2) remains unchanged.

## Change

Three production files share a timestamp captured when a visible assistant burst is first published into turn state. StreamingAssistant reads that timestamp across rerenders/remounts. Completion, segment flush and interruption copy it into the corresponding assistant row before clearing state. New bursts get new timestamps; no displayed stream retains the existing append-time fallback. `appendTranscriptMessage`, existing supplied/persisted times, backend contracts and completion cleanup ordering are unchanged.

The adjacent [scroll-flash PR #55602](https://github.com/NousResearch/hermes-agent/pull/55602) belongs to Sahil-SS9 and changes completion cleanup timing. This candidate does not absorb that work. Its parent is the existing owner head, preserving the contribution's history.

## Executed evidence

Identical focused-test overlay on base and candidate, fake Date with real scheduling and real Ink/controller/store/append/components:

- **UTC and America/New_York each:** base **33 pass, 8 fail**; candidate **41 pass, 0 fail**, the same 41 tests in five files. Do not sum repeated executions as distinct tests.
- Minute-crossing live/settled labels: base `[12:59] -> [13:00]`; candidate `[12:59] -> [12:59]`. Same-minute control remains green. New York shows `[08:59] -> [09:00]` on base and `[08:59] -> [08:59]` on candidate.
- Controls cover separately timed flush/tool/interim bursts, interrupted tail plus sealed segment, active remount and repeated turns with a persistent mount, no delta, disabled streaming, unpublished delta, error/reset/full reset/idle, hydrated visible text after a reasoning-only prefix, and an unstreamed final response distinct from a flushed tail.
- Existing timestamp-off and persisted/supplied timestamp tests pass.
- Scoped ESLint for all five candidate source/test files: pass. `tsc --noEmit -p ui-tui/tsconfig.json` from the equivalent TUI working directory: pass.
- Independent exact-candidate verdict: **ACCEPT for bounded fork-local CHECK/LIMITED**. The reviewer reproduced all four base/head/timezone executions and verified that production bytes are unchanged from the accepted initial repair. See independent-review.md.

Scope details: reset/error/idle controls now assert cleared streaming text/timestamp immediately after the boundary, before `startMessage`, and then test the next no-delta reply. The late interrupted extension check covers the controller return value, not the event-handler application. Pending-timer resurrection and cumulative final-text/interim-preview dedupe remain untested neighbors.

The updated existing timestamp-on/off fixture uses the real controller hydration entry point rather than directly patching a partial store. This identical adapter is also on the base test overlay; it does not supply or calculate timestamps itself.

## Runtime and provenance limits

Executed on a partial exact-source tree (ui-tui, apps/shared and listed root config files), checked against 589 source blobs. Base differs only in the test overlay; candidate additionally differs in the three production files. This is not a full repository checkout or current-main test. Node 26.7.0, npm 11.19.0, Vitest 4.1.10, React 19.2.7 and the existing Ink bundle/dependencies were reused from the earlier verified source/lock-qualified sandbox, copied into isolated trees. No install occurred for this task. Existing npm lock metadata was qualified previously; registry tarball contents were not independently revalidated.

Tests call the real controller and append helper directly and render real Ink components into non-TTY in-memory streams. The interrupt request is an in-memory transport boundary. Event-handler dispatch, full App, backend/provider, real terminal, persisted reload, full suite, i18n IPC, current-main, hosted CI, merge and release were not executed or established. No origin action.

The first base/head commands encountered a self-imposed offline guard interception of npm's optional update check (`https://registry.npmjs.org/npm`); no connection was allowed. Original logs are retained. Installed npm source and its debug log identify the updater. Subsequent commands use the same npm test invocation and unchanged guard, adding `npm_config_update_notifier=false` and `npm_config_offline=true`; final runs have no guard diagnostics. This was not a platform/reviewer denial. The guard is a targeted Node API fail-closed harness, not kernel-level network isolation.

## Reproduction

Use a disposable checkout of the pinned owner commit and dependencies matching its committed package-lock. For the RED side, overlay only the two test files from this candidate; for GREEN, also overlay the three production files listed in candidate-manifest.json. An existing built Ink package is required, as in the recorded runtime.

Run from the checkout root with a fresh temporary HOME/HERMES_HOME/HERMES_RUNTIME_DIR/cache, `TZ=UTC`, `LANG=C.UTF-8`, `npm_config_update_notifier=false`, `npm_config_offline=true`, and `NODE_OPTIONS=--require=<path-to-offline-guard.cjs>`:

```sh
npm run test --prefix ui-tui -- \
  src/__tests__/streamingTimestampContinuity.test.tsx \
  src/__tests__/streamingTimestamps.test.tsx \
  src/__tests__/messages.test.ts \
  src/__tests__/turnControllerNotice.test.ts \
  src/__tests__/turnControllerTodos.test.ts \
  --reporter=verbose
```

The fixture derives its initial expected display using the existing fmtMsgTimestamp formatter; continuity still compares the actual live and settled labels. Timestamp ownership is not mocked or duplicated. Only Date is fake; scheduling remains real. The identical command was also executed with TZ=America/New_York, establishing the non-UTC control. This v2 test portability/cleanup improvement was reviewed separately; frozen v1 evidence was retained unchanged and never published as source tests.

## Packet integrity

The candidate-manifest retains original frozen execution-log hashes. Public logs and review are ANSI/path-sanitized; SHA256SUMS identifies public bytes. Source/test hashes are unchanged. Original v1 logs and rejected-for-portability fixture are retained in the sandbox; harness-diagnostic.json preserves the optional npm updater interception and its original log hashes. The earlier immutable evidence packet contains the independently verified owner source manifest and corrected commit-to-tree provenance.
