# Admitted provider-error Retry evidence

Base: `3eb7ed08d19da393196722d0b219b2ba1ec22810` (upstream main).
Fork branch: `dot/hermes/admitted-provider-error-retry`.
Coordination: [fork #447 claim](https://github.com/kvnloo/hermes-agent/issues/447#issuecomment-6092414639).

## Bounded fix

`isFailedUserTurn` previously treated every user followed by `assistant.error`
as never submitted. A positive safe-integer `rowId` proves durable admission,
even when a provider error arrives before the submit ACK. Such a turn must keep
its durable Retry address and backend user-ordinal slot. Truly unadmitted turns
still use a plain resubmit.

The frozen regression mounts the real submit, session-cache and stream hooks.
Only RPC acceptance and metadata/hydration IO are mocked. It covers provider
error before/after ACK, Stop before either ordering, persisted failed-turn
projection, a newer persisted user, survivor rebinding, and invalid/unadmitted
row identities including zero. Base: 3 failures / 8 passes. Patch: 11 passes;
eight adjacent files: 122 passes. This is frontend execution, not a live model,
gateway-network, Electron application or cross-platform test.

The original `rebindSurvivorRowIds skips failed turns` fixture supplied `rowId=1`
while describing a user that was never persisted. Its corrected fixture uses
`undefined`, still requires that user to remain untouched, and still requires
the next admitted user to consume survivor slot zero. The original failing run
is retained in `outputs/original-fixture-failure.txt`; the admitted-survivor positive
case is in the frozen regression. Independent review checked this correction
and independently reproduced the final RED/GREEN comparison.

## Known pre-existing repeated-Retry limitation

The independent audit found a separate gap in the existing rewind ACK path:
`runRewindSubmit` returns survivor IDs without binding the replacement ACK's
`user_row_id`. After replacement ACK `{user_row_id:15,
survivor_row_id_map:{"13":null}}` (or `survivor_user_row_ids:[]`), another provider
error before hydration can make the _third_ submit lose both row address and
confirmation. Both cases fail identically on base and patch. The audit's other
two admitted controls fail on base and pass on patch; its hidden-user control
passes on both.

The unchanged executable audit source is preserved as
`critic-admission-boundaries.tsx.txt`, deliberately outside automatic test
discovery because it contains the two known failing cases. In a disposable
checkout with pinned dependencies, materialize and execute it with:

```sh
cp tests-js/evidence/admitted-error-retry/critic-admission-boundaries.tsx.txt \
  apps/desktop/src/app/session/hooks/use-message-stream/critic-admission-boundaries.test.tsx
cd apps/desktop
npx --no-install vitest run --project ui \
  src/app/session/hooks/use-message-stream/critic-admission-boundaries.test.tsx \
  --maxWorkers=2 -t 'critic admission boundaries'
```

Expected audit result: base 4 failures / 1 pass, patch 2 failures / 3 passes;
the 11 unselected tests are not passes. Raw results are in
`outputs/independent-controls-{base,patch}.txt`. No production rewind, reload or
deep-confirm code was changed. The broader data-loss report
[#135604](https://github.com/NousResearch/hermes-agent/issues/135604) remains
unconfirmed and is not claimed fixed.

## Attribution and verification limits

- Investigation lead: @trusktr's #135604 report.
- Original failed-submit ordinal/classifier work: @vondelomlo, commit
  `c2a50a86620c573bdfae4b401803dc47b82672a7`, based on #41275.
- Failed-turn retry guard: @JoaoMarcos44, #86623.
- Durable row addressing: @teknium1, #87294.
- Row-ID/ordinal separation: @NorethSea, #90661.
- This bounded classifier refinement and independent automated review: dot/ayo.

`receipt.json` records exact commands, final hashes and outcomes. Superseded
typecheck exits 137 and a code-health baseline timeout are preserved as resource
failures; they are not passes. Node 24.19.0/npm 11.9.0 are supported by the project.
Python 3.12.14 was used only for `scripts/check`, which explicitly supports 3.11+;
no Python application/runtime validation is claimed.
