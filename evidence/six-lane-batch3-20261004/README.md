# Factory continuation and source boundaries — 2026-10-04

This batch reused the same six slots. One lane produced a new integration
consumer test. Other lanes narrowed to current-source and independent review
when fresh reports already had owners or lacked a causal fixture. No unchanged
qualification suites were rerun to fill a roster.

## New integration evidence

Deliverable: [72f212b2](https://github.com/kvnloo/hermes-agent/commit/72f212b2d85bd91dc7c16b6c38deb55e4b9643ef),
downstream branch `evidence/pool-turn-recovery-20261004`. Exact final committed
test: **1 passed in 3.55 seconds**, retries disabled; independent review approved.
Hosted CI **NOT RUN** at handoff. Production code is unchanged from the selected
owner composition; this commit adds only the test and its receipt.

The new pool-turn consumer composes previously delivered gateway attachment
with banozz0's unchanged PR132231 patch, retaining its original-author ancestry.
It selects runtime through the real gateway method, manually constructs a real
`AIAgent`, and runs a conversation through SDK HTTP parsing and actual credential
recovery. Synchronous HTTP transport is replaced before resolution/constructor
with authored synthetic responses; unexpected asynchronous requests fail.
Temporary profile rows contain synthetic keys only; production auth guards and
settings are unchanged.

The first response returns a synthetic usage-limit 429. With the owner patch,
the real loop selects seat 1, rebuilds the client, sends the expected model and
synthetic Authorization header, and returns `Recovered` without provider fallback.
The negative control restores only the owner's credential-pool changes: the
same test completes through the synthetic fallback and fails its `Recovered`
assertion. The full owner source was restored before final commit/validation.

This extends the earlier direct-pool proof, not live-provider qualification.
It does not cover message ingress, full GatewayRunner orchestration, cache lease
lifecycle, OAuth refresh, concurrent sessions or multi-profile A→B→A behavior.
The initial malformed synthetic SSE fixture failure is explicitly excluded from
product evidence. See the final [consumer receipt](pool-turn-consumer.md) and
[independent review](independent-review.md).

## Source findings and held work

- [CUA boundary audit](cua-boundary.md), independently checked in
  [source review](source-review.md): factory CI repair019c26f/docs9846bb6 do not
  overlap staged FIX04, compiled replay, accounting or queue work. #111's green
  checks do not qualify those broader scopes. Wave7's historical carrier SHA
  is kept separate from later current-head evidence. No new CUA edits or tests.
- Queue readiness remains **0/55**. B09/R2-07f have **zero measured trials**;
  live modal fallback **0/4**; toggle bound **+2.2 ms**, not +2.0 ms. Owner,
  recertification and privacy gates remain. No unpublished artifacts or runtime
  reproduction was accessed, and the parent's cross-repository audit stays
  separate from this factory work.
- [Systemd132565](systemd-owner.md) duplicates owner124082, which Kevin already
  reviewed. Current source matches that owner's base. No new systemctl action,
  competing implementation or redundant test was justified.
- [MCP lifecycle audit](mcp-lifecycle.md) traced distinct startup, warmup and
  turn paths. It found no unconditional second connection. The report still
  needs a concrete process/scope/reload/reconcile transition before a fix.

Current Hermes main advanced from24b9f0f8 to20bd00439cfc2e8d6d296f28fba0cdeeb6cdda49
through four WhatsApp-only commits. Relevant pool/MCP files are unchanged; this
is not a rebase or whole-main-green claim. The new test remains on the selected
original-author composition source and is qualified at its exact final commit.

No upstream communication, active-owner branch changes, dependency installs,
paid/live providers, real credential mutations, auth-guard changes, workflow
reruns, merge or deployment occurred. Hosted checks remain separate from local
results. Prior holds123578,417NOT_MET,131689 and the three-open-PR limit remain.
Worker receipts retain handoff status; the parent's final remote verification
supersedes pending-publication wording. Prior packet:
[batch 2](../six-lane-batch2-20261004/README.md).
