# Batch 2: CUA current-carrier failure triage and independent CI repair

Candidate: `019c26f65e0e59f8a8661321d63c5fb1fb105000`
Branch: `fix/image-lag-missing-base-version-20261004`
Worktree: `/workspace/lanes/cua`
Base: current upstream main `0335d5a5e0fd197522365fef3487a279be94ad4f`
Independent H4 review: APPROVE from `/root/hermes_gateway`; no correctness findings.
Publication: pending parent; no push, PR edits, upstream messages, reruns, merge or deploy.

## Concrete fix

The current image-lag workflow unconditionally read the PR base's
`libs/cua-spacesd/VERSION`. Bases predating cua-spacesd lack that file; even the
warning-only check exited128 before evaluating image lag. #87's pinned base
`2ca90d33857fdb4813ecc8d12c2058be7d4ebcc4` lacks that path (GitHub contents API404).
Its hosted job111308484971 failed the scope step with exit128. The same defect
reproduces with synthetic local history on current upstream's workflow.

Fix treats an absent base VERSION as introduction, preserving the existing
version-change skip route. A missing/invalid base revision still fails during
fetch; existing changed/unchanged routes remain unchanged. Head-file failures
remain failures. Only workflow plus regression file changed. Original #4574
implementation/ancestry preserved; source PR metadata in `cua-batch2/source-pr-4574.json`.
No guarded-completion, #111, motion, credentials or permission changes.

Validation:
- Before fix: new absent-file test fails with128, other 2 tests pass.
- Final source: `python -m unittest discover -s scripts/images/tests -p test_lag_scope.py -v`: 3 pass (4 synthetic histories including invalid-base negative control).
- `python -m unittest discover -s scripts/images/tests -p test_image_pins.py -v`: 23 pass.
- `git diff --check`: clean. These tested files are unchanged in commit019c26f.
- Tests use standard library and local Git only; no dependencies installed.
- Hosted CI for candidate: NOT_RUN; no real image/release/registry validation claimed.

## Existing carrier evidence refreshed

#87 remains at `b2ae7cb934403f2585c7d3ed23a188b44264f293` with same13 failures.
Its current base is pinned `2ca90d33857fdb4813ecc8d12c2058be7d4ebcc4`.
GitHub reports5,511 changed files and comparison186 commits ahead/0 behind;
this is not a guarded-only comparison. Existing #111 divergence remains an
owner reconciliation decision; it was not restacked or ported.

The exact release-title validator from b2ae7cb9 reproduces failure for current
#87 title `ci: validate guarded completion on upstream 9545a3d` with
`validate-title --require-release`. That confirms title/product-scope mismatch,
not an authorization to edit the owned PR or bypass release metadata.

All13 jobs' public metadata and annotations were downloaded, recording exact
head, failed step, and annotation in `/workspace/receipts/cua-batch2/failure-details.json`.
Direct log downloads redirect to an Azure Blob endpoint returning Forbidden;
signed redirect URLs are omitted from retained failure files. No job was rerun.
This blocks exact stderr diagnosis for remaining jobs; exit codes alone do not
establish causes. No failure was dismissed as unrelated to its tested tree.

| Failed jobs | Observed failing step / evidence | Next action |
| --- | --- | --- |
| Docs image refs | baseline/doctor check; annotation says no image-doctor-ledger branch | Owner inspect baseline refs against intended comparison; missing ledger alone does not identify failing refs. |
| Image doctor | cua-sandbox composite action exits1 | Obtain authorized job log; action/package cause unknown. |
| Catalog lag | scope exits128; base VERSION absent | Candidate019c26f above, independently reproduced. |
| Windows signed0.28.2 | Download published Windows archives exits1 | Obtain download stderr; no signing/runtime failure proven. |
| Three Linux installer smoke jobs | served-release installer exits1 | Obtain failed logs; no local container/installer execution. |
| Portable parity | live-registry proof exits101 | Obtain Rust stderr; cargo unavailable locally, no install. |
| Three generated reference jobs | Check generated reference exits1 | Obtain generator diff/build stderr; no drift cause inferred. |
| Documentation sync | aggregate gate exits1 | Downstream consequence of failed selected reference checks, not independent evidence of another generator defect. |
| Release validate | squash-release title exits1 | Existing owner choose intended base/scope and corresponding accurate title; local exact-script reproduction recorded. |

Useful next choices: review/publish independent CI repair; owner reconcile #87's
old pinned base and title; obtain authorized logs for remaining precise failures;
keep #111 current-head/guarded carrier reconciliation with its existing owner.

Exact post-commit validation: combined unittest invocation on019c26f ran26 tests, all pass; log `cua-batch2/019c26f-final-tests.log`. Full13-row disposition with exact job links: `cua-batch2/failed-checks.md`.

Documentation-only child: `9846bb67a927ef1320bce577c4bbae1ea2974c12` publishes
13-row `evidence/guarded-carrier-failures-20261004/README.md`. Code remains exactly
019c26f; no additional runtime rerun warranted. Independent docs review requested.
