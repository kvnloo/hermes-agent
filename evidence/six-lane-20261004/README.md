# Six useful execution lanes — 2026-10-04

This bounded batch used five isolated Hermes worktrees on upstream
`24b9f0f8c5df5ec6d3d5c10ad9b27c3346bbc925` plus one CUA worktree. It delivered
one reviewed functional fix and consumer/ownership evidence. It did not find
five unowned defects, and did not manufacture patches to meet a lane count.

| Lane | Outcome | Local validation |
| --- | --- | --- |
| H1 CLI/config | Qualification and 33 owner exclusions; independent H2 review | 28 passed on unchanged base |
| H2 gateway | Effective session model reaches both pool-attachment consumers | Base 2 failed/1 passed; final 5 passed |
| H3 agent/providers | Generic fallback consumer proof; low-budget failure already owned | Existing suite 19 passed; final synthetic control 2 passed |
| H4 tools/plugins | Web consumer qualification; MCP stderr location verified; independent CUA review | 13 web tests and 1 real-child startup test passed |
| H5 TUI/session | Qualification only; independent H3 review | 97 passed in 16 files on unchanged base |
| CUA | Current-head/check/source evidence reconciled | JSON, captured API records, source identities and independent review |

H5's 97 passes are existing synthetic/local contracts for session generation,
resume, profile database/cwd/images, message visibility, usage, submission and
turn payloads. There was no fixed defect and no negative control. They neither
resolve the excluded owners' reports nor establish live-client/platform parity.

## Reviewed deliverables

- Gateway fix: [40b59b2144](https://github.com/kvnloo/hermes-agent/commit/40b59b21440c6e9c723c49e4f74dfbaf019b455d),
  downstream branch `ready/gateway-override-pool-model-20261004`. Human reporter
  **banozz0** credited. Parent independently reran the two focused files on this
  exact committed SHA with `--file-retries 0`: **5 passed**, 2026-10-04. Temporary
  profile fixtures honor the auth-store guard; no real credentials, production
  settings, auth-guard overrides, or live inference were involved.
- CUA ledger: [0afff680](https://github.com/kvnloo/cua/commit/0afff680782e2f15a10f8c61db9eb6804f34c89c),
  downstream branch `docs/guarded-consumer-evidence-20261004`. It preserves
  existing #111/#4316 ownership, commits and human credit. Its new documentation
  has no runtime change; existing hosted checks are historical evidence, not a
  new hosted run by this batch.

The per-lane receipts record the point at which each worker handed off. Their
"publication pending" statements are superseded by the parent's final delivery
report. No upstream PR/comment, existing PR edit, merge, deploy, workflow rerun,
dependency installation, or stored Git/auth configuration change was made.
The standing three-open-PR limit did not authorize closing existing PRs; no new
upstream PR was opened. Existing parked drafts and all specified holds remain.

## Actionable next choices

1. Review the gateway attachment patch for downstream consumption. It is partial
   acceptance of #132232: the model-aware second-account rotation contract stays
   with #132231. Qualify that composition only after selecting its final owner
   revision; do not claim a live Discord turn was tested here.
2. Let the CUA #111/#4316 owner reconcile stale SHA/CI wording and decide how to
   compose the existing divergent commits. The current carrier has 13 failing
   downstream checks, undiagnosed here; matching guard blobs do not prove runner
   or full-tree parity. The ledger links exact jobs. Do not duplicate a port.
3. For fallback #132410, obtain sanitized xai error status/body and effective retry
   budget. The budget-one failure already has owners PR129895/130855; generic
   custom-provider proof does not establish xai/Codex equivalence.
4. For MCP #132397, the next useful input is a synthetic warmup-to-run handoff
   reproduction or a reporter-provided redacted profile `logs/mcp-stderr.log`.
   The existing startup-diagnostic proof does not explain the two-wave failure.

Missing CUA runtime dependencies are importable Python `typesafe` and local
Jev-use TypeScript dependencies. They were not installed. This did not block
the independent evidence audit. Hermes used the installed test interpreter;
the unmodified canonical runner needed scoped write access to `/var/tmp`.

No broad suite, paid model calls or security-bypass reproduction was used.
Hosted CI for these new deliveries must be reported separately from local tests.
Recover [ARTIFACTS.md](ARTIFACTS.md) before assigning another batch so completed
qualification and active owners are not rediscovered as new work.
