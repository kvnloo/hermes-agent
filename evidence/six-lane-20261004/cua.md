# CUA sixth lane receipt

- Worktree: `/workspace/lanes/cua`
- Branch: `docs/guarded-consumer-evidence-20261004`
- Commit: `0afff680782e2f15a10f8c61db9eb6804f34c89c`
- Base: fork main `da46c4bc85bc43f9641d3ce4b6f319e6d7b6c1a9`
- Deliverable: `evidence/guarded-consumer-current-20261004/README.md` and `ledger.json`
- Raw current GitHub responses: `/workspace/receipts/cua-current/`
- Publication: pending parent review; no push, PR edit, upstream message, rerun, merge or deployment.

Concrete outcome: corrected evidence interpretation without duplicating #111 or
#4316. Current #4316/#87 head b2ae7cb9 has passing downstream Jev-use workflow,
but #87's overall check rollup has 13 failures (not diagnosed here). #111 f74a4d5e
has 14 success/1 skipped; its PR body says hosted CI not executed. #4316 body
names obsolete 05225e2a. #111/current carrier diverged according to GitHub compare
(4 ahead/177 behind). Guard and verifier blobs are identical; Python runner is
not. #91 historical composition has no reported checks on its current head.

Validation on exact final commit: JSON parsing; four captured SHA/rollup matches;
selected checks all match raw source; eight blob SHA comparisons; whitespace
check; clean worktree. No runtime edits or redundant runtime tests. Existing
Python, Node and MCP available; importable typesafe and local Jev-use TypeScript
dependencies absent, no installs. No native/browser/live/timing qualification.

Independent reviewer: /root/hermes_tools, requested and pending.
Next: owner updates stale receipt wording; owner decides reconciliation of #111
with current carrier preserving authored commits; requalify #91 composition when
selected; triage current #87 failures by recorded exact job URLs.
