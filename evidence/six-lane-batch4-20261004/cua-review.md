# Batch 4 H5 — ingress/profile gate and CUA check clarification review

Hermes parent checkout latest FETCH_HEAD inspected: `ea81748579ee1732d214ccb75f91d22208ed623d`.
H5 evidence head preserved: `d2d03f033fc9a3586c313efcf357d9e3fecee3f8`.
No new worktree, source edit, test run, installation, publication or upstream write.

## Qualification gate

Read current maintainer-authored issues related to model/profile and gateway/cache and the latest relevant model-override reports. No concrete distinct unowned missing proof was established.

- #131294 channel_overrides cache eviction has open owner PR131295 (EloquentBrush0x) and132238 (Sahilvishnaliya), and overlaps the already-completed whole-turn qualification. No duplicate proof or patch.
- #130572 profile model ignored has open owner PR130576 (dskwe). Current discussion distinguishes saved per-conversation picks, configuration defaults, and gateway launch mode. It does not establish a new unowned missing runtime contract.
- Latest source delta since20bd004 is local-runtime/bootstrap/PM/desktop-feature-flag work, not a changed gateway ingress/cache/profile path. No broad unchanged suite was run.

Per parent gate, narrowed this lane to independent CUA exact-code/head/check clarification review. Previously recorded97 session tests and72f whole-turn qualification were not repeated.

## CUA independent review — APPROVE clarification

Reviewed `/workspace/receipts/batch4-cua.md` and independently checked fresh GitHub API plus exact workflow source:

- Published `kvnloo/cua:fix/image-lag-historical-base-20261004` points at `9846bb67a927ef1320bce577c4bbae1ea2974c12`.
- Code commit `019c26f65e0e59f8a8661321d63c5fb1fb105000` parent is `0335d5a5e0fd197522365fef3487a279be94ad4f`.
- Code-to-published-head diff is only `evidence/guarded-carrier-failures-20261004/README.md`; executable files match.
- Exact code SHA has one successful check, `validate`, in **CI: Image API**, push run37174772647/job111355013867: https://github.com/kvnloo/cua/actions/runs/37174772647/job/111355013867.
- The workflow path is `.github/workflows/ci-image-api.yml`, not repaired `.github/workflows/ci-images-spacesd-lag.yml`. Its explicit tests are under `libs/python/cua-sandbox/tests`; they do not include the new `scripts/images/tests/test_lag_scope.py` regression.
- Published docs head has zero check runs.
- Both code and docs heads have zero legacy commit statuses. The combined API's `state: pending` with `total_count: 0` does not establish a queued/running workflow.

Approved wording: **published, locally tested and independently reviewed; one other hosted job passed at the code SHA; targeted image-lag hosted validation remains unobserved**. It would be incorrect to call the repaired workflow hosted-green or the original carrier cleared.

This review verifies the fresh clarification only. It did not repeat local26-pass validation, requalify the full13-failure carrier ledger, dispatch/rerun workflows, or access Driver/native/guarded/runtime/security evidence. Existing owner and promotion gates remain intact.

Next choice stays with parent/owner: request ordinary downstream hosted validation on the exact candidate if appropriate, preserving distinction between CI: Image API and the repaired image-lag workflow.
