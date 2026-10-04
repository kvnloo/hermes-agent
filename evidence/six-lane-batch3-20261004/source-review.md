# Batch 3 H5 — current delta triage and independent CUA boundary review

Hermes current upstream: `20bd00439cfc2e8d6d296f28fba0cdeeb6cdda49`.
Preserved H5 evidence branch/head `de99559859`; no checkout/reset/branch edits.
No new tests, production edits, dependency installs, publication, or paid calls.

## Targeted Hermes triage

Compared `24b9f0f8c5df5ec6d3d5c10ad9b27c3346bbc925` to current upstream. Exactly five changed files: WhatsApp adapter, bridge script, two WhatsApp test files, and WhatsApp documentation. Parent already assigned that delta to another worker; H5 did not duplicate its test run. Current maintainer-authored request listing showed no new small distinct request.

Two fresh small defect candidates were rejected by category ownership lookup rather than exact-issue-number search alone:
- #132554 Signal setup guide mismatch: existing open PR78930 (veijde) and55689 (Christopher-Schulze) already align setup UI/guidance with native signal-cli daemon.
- #132536 doctor rejects auxiliary main directive: existing open PR132539 (flyer103).

Previously qualified 97 tests were not repeated. Package-quarantine, MCP, fallback, pool and systemd lanes were not duplicated.

## Independent CUA review — APPROVE bounded source note

Reviewed `/workspace/receipts/batch3-cua-boundary.md` using fresh read-only API reads:
- https://github.com/kvnloo/cua/issues/93#issuecomment-5973265581 (Wave7, unchanged updated2026-10-03T20:38:09Z).
- https://github.com/kvnloo/cua/issues/74#issuecomment-5973266113 (posting queue).
- https://github.com/kvnloo/cua/pull/111 body/current head `f74a4d5e1ae804249c0d37f576702890949d76f8`.
- https://github.com/trycua/cua/pull/4316 current head `b2ae7cb934403f2585c7d3ed23a188b44264f293`.

Verified local commit changed-file lists: CI repair `019c26f65e0e59f8a8661321d63c5fb1fb105000` touches only `.github/workflows/ci-images-spacesd-lag.yml` and `scripts/images/tests/test_lag_scope.py`; documentation child `9846bb67a927ef1320bce577c4bbae1ea2974c12` touches only `evidence/guarded-carrier-failures-20261004/README.md`.

Conclusions supported by those sources:
- The CI repair's scope is independent of Driver/native/guarded behavior. Its previously recorded26-pass result cannot qualify runtime or timing behavior. No tests were rerun in this review.
- #111 explicitly limits itself to terminal handling of already-exiting Python exception paths and excludes acknowledged-but-unresolved completion replay, exactly-once guarantees, TypeScript parity and a new ActionResult contract. Consequently its test results do not establish resolution of the separate staged FIX04 scope or native owner ruling.
- Wave7 historical4316 head `a0bca7440` versus current `b2ae7cb...` is a timestamp/source boundary. It is not a basis to silently migrate measured claims.
- Public gate values are preserved: READY NOW0/55; B09 andR2-07f accepted BLOCKED with zero measured trials/pilots excluded; modal pooled0/4; toggle non-inferiority+2.2ms, not+2.0ms; owner budget/admission/native/privacy/recertification decisions remain.
- No timing savings may be summed across different binaries or inherited by the factory current checkout.

Review approval concerns the boundary note and claim discipline only. It is not runtime approval, a new readiness measurement, or a promotion decision. No raw runtime evidence, unpublished artifacts, Driver/native/security replay, or guarded tests were accessed or run. Existing author/owner responsibilities remain intact.

Actionable next choice: retain the CI repair for its own downstream review, and leave #111 selected-source composition and Wave7 owner gates to existing owners. No new implementation opportunity was established in this lane.
