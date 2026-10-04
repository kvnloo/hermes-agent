# Batch 3: CUA factory/source boundary audit

Read-only public sources:
- Wave 7: https://github.com/kvnloo/cua/issues/93#issuecomment-5973265581
  (updated 2026-10-03T20:38:09Z).
- Posting queue: https://github.com/kvnloo/cua/issues/74#issuecomment-5973266113
  (updated 2026-10-03T20:38:13Z).
- Current #111 metadata/body: https://github.com/kvnloo/cua/pull/111,
  head `f74a4d5e1ae804249c0d37f576702890949d76f8`.

## Disposition

Independent CI repair `019c26f65e0e59f8a8661321d63c5fb1fb105000` remains
non-overlapping. Its complete changed-file set is:
- `.github/workflows/ci-images-spacesd-lag.yml`
- `scripts/images/tests/test_lag_scope.py`

It handles a missing base VERSION using synthetic Git histories. Documentation
child `9846bb67a927ef1320bce577c4bbae1ea2974c12` records failed-job dispositions.
Neither changes Driver/native behavior, guarded completion, evidence accounting,
posting-queue gates, compiled replay, or staged FIX-04. H4 has approved both code
and documentation. The existing 26-pass result qualifies this CI scope only.

No material correction to the factory's existing limited CI/test receipt is
required: it did not claim Driver readiness, native safety, timing results, or
promotion eligibility. This local note adds source boundaries without rewriting
owned staged queue/accounting packets or generating duplicate work.

## #111 source risk that matters

#111's published body explicitly limits it to Python terminal outcomes for
exception paths that already exited. It excludes acknowledged-but-unresolved
completion replay, exactly-once guarantees, TypeScript parity changes, and a new
ActionResult contract. The sibling #105 mutation-outcome work is excluded.

Wave 7's separate staged FIX-04 packet concerns broader unknown-delivery and
runner behavior and an owner-gated native behavior change. Therefore #111's
passing unit/hosted results cannot serve as FIX-04 qualification, cannot retire
its source risk, and cannot resolve the related native owner ruling. Neither
packet is a substitute for exact selected-source composition review by its
existing owner. No such review, safety reproduction, port, or new runtime test
was attempted here.

The Wave 7 comment names #4316 at historical `a0bca7440`; our later API snapshot
records `b2ae7cb934403f2585c7d3ed23a188b44264f293`. This is a timestamp/source
boundary, not permission to silently update Wave 7's measured-source claims.
The factory's already-recorded #111/current-carrier divergence remains an owner
reconciliation requirement; equal guard blobs alone do not establish full-tree
or runtime qualification.

## Gates retained verbatim in meaning

- Public staged queue: READY NOW 0 of 55, not a factory promotion allowance.
- B-09 and R2-07f: accepted BLOCKED packets; zero measured trials; pilots excluded.
- Live modal fallback: 0/4 pooled; substituted fallback/admission requires owner decision.
- Toggle compiled replay: +2.2 ms non-inferiority bound, not +2.0 ms.
- Existing explicit owner gates remain: budget, modal fallback/admission,
  toggle bound, native behavior, privacy decisions and required recertification.
- No additive savings across different binaries, and no inheritance of timing
  claims onto the factory's current upstream checkout.

No private/unpublished artifact was accessed. No raw runtime evidence was
executed or fetched. Only public comments, #111 metadata/body and a public
FIX-04 commit filename listing were read; that final-commit listing is not used
as a whole-stack implementation inventory. No Driver/native/guarded tests,
paid calls, dependency installation, upstream writes, or branch changes occurred.

Next owner choice: keep the CI repair eligible for its own downstream review,
while leaving #111 composition and all Wave 7 gates with their existing owners.
