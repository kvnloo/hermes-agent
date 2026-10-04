# Batch 4: exact CUA CI repair and hosted-evidence clarification

## Publication and source

Remote branch verified through GitHub ref API:
`kvnloo/cua:fix/image-lag-historical-base-20261004`
Head: `9846bb67a927ef1320bce577c4bbae1ea2974c12`.
https://github.com/kvnloo/cua/tree/fix/image-lag-historical-base-20261004

The publication branch name differs from the local implementation branch
`fix/image-lag-missing-base-version-20261004`; the local name has no remote ref.
Neither branch-name confusion nor that 404 means the published commit is absent.
No PR exists for the published branch in the current all-state query.

Code commit: `019c26f65e0e59f8a8661321d63c5fb1fb105000`.
Its parent is current-source snapshot `0335d5a5e0fd197522365fef3487a279be94ad4f`.
Only code/test changes:
- `.github/workflows/ci-images-spacesd-lag.yml`
- `scripts/images/tests/test_lag_scope.py`

Head `9846bb6` adds only `evidence/guarded-carrier-failures-20261004/README.md`.
Its executable source is identical to tested code `019c26f`.

## What the local evidence proves

Before the patch, the shipped workflow shell fails with exit 128 against a
synthetic valid Git base lacking `libs/cua-spacesd/VERSION`. After the patch,
that case follows the existing version-introduction skip route. Invalid base
references still fail with 128. Existing changed/unchanged VERSION cases retain
their routes. The source is a missing-file handling repair, not a broad CI gate
relaxation.

The exact committed code already ran 26 passing tests, recorded in
`/workspace/receipts/cua-batch2/019c26f-final-tests.log`: 3 new tests (4 histories)
and 23 existing image-pins/wiring tests. H4 independently approved the code and
its docs. No unchanged local suite was rerun in this batch.

## Current hosted result: concrete correction to historical NOT_RUN wording

The code commit now has one completed successful check:
- workflow `CI: Image API`, job `validate`, push event, exact head `019c26f...`;
- https://github.com/kvnloo/cua/actions/runs/37174772647/job/111355013867

This is NOT the repaired `CI: Images on the current cua-spacesd` workflow. Its
focused tests cover Image API/model/recipe/workflow functionality in
`libs/python/cua-sandbox/tests`; they do not run `scripts/images/tests/test_lag_scope.py`.
Thus one green hosted Image API job does not qualify the absent-base workflow
fix on GitHub.

The published documentation head `9846bb6` has ZERO check runs. Both commits
have zero legacy commit statuses (the combined-status API says `pending` when
its statuses list is empty; this is not an observed queued/running workflow).
There is no observed exact-candidate hosted image-lag result and no observed
hosted run of the new regression. The correct status is:
**published; locally tested and independently reviewed; one other hosted job
passes on code SHA; targeted hosted validation unexecuted/unobserved.**
Historical receipt NOT_RUN statements remain time-scoped; this note supplies
the fresh API result rather than rewriting old evidence.

## Original carrier remains uncleared

#87 still has head `b2ae7cb934403f2585c7d3ed23a188b44264f293` and reports
202 success, 23 skipped, 13 failure. Its original catalog-lag job
111308484971 still reports failure. None of these failures is cleared by
publication of a separate branch.

Its base VERSION absence is confirmed by the earlier API query, and its failed
scope step reported exit128. This supports the local causal diagnosis but exact
hosted stderr remains unavailable: direct log downloads returned Forbidden.
We do not claim the local reproduction proves every possible hosted failure
cause or that the proposed fix has cleared that job.

The 13-row ledger remains correctly bounded:
- Image-lag scope: missing-file defect reproduced locally; hosted stderr unknown.
- Release-title validation: exact script rejects current ci title under required
  release mode; no owner title/base edits and no hosted clearance.
- Docs-image baseline: annotation says ledger branch absent; exact failing refs unknown.
- Docs-sync gate: records failed selected checks; not proof of a further root cause.
- Other nine rows (image doctor, Windows download, three installer rows,
  portable parity, three references): exact causes remain unknown without logs.

## Boundaries and next choice

No #111/#4316, FIX-04, replay, accounting, motion or owner-branch changes occurred.
No workflow dispatch/rerun, upstream write, install, paid call, or new test run.
Owner can decide whether/when to request normal downstream hosted qualification
on the exact candidate. Until that occurs, describe this as a published local
repair with targeted hosted qualification outstanding—not a cleared carrier.

Supporting fresh responses: `/workspace/receipts/cua-batch4/{published-ref,
code-checks,docs-checks,candidate-job}.json` and
`/workspace/receipts/cua-batch2/87-batch4.json`.
