# Focused factory follow-through — 2026-10-04

The six roles narrowed to three concrete workstreams plus independent review:
MCP lifecycle consumer, existing-owner systemd integration, and exact CUA hosted
check clarification. The ingress/cache/profile gate found no distinct unowned
maintainer contract, so it did not create open-ended qualification work. Previous
turn-recovery and session suites were not repeated.

## Delivered Hermes evidence

- [MCP warmup consumer e265fe86](https://github.com/kvnloo/hermes-agent/commit/e265fe8633b97facf0807014340911f06e231f67),
  remote `evidence/mcp-warmup-agent-consumer-20261004`, base
  `ea81748579ee1732d214ccb75f91d22208ed623d`. **2 focused tests passed** on final
  source, committed without edits. Actual gateway discovery and warmup, real
  AIAgent direct schema construction, and registry RPC retain the same healthy
  child. Explicit teardown loses the tool without respawning. Network guards
  recorded zero attempts in final parent phases. Only unrelated metadata is
  stubbed; direct tool mode and disabled local runtime use supported settings.
  [Receipt](mcp-warmup.md), [independent review](mcp-review.md).
- [Systemd owner integration fba7a46a](https://github.com/kvnloo/hermes-agent/commit/fba7a46a454a004e8fc1966d3bde1dbb2c3c5588),
  remote `evidence/systemd-owner-integration-20261004`, same fresh base.
  All three **happy5318** PR124082 commits are unchanged cherry-picks with
  original authors/dates, including the empty author email. The new outer
  startup consumer fails twice on the base's phantom90s result, then the exact
  integrated head passes **15 selected tests**. This covers false-warning
  suppression while retaining a real short-budget mismatch. No systemctl,
  service, process-inspection or live diagnostic invocation occurred.
  [Receipt](systemd-integration.md), [independent review](systemd-review.md).

Both exact remote SHAs were verified. Each has zero observed check runs at
handoff; local test success is not hosted CI success. The systemd REST upload
rejected an original empty author email, but standard Git push subsequently
succeeded using existing credentials. Exact history was preserved; no identity
rewrite, stored credential change or partial integration ref was needed.

The MCP result does **not** reproduce or fix132397. It qualifies the stated
single-profile Linux schema/registry path in direct-tool mode, not the default
tool-search executor, model turn, launchd, third-party server or multiplex
lifecycle. A causal reporter transition remains necessary before a runtime fix.

## CUA: exact repair and unresolved qualification

[Published branch](https://github.com/kvnloo/cua/tree/fix/image-lag-historical-base-20261004):
`fix/image-lag-historical-base-20261004`, head
`9846bb67a927ef1320bce577c4bbae1ea2974c12`. Code is parent
`019c26f65e0e59f8a8661321d63c5fb1fb105000`, based on `0335d5a5e0fd`.
Only `.github/workflows/ci-images-spacesd-lag.yml` and
`scripts/images/tests/test_lag_scope.py` change executable/test behavior; the
child adds only the13-job disposition ledger.

The repair handles a valid historical base that lacks
`libs/cua-spacesd/VERSION`, while invalid base revisions still fail. Exact code
has **26 local passes** and independent review. These tests were not repeated.

Fresh hosted evidence is more precise than earlier time-scoped NOT_RUN wording:
[Image API job111355013867](https://github.com/kvnloo/cua/actions/runs/37174772647/job/111355013867)
passes on019c26f, but its workflow does not exercise the repaired image-lag job
or new regression. Documentation head9846bb6 has zero check runs. **Targeted
hosted image-lag validation remains unobserved.**

Original carrier87 is still `b2ae7cb934403f2585c7d3ed23a188b44264f293` with
202success/23skip/**13fail**. A separate repair branch does not clear any of
those results. Base VERSION absence is locally causal and consistent with the
failed scope step's128, but exact hosted stderr was unavailable (Forbidden).
Other failure causes remain bounded by metadata; no whole-carrier clearance.
[Exact check receipt](cua-exact-checks.md), [independent review](cua-review.md).

## Remaining choices

1. Owner/parent may request normal targeted hosted CUA qualification on the
   selected final candidate. This batch dispatched or reran no workflow.
2. Systemd124082 now has a preserved-current-base downstream integration proof;
   upstream owner/carrier selection remains unchanged, no competing PR opened.
3. MCP needs the actual process/profile/reload/reconcile/child-failure transition
   before attributing132397 or writing a fix. Successful healthy-path proof is
   not a general cannot-reproduce verdict.

No dependency installations, upstream communication, owner-branch edits,
security-bypass reproduction, paid/live providers, merge or deployment occurred.
The three-PR limit and prior holds123578,417NOT_MET,131689 remain. CUA111/4316,
FIX04, compiled replay, accounting, motion, privacy and queue gates were not
changed. Worker pending-publication statements are superseded by the remote
verification above. Prior evidence: [batch3](../six-lane-batch3-20261004/README.md).
