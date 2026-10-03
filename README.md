# Three bounded production candidates for review

Pinned tested upstream main: `3c9847f5e86e81c23335a54daa532de28eeffeb3`. Each is an automatic integration of an existing published candidate; no new behavior or test cases in these refreshes. All three fixes were absent from this pinned main and their source PRs remained open at audit. This is local bounded qualification, not whole-PR or release acceptance. Kevin Rajan directed the downstream work.

## Importer memory budget

Branch `downstream/20261003-promotion-review-import-memory`; [exact commit 4bfa806c4ac197447d062cf8655f91145a663f31](https://github.com/kvnloo/hermes-agent/tree/4bfa806c4ac197447d062cf8655f91145a663f31). Tree `993eb03cefb36257fad79701682cfe2a26425d42`. Preserved previous candidate `9c56a7c6b76d93717e0eff4a861fcfc8ea953ec9` is the second parent.

Imported memory respects the destination budget and remains usable by MemoryStore. Raw destination config only; managed overlays and malformed policy are not qualified.

Evidence: **60 PASS; exact-main control 58 PASS / 2 FAIL; independent subset 2 PASS**. Independent subsets overlap the matrices and must not be summed. Controls use the exact whole pinned main with identical test overlays, no production substitution.

Credit: John Paul Soliva / jonpol01; original upstream #123570.

## Cancellation and recovery

Branch `downstream/20261003-promotion-review-cancel-recovery`; [exact commit e5ee351a94465208b68ebf27d634abcf223d00d7](https://github.com/kvnloo/hermes-agent/tree/e5ee351a94465208b68ebf27d634abcf223d00d7). Tree `a31c8a06439a7ae0f62d5b2c9b089f24b00c131c`. Preserved previous candidate `1a523b7df2ba4731a5d9ae0aa06b0f51976d977d` is the second parent.

Wake remaining cancellation waiters despite notification failure; retire successfully interrupted local turn markers before notification failures can cause recovery. Combined control isolates fanout prerequisite, not every later marker assertion. No live restart or BaseException qualification.

Evidence: **122 PASS; exact-main selected control 4 FAIL / 3 PASS; independent subset 7 PASS**. Independent subsets overlap the matrices and must not be summed. Controls use the exact whole pinned main with identical test overlays, no production substitution.

Credit: Codex downstream corrections; human lifecycle foundations by Teknium, Siddharth Balyan, Brooklyn Nicholson, Yuan Li and joaomarcos; Liuzikaii/KaiKai owns separate related upstream #125419.

## Chronos fallback ownership

Branch `downstream/20261003-promotion-review-chronos-fallback`; [exact commit 5064c2698aebf1d6b811f300468fd4afb9313d32](https://github.com/kvnloo/hermes-agent/tree/5064c2698aebf1d6b811f300468fd4afb9313d32). Tree `ba373bdd375220116636b070767d7ef74474894b`. Preserved previous candidate `a83b87d635459c5c850115e2ff5c4f3ce259f66e` is the second parent.

Keep the Chronos fallback ticker behind the live gateway ownership gate while preserving deferred startup and legacy provider signatures. Real finite ticker threads, mocked liveness/NAS rejection/ticks; no actual NAS delivery or unrelated server-owner qualification.

Evidence: **66 PASS; exact-main selected control 2 FAIL; independent subset 5 PASS**. Independent subsets overlap the matrices and must not be summed. Controls use the exact whole pinned main with identical test overlays, no production substitution.

Credit: Finn763, upstream #126977; deferred-start prerequisite by unsupportedpastels / Mark S.; existing #126907 claimant vanscodex retains ownership.

## Gates and exclusions

Remote CI is NOT_RUN at publication: no observed checks, statuses or Actions runs; local tests are not green CI. Upstream active protect-main ruleset 14161644 requires `All required checks pass` and code-owner review. Classic branch-protection lookup returned 403, so complete protection configuration was not observable. Verify these gates and target-head compatibility before any merge. No workflow reruns or dispatches were requested.

No upstream posting, merging, deployment, installation or paid model calls. Existing refs are preserved. Keep #123578 on hold, #417 NOT_MET_AS_WORDED, #131689 needs-decision, and TUI after-landing gates. Preserve other policy/native/install holds. Do not overlap the seven-phase review, o8 ownership, HermesCUA/Bend, or agentcontact426 work. No blanket promotion authority is implied.
