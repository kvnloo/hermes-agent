# Six-lane follow-through, batch 2 — 2026-10-04

This batch reused the existing six worktree slots. Hermes current upstream was
still `24b9f0f8c5df5ec6d3d5c10ad9b27c3346bbc925`; the new independent CUA repair
uses upstream `0335d5a5e0fd197522365fef3487a279be94ad4f`. Unchanged qualification
suites from batch 1 were not repeated. Two lanes narrowed to independent review
after public owner checks found no suitable independent implementation.

| Lane | Concrete result | Receipt |
| --- | --- | --- |
| Hermes 1 MCP | Real synthetic stdio discovery reuses a child; explicit teardown is a working negative control. 2 passed; reported lifecycle failure remains unproven. | [MCP](h1-mcp.md) |
| Hermes 2 composition | Attachment alone: 2 failures at rotation. Adding banozz0's unchanged owner patch: same 2 pass. Final composed tree: 10 focused tests pass. | [Composition](h2-composition.md) |
| Hermes 3 providers/review | #132410 still lacks public error shape and retry budget. Independently reviewed composition proof. | [Providers](h3-provider-review.md) |
| Hermes 4 review | Independently reviewed CUA repair, all 13 failed-job records, and package-policy proof. | [Review](h4-independent-review.md) |
| Hermes 5 package policy | Both owners' proposed seven-entry policies omit dependency-group distlib. Generated-policy proof: 2 expected failures, 1 control pass; no competing fix. | [Policy](h5-package-policy.md) |
| CUA | Independently repaired historical-base VERSION absence; 26 tests pass. Triaged 13 existing failed jobs without inventing inaccessible stderr. | [CUA](cua.md) |

## Downstream deliverables

- [MCP consumer test 97e24e3e](https://github.com/kvnloo/hermes-agent/commit/97e24e3e0162b6501b4c85d9d31a328d6c1366d6),
  branch `evidence/mcp-discovery-reuse-20261004`. Test-only, root reviewed, exact
  committed test passed. It does not reproduce macOS launchd or a full gateway
  startup/turn transition and does not close #132397.
- [Pool composition 0d8d04fc](https://github.com/kvnloo/hermes-agent/commit/0d8d04fca1986cd62fe679ad9f97bb99cbbe63f7),
  branch `evidence/pool-model-composition-20261004`. Original PR132231 source
  `2a91d03d81a4962ca6f159fdb06b3feaf5c4223a` was cherry-picked as `a39e56cfdc`,
  retaining banozz's author/date and identical patch identity. The new consumer
  composes it with gateway `40b59b2144`; it does not replace or promote its owner.
  Proof ends at direct pool rotation, before the actual agent-turn transport,
  credential swap/retry and provider-fallback ordering.
- [CUA repair and failure ledger 9846bb67](https://github.com/kvnloo/cua/commit/9846bb67a927ef1320bce577c4bbae1ea2974c12),
  branch `fix/image-lag-historical-base-20261004`. Runtime/workflow repair is
  parent `019c26f65e`, tested on that exact SHA; the child only adds documentation.
  Missing base VERSION follows the existing introduction/version-change skip
  path. Invalid revisions still fail. Existing changed/unchanged cases pass.
  Both repair and ledger independently reviewed.

The [package-policy probe](quarantine-consumer-probe.py) belongs in evidence,
not a permanent green test suite. To reproduce, copy it into
`tests/pm/test_exact_pin_quarantine_consumer_probe.py` on the recorded Hermes
base and use the canonical runner command in its receipt. It deliberately
produces two failures and one pass. Only owner policy deltas were simulated;
full owner branches, mirror resolution and native Windows were not qualified.

## Remaining evidence and owner decisions

1. CUA: current carrier #87 compares against old pinned base `2ca90d3385` and
   reports 5,511 changed files. Its current title fails the exact-head release
   title validator when product release scope is required. The owner must
   select the intended base/scope/title; no owned PR was edited. #111 remains
   divergent and is not silently ported or restacked.
2. Most CUA failed-job root causes remain unknown because authorized log
   download redirects returned Forbidden. Metadata/annotations are recorded;
   exit codes do not prove signing, installer or generator causes. Cargo and
   Jev-use runtime dependencies were unavailable; no installs or reruns occurred.
3. Hermes package-policy owners PR130838/132300 need dependency-group coverage
   and source/lock parity for distlib. The private parent receipt is ready;
   no public solicitation or competing implementation was made.
4. MCP needs a synthetic fixture of the actual warmup-to-run/scope/process
   transition before a runtime fix. Fallback #132410 needs public sanitized
   exception details and effective retry budget before connecting it to the
   already-owned cap fixes PR129895/130855.

All delivery is downstream-only. No upstream PR/message, active-owner branch
edit, merge, deploy, canceled-workflow rerun, real credential mutation, auth
guard override, paid provider call or dependency installation occurred. Git
publication uses existing authorized GitHub REST Git objects because Git HTTPS
push returned 401; exact object IDs, parents and authors are preserved, with
fast-forward-only updates and remote verification. Hosted candidate CI is
reported separately from local tests and remains unqualified at handoff.

Receipts preserve worker handoff status; the parent's final remote verification
supersedes their earlier pending-publication wording. The standing three-PR
limit, parked drafts and holds **123578**, **417 NOT_MET**, **131689 needs
decision** remain. Prior batch evidence is [here](../six-lane-20261004/README.md).
