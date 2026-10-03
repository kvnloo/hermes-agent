# Canonical compression follow-up request lifetime

Final candidate `4104b5047794e22ca51f491d29b5636d080b5c1d` directly extends [Teknium's current #106742](https://github.com/NousResearch/hermes-agent/pull/106742), source `cb8d6920549ebe9d31f69f187d30b356b5639eed`. Exact tree/parent/new downstream ref are in publication-map.json. No merge, upstream post, installation, paid call, workflow rerun, deployment or auth change.

## Concrete correction and attribution

Canonical compression receives a mutation receipt and then resumes the session to refresh its transcript. The existing settle callback discarded the caller's timeout and AbortSignal for that follow-up. The single production-line correction forwards the same optional `timeoutMs` and signal into the existing request callback. This preserves the per-RPC allowance; it does not create an overall elapsed deadline, retry policy, backend cancellation or rollback.

Credit Teknium for the canonical adapter and [ahrazzle review5296408057](https://github.com/NousResearch/hermes-agent/pull/106742#pullrequestreview-5296408057) for identifying the lost options. The review explicitly identifies automated posting with human oversight; it is not represented as independent human-maintainer direction. Codex authored the scoped correction and two consumer cases under Kevin Rajan direction.

## Exact-source comparison

Same three-file selection, identical test bytes, actual candidate/source worktrees:

| Source | Result |
|---|---|
| Exact original cb8d plus new test overlay, no production substitution |22 existing PASS,2 new FAIL|
| Exact4104 candidate |24 PASS:22 existing plus2 new|
| Independent focused final consumer execution |2 PASS, no blocker|

Both negative failures are observable pending-versus-rejected assertions, separately for caller abort and configured follow-up timeout. They are not import failures, test-harness deadlines or source-text assertions. Existing protocol/channel tests pass in both arms. Independent reviewer verified exact source/test bindings and inspected negative receipts without repeating the entire matrix. Root reviewed the production line and complete new tests.

The tests traverse actual HermesGateway, CanonicalDesktopProtocol, JsonRpcGatewayClient and JsonRpcRequestChannel through a finite in-memory WebSocket EventTarget. A public session.resume primes canonical revision/generation state; no private-cache patch or mocked protocol callback supplies the behavior. Deterministic fake timers establish:

- Abort after resume dispatch rejects the original consumer with AbortError; a late response cannot reverse cancellation. Preview retains its single-request/report behavior.
- Successful compression returns the refreshed transcript. A later request consumes900ms before the compression receipt, then gives resume its full configured1000ms. Timeout rejects that follow-up at its own boundary and clears pending timers. This deliberately proves a per-RPC budget, not a1000ms total operation deadline.

Existing Node24.19.0 and Vitest4.1.10 reused without installation. The bounded external Vitest configuration aliases the shared package to the active worktree's source. This is not the full Desktop/Electron runner, full typecheck or UI qualification. No real socket, gateway daemon, authentication provider, model execution, native browser cancellation, server mutation rollback or whole-PR approval is claimed. Nearby async-settle bookkeeping, prerequisite attachment calls and download timeout policy are unchanged and unqualified by these two cases. Current main snapshotbd0affe has no canonical adapter; this qualifies the owner candidate, not main or the other hosted integration branches.

## Continued queue discipline

This work followed published current-source cancellation/consumer receipts at [4520aa9f](https://github.com/kvnloo/hermes-agent/tree/4520aa9ff8bd74e07474cb7b09d269348ee1e643). Completed integrations were not reopened merely to create new test counts.

Read-only follow-up checks ruled out stale work or retained explicit decisions:

- Fork70's old busy-holder checkpoint expectation conflicts with main's newer exclusive/quiet-only checkpoint contract. No backport or obsolete acceptance test was created.
- Closed backup106011 remains under issue317's individual hold. Active owner124710 already has independent same-head consumer evidence; integrating its older backup series into main would need to preserve newer error/publication contracts and reconcile critical-file scope. No wholesale resurrection or duplicate106-case run.
- Kevin's combined TUI notification invariant across129524/129525/129526/129556 is explicitly conditional on the separate slices landing. They remain open; no pre-landing composition or leaf rewrite was performed.
- CPU headroom105423 and external-memory130976/130997 need owner policy decisions, not unilateral budget changes.
-123578 remains owner-contract HOLD based on automated review,417 acceptance HOLD,131689 needs-decision. Library/native-environment limits remain. Concurrent token-addressing/CUA and Bend work belongs to its separate owner and supplies no implicit approval here.

Exact candidate workflow audit inspected51 definitions: no create event or push filter matching the new reviewed branch. Publication uses new refs only and no tags; the evidence root has no workflows. Post-publication verification binds remote commit/tree and reads Actions/check/status results. Empty hosted CI is NOT_RUN, never PASS. Raw logs/full bindings remain local; this is sanitized public provenance and bounded evidence, not blanket upstream promotion authority or a claim that the entire queue is exhausted.
