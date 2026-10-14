# Streaming timestamp continuity: exact-head execution evidence

## Result

**FAIL_GAP / LIMITED: the existing author-requested minute-boundary invariant fails. No production fix is included.**

On PR [NousResearch/hermes-agent#111511](https://github.com/NousResearch/hermes-agent/pull/111511), exact head `0b58039b7c1f77dd54fa0cd080f794a11002bd49`, the real streaming component keeps `[12:59]` while a reply streams; the settled component renders `[13:00]` after completion across the minute boundary. A same-minute control renders `[12:59]` in both forms.

First targeted run: **26 passed / 1 failed across five files**, exit 1. Independent rerun: **26 passed / 1 failed**, exit 1. The sole failure is the new equality assertion comparing the rendered live and settled labels. Existing timestamp-on/off, persisted-value, transcript and adjacent turn-controller controls pass. Both runs reported no offline-guard diagnostics.

The [September 27 request](https://github.com/NousResearch/hermes-agent/pull/111511#issuecomment-5853446302) is Kevin/kvnloo’s own review comment, not an upstream maintainer requirement or formal review. This evidence addresses that existing request; it does not establish maintainer acceptance or authorize promotion. Preserve kvnloo’s implementation ownership and the PR’s original Muse-assisted contribution credit. Downstream tracking: [#500](https://github.com/kvnloo/hermes-agent/issues/500).

## Executed boundary

The authored test imports and executes the real `turnController`, nanostores, `StreamingAssistant`, `appendTranscriptMessage` and `MessageLine`, with real `@hermes/ink` rendering into in-memory streams. Only `Date` is faked; actual controller/React/Ink timer scheduling runs. The test streams a second delta after advancing the clock and verifies that the live label stays fixed before completing the reply.

The test directly calls controller methods and the append helper in the same order as the completion path. It does **not** execute `createGatewayEventHandler`, `AppLayout`, a live terminal, Python gateway, session persistence/reload or a model/provider. It is native-component integration evidence, not an end-to-end application result.

Production sources are unmodified. [StreamingAssistant](https://github.com/kvnloo/hermes-agent/blob/0b58039b7c1f77dd54fa0cd080f794a11002bd49/ui-tui/src/components/streamingAssistant.tsx) captures its own burst-start timestamp. [recordMessageComplete](https://github.com/kvnloo/hermes-agent/blob/0b58039b7c1f77dd54fa0cd080f794a11002bd49/ui-tui/src/app/turnController.ts#L629-L747) emits the final assistant row without `createdAt`; the [event handler](https://github.com/kvnloo/hermes-agent/blob/0b58039b7c1f77dd54fa0cd080f794a11002bd49/ui-tui/src/app/createGatewayEventHandler.ts#L1542-L1588) appends it; [appendTranscriptMessage](https://github.com/kvnloo/hermes-agent/blob/0b58039b7c1f77dd54fa0cd080f794a11002bd49/ui-tui/src/lib/messages.ts#L5-L11) supplies the later wall clock. A repair must preserve supplied/persisted timestamps and existing append-time fallback semantics.

## Provenance and environment

Commit `0b58039b7c1f77dd54fa0cd080f794a11002bd49` has actual root Git tree `a2efc59fc2ca61ca5436fbc5d8486461d035f5d2`. The frozen `source-manifest.json` field named `root_tree` mistakenly contains the requested commit treeish; `root-tree-correction.json` explicitly corrects it. Both critics verified all 589 blob/content hashes, and the source critic independently reacquired commit→tree→path mappings. The frozen original is retained unchanged.

The raw authored test assumes UTC for its `[12:59]` fixture. Always use the wrapper’s `TZ=UTC`; the test alone is not a timezone-portable ready-to-land regression.

- Linux x86_64; PM Node 26.7.0; native Vitest 4.1.10. React 19.2.7, react-reconciler 0.33.0, Vite 8.2.0, esbuild 0.28.1, nanostores 1.4.2, @nanostores/react 1.1.0 match the committed lock.
- This was a **partial exact-head tree**, not a complete Git checkout: 589 source/configuration files covering `ui-tui`, `apps/shared` and listed root files. Every file was verified against its Git blob SHA. 586 blobs came from existing local Git objects; three PR-specific blobs came from the exact-ref GitHub connector. Post-run verification found zero mismatches.
- `source-manifest.json` records exact Git identities; `materialization.json` records file SHA-256 and retrieval provenance. These identify original inputs, not the added evidence test or generated Ink bundle.
- Dependencies were copied into the disposable tree from an existing canonical npm-ci installation with a byte-identical committed root lock. No dependency installation or version substitution was performed here. Root lock SHA-256: `9934677654ce672900b0946898cc28c73671f75896862b5768c24cca84776ccd`. Workspace links resolve inside the partial exact-head tree.
- Exact-source `npm run build:ink --prefix ui-tui` passed. Scoped ESLint on the authored test passed with no diagnostics.
- The test run uses an empty inherited environment plus explicit temporary HOME/HERMES_HOME/runtime/cache, UTC/C.UTF-8 and a fail-closed networking guard. The guard changes no timestamp, rendering, store or completion logic. It is a narrow accidental-network safeguard, not a claim of complete kernel isolation.

## Reproduction

Use an isolated checkout at exact head `0b58039b7c1f77dd54fa0cd080f794a11002bd49` with dependencies prepared from its committed lock and a supported Node version. Dependency preparation is separate from the evidence run; this packet never installs packages.

1. Copy `streamingTimestampContinuity.test.tsx` to `ui-tui/src/__tests__/streamingTimestampContinuity.test.tsx`.
2. From that checkout, run `npm run build:ink --prefix ui-tui`.
3. Run `bash /path/to/this/packet/run-targeted.sh /path/to/checkout`.
4. Expected result on this head: 26 pass, 1 fail; the crossing-boundary label equality fails with received `[13:00]`, expected `[12:59]`.

The portable wrapper expresses the same five-file command and environment isolation as the executed absolute-path wrapper. The portable wrapper itself was not separately rerun. Full original command identity and artifact hashes are in `verification.json` when the review receipt is finalized.

## Limits and next boundary

No base-versus-fix or RED-to-GREEN claim: this is a new failing invariant on the current PR head, with a same-minute control. No production patch, current-main test, full TUI suite, aggregate check, typecheck, i18n IPC, live network, native GUI/terminal, Python gateway, session rehydration, CI-green, merge or release claim. Existing exact-head CI/Nix/Docker runs require action approval.

The smallest repair boundary is a message/segment timestamp shared by the streaming representation and its settled counterpart. That design must preserve meaningful per-message/segment chronology and lifecycle resets; a global append-helper change would risk unrelated semantics. Interrupted, interim/tool-separated, resumed and subsequent-turn paths remain untested by this two-case probe.

Independent review and execution logs are included as separate receipts. No origin-facing action is part of this packet.

Reviewer frozen hashes identify the original local artifacts. Sanitized public log/review copies and the portable wrapper can have different hashes; `SHA256SUMS` and `verification.json.artifacts` identify this published packet. Earlier local qualification files remain a historical source-only checkpoint, superseded by this execution receipt.
