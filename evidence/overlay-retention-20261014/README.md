# Mounted agents-overlay retention evidence

Independent evidence for [origin PR #129524](https://github.com/NousResearch/hermes-agent/pull/129524), tracked on [downstream #449](https://github.com/kvnloo/hermes-agent/issues/449). Production implementation and repair remain kvnloo's; this packet adds no production change.

## Result

**LIMITED; independently reviewed and accepted as bounded mounted-component regression evidence.** The mounted retention invariant passes on exact repaired head `3f2bd549bc3ced2172785e0e91587b80209db10f`. This closes an execution gap after the earlier source reconciliation; it does not establish full-app correctness or merge readiness.

- Six new cases on repaired head: **6 passed**.
- Identical six-case fixture on the repair's actual parent `6a582ba93c9145debe4abf8b0f7001e490427ec7`: **2 passed, 4 failed**. Each retained-row case remains visibly at `59s ago` instead of advancing to `60s ago`. Its later expiry assertions are not reached on this failing parent.
- Existing owner suites `agentsOverlayClock.test.ts` and `overlayScrollbar.test.tsx`: repaired head **7 passed**; repair parent **6 passed, 1 failed** (retained-row clock policy).
- Repeats and independent reruns do not add distinct cases. These counts are not a full-suite result.

The sensitivity comparator is the verified parent of the repair commit, not the origin PR's moving main base. The original always-ticking main behavior need not fail retention.

## Executed path

The test mounts the actual `AgentsOverlay`, real nanostores, `useProcessRows`, and the repository's built native Ink renderer. Four real gateway-shaped `status: exited` snapshots map through production `processStatus` to `done`, `failed`, `killed`, and `lost`.

Each starts 59 seconds after its exit time. The real component's interval advances React state, which drives the real process-row projection. At 60 seconds the current rendered frame still contains the process and `60s ago`; at 61 seconds the process disappears and the overlay's one-second interval is cleared. The underlying process snapshot remains the identical object throughout, ruling out fixture deletion as the cause. Another two minutes of controlled time do not restart that interval.

Controls keep a running process visible and ticking after 61 seconds, and keep a static archived replay without process rows free of overlay timer registrations.

Only Date, setInterval and clearInterval are controlled. React/Ink scheduling using setTimeout remains real. The input stream supplies a synthetic raw-mode interface because `useInput` requires it; output is a non-TTY in-memory stream. `onFrame` captures each complete non-TTY frame separately, rather than searching accumulated historical output. No physical terminal paint is claimed.

Real Ink also creates its own two-second raw-input mouse watchdog. That watchdog is preserved, separately observed, and is not incorrectly counted as an overlay timer. Static hydration may produce a legitimate frame; the static control proves no overlay interval was registered, not zero total renderer frames.

The gateway boundary is an allowlisted in-memory `delegation.status({})` response. Every case asserts exactly that one call; there is no gateway/backend process, transport connection, provider or account. No production module is mocked or extracted into a substitute implementation.

## Requirement and ownership

[The production contract](https://github.com/NousResearch/hermes-agent/blob/3f2bd549bc3ced2172785e0e91587b80209db10f/ui-tui/src/app/processRoster.ts#L32-L35) says finished process rows remain long enough to read, then leave; the transcript notification is the durable record. The filter drops rows when whole elapsed seconds exceed 60. [The review](https://github.com/NousResearch/hermes-agent/pull/129524#issuecomment-5981328402) identified the stopped-clock conflict, and [the owner repair](https://github.com/NousResearch/hermes-agent/commit/3f2bd549bc3ced2172785e0e91587b80209db10f) explicitly addresses it.

The earlier P1 is already source-repaired, as [October 13 reconciliation](https://github.com/kvnloo/hermes-agent/issues/449#issuecomment-6153862929) records. Preserve kvnloo's implementation ancestry and Enough1122's review credit. No duplicate implementation, original-branch update, upstream comment, review, PR or merge is part of this evidence.

## Source and runtime qualification

- Two independent partial exact-source trees each contain **596 verified source/config files**: the complete selected TUI and shared trees plus root configuration. Git blob hashes match the fetched immutable trees. The only source difference between the two selected variants is `ui-tui/src/lib/agentsOverlayClock.ts`.
- The identical test overlay is added outside that original file set. The source trees were rechecked after execution.
- Node **26.7.0**, npm **11.19.0**, Vitest **4.1.10**, React **19.2.7**, nanostores **1.4.2**, and the existing installed dependencies are reused. No package installation occurred. Root lock/package and TUI package manifests match the existing qualified dependency environment.
- Workspace links for `@hermes/ink` and `@hermes/shared` resolve inside each selected source tree. Third-party dependency links resolve to the existing shared installation. Reuse is read-only by intent, not filesystem-enforced.
- All Ink source files match tree `748062fcfe187df062dec353b43bd29110bee16c`. A disposable esbuild **0.28.1** rebuild of that exact source produced the identical reused bundle, SHA256 `20a00e874ac7145c88ed358c3db33150dfcc865df7767e2fc07106ce837ea9fd`.
- Each invocation uses a fresh disposable HOME/HERMES_HOME/runtime/cache, a scrubbed environment, UTC, offline npm mode and the unchanged fail-closed Node network guard (`b27d5d69fbd8140e5c51eb91f918476191617d6a17b0e2bd199cb957488926ac`). No guard diagnostic appeared. This is a Node API guard, not kernel-level network isolation.

## Reproduction

Prepare disposable exact-source trees at the head and actual repair-parent revisions. Use the matching installed locked dependencies and built Ink, with workspace package links resolving to the selected variant. Copy `agentsOverlayRetention.test.tsx` into each variant's `ui-tui/src/__tests__/` directory.

The recorded wrappers expect `head/` and `parent/` execution trees beside them. Update the recorded Node PATH to the equivalent existing installation when reproducing elsewhere. Keep the guard and isolated environment intact.

```sh
bash run-focused.sh head
bash run-focused.sh parent
bash run-adjacent.sh head
bash run-adjacent.sh parent
```

The focused command is `npm run test --prefix ui-tui -- src/__tests__/agentsOverlayRetention.test.tsx --reporter=verbose`. Parent exit 1 is an expected defect witness, not a setup failure. The adjacent command selects only the two owner files named above.

## Independent review

A separate reviewer reverified all 596 recorded files per variant, checked frame capture and timer attribution, and independently repeated both focused runs: head 6/6; parent 2 pass/4 expected failures. It then verified the final formatting-only diff and bound acceptance to fixture SHA256 `337a4075bfaf0116db4e28ab2359db5aa30ca9773a2c0daee12b8bc0ed04a89c`. See [review](independent/review.md) and reviewer logs. Focused ESLint on the final fixture exits 0.

## Initial harness corrections and limits

The first fixture incorrectly counted Ink's input watchdog as an overlay interval. After separating the timer identities by their verified cadences, a static-control assertion still counted one asynchronous hydration frame as periodic work. It was corrected to assert absence of overlay interval registrations instead. These preliminary fixture failures are preserved separately and are not attributed to the candidate. An initial build-provenance command mistakenly passed a native esbuild executable to Node; invoking the existing executable directly produced the matching bundle. Initial focused lint findings were formatting only.

No full suite, aggregate check, full typecheck, i18n IPC, live provider, backend process, database persistence, physical TTY, desktop UI, Windows/macOS, current-main integration or deployment was exercised. No broad performance/savings claim follows from these tests. Real running-process elapsed presentation depends on fresh gateway snapshots and is not proved by the running-row visibility control. Live running/queued agent cadence is covered only by the existing owner helper test, not a new mounted case.

Hosted CI is separate and remains approval-gated: [CI](https://github.com/NousResearch/hermes-agent/actions/runs/37657898904), [Nix](https://github.com/NousResearch/hermes-agent/actions/runs/37657898187), [Docker](https://github.com/NousResearch/hermes-agent/actions/runs/37657898432). No workflow approval, origin action, default-branch update or merge is authorized by this packet.
