# Independent timestamp evidence review

Verdict: ACCEPT the reproduction of the timestamp continuity defect at head `0b58039b7c1f77dd54fa0cd080f794a11002bd49`, restricted to partial-tree, native-component integration for a normal single-burst reply. This is not full gateway/App/backend or full-suite qualification, a fix, merge readiness, or maintainer acceptance.

## Execution receipt and scope
The existing independent critic's frozen rerun, reviewed here, started at 2026-10-14 12:22:15 UTC and reports 26 passed / 1 failed, 27 unique tests in five files (four files passed, one failed). The failure is the intended equality invariant: live [12:59], settled [13:00]. The same-minute case renders [12:59] in both forms. Timestamp-on/off, persisted timestamp, append-time fallback/supplied timestamp, and controller-neighbor tests pass.

No extra runtime rerun was performed by this reviewer after learning the independent critic had already run it; duplicate suite executions must not be counted as additional distinct tests.

Frozen command: bash <evidence>/run-targeted.sh
Runtime: existing Node 26.7.0, native Vitest 4.1.10. The script sets a clean environment, disposable HOME/HERMES_HOME/runtime/cache paths, TZ=UTC, and the offline guard. Five test files are selected explicitly. No full suite or i18n command was run. Existing Ink build and targeted lint results are supporting worker receipts, not rerun by this reviewer.

## Fixture validity
The authored fixture imports the real turn controller, nanostores, StreamingAssistant, MessageLine, appendTranscriptMessage and Ink renderSync. It fakes Date only; real controller batching and render scheduling still execute. It waits for the actual store text and Ink output after each delta. Timestamp formatting or stamping is not reimplemented in the test: the helper extracts rendered [HH:MM] strings, then compares live and settled labels.

The fixture directly calls startMessage/recordMessageDelta/recordMessageComplete and manually reduces finalMessages through appendTranscriptMessage. It does not execute createGatewayEventHandler, useMainApp, full App, JSON-RPC or the backend. Source inspection supports equivalence for the covered normal, uninterrupted completion:
- createGatewayEventHandler.ts:1528-1531 forwards delta to recordMessageDelta.
- createGatewayEventHandler.ts:1542-1588 obtains finalMessages and sends them to appendMessage on the normal completion branch.
- useMainApp.ts:480-482 implements appendMessage through appendTranscriptMessage.
- appLayout.tsx:221-252 uses MessageLine for history and StreamingAssistant for live content with the same timestamps preference.

Real formatting uses local Date.getHours/getMinutes. TZ=UTC in the frozen wrapper makes the explicit UTC fixture and [12:59] expectation deterministic. The raw test file alone is not timezone-portable; outside this wrapper, its first assertion may fail before reaching the target invariant. Keep the wrapper command as part of this evidence. The test uses in-memory non-TTY streams and separate component mounts, not a live interactive terminal or a full screen-state assertion.

## Source/provenance checks
This reviewer recomputed Git blob SHA-1 and SHA-256 for all 589 materialized tracked files: zero mismatches. Those files equal the source manifest. Independent read-only GitHub commit/tree reads also verified all 589 path-to-blob mappings:
- commit: 0b58039b7c1f77dd54fa0cd080f794a11002bd49
- actual root tree: a2efc59fc2ca61ca5436fbc5d8486461d035f5d2
- ui-tui tree: 73b57de36aab9f78e00345e29c86f99b27f28c85
- apps tree: c7805af849aa9c23959408f2be90e885a316125d
- apps/shared tree: 91f3a9ba39bf7bb8af44b5537de79a0b573c5a40

Metadata correction: the frozen source-manifest.json field root_tree contains the commit SHA, not the actual root tree SHA. No frozen manifest was modified. independent-tree-provenance.json records the correct binding and independently fetched blob list.

The root lock is byte-identical to the prior locked installation reused by copy; no fresh install occurred. @hermes/ink and @hermes/shared workspace links resolve into this exact partial tree. Dependencies are not a fresh-install or complete dependency-integrity qualification.

## Smallest repair boundary, not implemented
The defect crosses live-message identity into controller-created settled rows:
- StreamingAssistant.tsx:41-47 captures the first rendered burst time in a component-local ref.
- turnController.ts:715-716 creates final assistant text without createdAt.
- messages.ts:10-11 applies append-time Date.now() to missing createdAt.

A narrow repair should give the live assistant reply/burst a canonical timestamp in shared controller/turn state and preserve that same value onto its settled row; the live view should consume that value. Do not globally change appendTranscriptMessage fallback or overwrite supplied/persisted timestamps. The exact onset semantics should stay aligned with the feature's intended message/burst meaning, rather than blindly using turn start, which may precede visible text.

Sibling transitions need design/test attention before calling any fix complete: flushStreamingSegment currently creates assistant segments without createdAt (482-487), and interruption creates a partial assistant row without createdAt (393). These are source-level risk observations, not extra runtime reproductions. Interim/tool boundaries, repeated turns, remounts, interruption/error and no-delta completion are untested by this new invariant fixture.

## Attribution
The request is Kevin/kvnloo's own conversation comment, author_association NONE, not a maintainer ruling or submitted formal review. Independently read source: https://github.com/NousResearch/hermes-agent/pull/111511#issuecomment-5853446302
Downstream claim: https://github.com/kvnloo/hermes-agent/issues/500
Keep kvnloo's implementation ownership and existing contribution credit.

## Frozen SHA-256 identities
- authored fixture: 5c1db1c8fc44eb46aba145b55d8340d397556f42fc5d7d397f353f8dcc9e53f2
- run-targeted.sh: db892e27daf2409f82bdf4926e7bb3be1453f73c13f8ef32d97b91dfe75e3c38
- offline-guard.cjs: b27d5d69fbd8140e5c51eb91f918476191617d6a17b0e2bd199cb957488926ac
- source-manifest.json: 7ed9cc49ee66752e701115c10bc91b781d59e531fade7eb928bad994dea42cf2
- materialization.json: 0ebb9b30a71d63d6f70dd722424308bdfa918b8afb836599de73712bc61c2307
- root package-lock.json: 9934677654ce672900b0946898cc28c73671f75896862b5768c24cca84776ccd
- independent-review.log: 052bc693b9f0b82d4d14c492fad35cdea6c5926a3ef3529857a97cd199d8323e
- dependency-source-verification.json: 8912c48391fba4e4f8b8625c00444e349d0f0cec3c353362b325e3add52e186c

No frozen source/test/runner edits, production implementation, GitHub writes, default-branch action, credential handling or denied-command retry occurred in this review. Added only this review artifact and the independent tree-provenance receipt.

