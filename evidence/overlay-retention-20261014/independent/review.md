# Independent review: mounted AgentsOverlay retention

Classification: **ACCEPT as bounded mounted-component regression evidence** for Hermes #449 / origin PR #129524. No blocking assertion or provenance defect found within the supplied packet.

## Independent rerun

Using the unchanged `bash run-focused.sh head` and `bash run-focused.sh parent` on 2026-10-14 UTC:

- Head: exit 0, **6 passed**. See `head-reviewer.log`.
- Repair parent: exit 1, **4 expected failures / 2 passed**. Every settled-process case retained its sentinel at **59s ago** when **60s ago** was required. Running-process and static-replay controls passed. See `parent-reviewer.log`.
- No `OFFLINE_GUARD` violation or unexpected failure appeared. New disposable homes and local test caches were retained. No install, external write, broad test, production-code edit, GUI, or provider operation was performed.

The independently rerun test SHA256 was `5873c81842b2673a4a0c566cca561cd58e33c427a35bee9f68c0d7c9b8551350`, preserved in `fixture-reviewed-before-formatting.tsx`. I inspected the complete `formatting.diff` and verified equality after removing blank lines and normalizing the two reordered named-import lists. No executable behavior changed. Final packet/head/parent tests are identical with SHA256 `337a4075bfaf0116db4e28ab2359db5aa30ca9773a2c0daee12b8bc0ed04a89c`. I also inspected the owner-produced final-artifact logs: `../logs/head-formatted.log` remains 6 passed; `../logs/parent-formatted.log` remains 4 expected failures / 2 passed. The independent acceptance extends to this formatting-equivalent final artifact. Final formatting runs and focused lint were performed by the owner, not repeated by this reviewer.

## Provenance

- Recorded head: `3f2bd549bc3ced2172785e0e91587b80209db10f`; repair parent: `6a582ba93c9145debe4abf8b0f7001e490427ec7`.
- Independently recalculated Git blob hashes for all **596** source/config files per variant. Head matched `source-files.json`, whose entries also matched `source-trees.json`. Parent UI matched `parent-ui-tree.json`; other files matched the shared recorded baseline. No missing files or hash mismatches.
- Complete recorded head/parent UI tree comparison shows only `src/lib/agentsOverlayClock.ts` differs. Local source/config comparison likewise shows only that policy file differs. This is an isolated policy differential, not an independently fetched full-parent checkout.
- Local `@hermes/ink` and `@hermes/shared` links resolve to each variant's own source. Both Ink bundles and the supplied exact-source rebuild have SHA256 `20a00e874ac7145c88ed358c3db33150dfcc865df7767e2fc07106ce837ea9fd`.
- Unchanged guard SHA256: `b27d5d69fbd8140e5c51eb91f918476191617d6a17b0e2bd199cb957488926ac`. The runner preserves its environment isolation and network guard. Existing third-party dependencies are borrowed through symlinks; these are read-only by intent, not a filesystem-enforced mount.

## Assertion and harness assessment

The packet mounts the real `AgentsOverlay`, nanostores, process-row derivation, and native Ink renderer. Only the `delegation.status` transport response and Date/interval APIs are controlled; real render scheduling is preserved. The transport stub rejects unexpected methods/parameters and assertions require exactly one expected call.

Frame capture is appropriate: non-TTY `LogUpdate.render()` emits the full current frame, `writeDiffToTerminal()` precedes `onFrame`, and the PassThrough listener collects those writes synchronously. Resetting the pending buffer at each frame avoids stale historical text. This is not an ANSI-diff reconstruction pretending to be a current screen.

The settled-row cases start at 59 seconds since exit, advance 1 second to require both the command and `60s ago`, then advance another second to require removal. The real row builder retains ages <= 60 and drops > 60. The test observes one 1-second overlay interval at 60 seconds and none after expiry; the snapshot retains identity. No further frame is captured during the subsequent 120-second simulated advance. Source inspection corroborates the effect's `clearInterval` cleanup.

Ink's independent 2-second raw-input watchdog is preserved and distinguished by delay. Its probe returns immediately for non-TTY stdout. The asserted interval sets are [1000, 2000] during active retention and [2000] afterward, preventing the watchdog from being mistaken for an overlay leak or a retention clock.

The running control confirms visibility past 61 seconds with the 1-second interval still registered. The archived replay control confirms content remains visible and **no overlay timer was ever registered**. It makes no claim that hydration caused zero renders.

## Boundaries

This establishes controlled mounted behavior, not production elapsed-time accuracy, real-terminal keyboard/layout behavior, backend/provider integration, build/type/lint health, or full-suite status. Parent retention cases stop at their first failing 60-second assertion, so later parent expiry/teardown assertions are not separately executed. Snapshot identity checks are referential, not deep immutability checks. The no-new-frame observation is limited to the measured simulated advance, not every possible later asynchronous event. The Node guard is not an OS network sandbox. Commit-to-manifest origin is accepted from the supplied provenance; no fresh remote ref or repository-wide audit was performed.
