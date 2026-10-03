# Source-current Hermes correctness and consumer qualification

2026-10-03. Existing five-lane downstream program continued through current-source checks, two concrete consumer boundaries, a current-main cancellation integration and unchanged-author checkpoint recertification. Exact new downstream commits/trees/parents are in publication-map.json. Separate branches are not one integrated release. No upstream posts, merge commits, deployments, installations, auth changes, paid calls or workflow reruns occurred.

## Cancellation and recovery on pinned current main

Final `1a523b7df2ba4731a5d9ae0aa06b0f51976d977d`, based on `bd0affe5e5f723579df8902852f5d0c47795f355`. Carries the existing published fanout correction681 and local-interrupt marker correction719 through author-preserving cherry-picks `35c1b31c52` and `833b6ad1e84c5dc503c0c45a5a651bc24833dedb`, then adds one current-batch consumer test. Original protocol contribution remains [Liuzikaii/KaiKai's #125419](https://github.com/NousResearch/hermes-agent/pull/125419), unchanged OPEN `cb8f552878b6cf527851a5d939c793b33e2bc2da`. Its separate registration rollback/cb8 and f99 tests were not unnecessarily transplanted. Existing main authorship/history is retained; Codex composed the prior corrections and added this test under Kevin Rajan direction.

Integration preserves main's partial-batch locked answers and cancelled outcome, window-decline tracking, orphan parameter/callers, profile-bound observer hook, background-review cancellation and approval notifications. Only explicit local Stop opts into marker retirement; default shared callers retain ownership. Notification exceptions remain visible after removed request owners settle. Callback exceptions/BaseException behavior is unchanged and outside this correction.

Final canonical five-file matrix on exact1a523: **122 PASS**, not a synthesized count. One newly authored case, six previously published correction cases and remaining existing coverage. Independent prior-source six-case execution **6 PASS** on833; those six test bodies and production are unchanged in1a523. Independent new locked-batch consumer on final1a523: **1 PASS**, no blocker. These are seven distinct reviewed cases, not seven newly authored cases.

Source-bound controls use final test bytes:

- Whole pinned main plus seven selected tests: **4 FAIL,3 PASS**. Two fanout failures; local-interrupt and locked-batch error arms stop at the second owner remaining blocked. Cleanup drains fixture waiters.
- Exact intermediate35c1 with only the fanout fix plus four marker cases: **1 FAIL,3 PASS**. The actual recovery scheduler observes the stale marker and offers attempt1, isolating the marker gap from the earlier fanout failure.
- New locked-batch case alone on main: **1 FAIL**; candidate **1 PASS**. Actual clarify registration/lock and StdioTransport error preserve the first answered item, produce cancelled outcomes for both owners, and retain the original ENOSPC exception. The negative proves the fanout prerequisite; it does not separately isolate every later answer assertion. An old681 full-module control was not forced through main's incompatible transport API.

Real temporary marker files, request registry, transport and recovery eligibility; finite agent/scheduler/transport fault seams. No process restart, model execution, every-callback-error, native compute or whole-PR qualification.

## Current hosted-stack rejection retires recovered Bot receipt watchers

`751011c036644e4932a5852901ea1b46ef1a5890` composes the existing b45 rejection-retirement correction onto current [#121813](https://github.com/NousResearch/hermes-agent/pull/121813) `bc1b572e2c0cdefb9a9324198df3155815fae500` through cherry-pick251c0d62, then adds one consumer. The only production delta is the original ten-line reconcile catch. Brian Fernstrom/Lokee86 and Teknium retain implementation credit; keeltrace and andrexibiza retain review-contract credit. The current stack already implements Bot receipt-task retirement; that mechanism was not duplicated.

The new crossing creates a benign owned temporary queued admission/receipt, drives real runtime initialization and recovery-created watcher setup, then rejects adapter configuration. At actual reservation release it verifies the watcher is cancelled/joined and the task registry empty; the main profile stays served and queued delivery is not falsely marked successful. No credential/ticket/routing/auth operation is exercised.

Candidate four-file selection: **13 PASS,1 deselected (one new,12 inherited)**. Exact wholebc1 plus identical consumer: **1 FAIL**, actual watcher remains pending. Independent final canonical consumer/cleanup selection: **3 PASS**, no blocker. Real-control-socket case excluded.

Earlier draft incorrectly expected the shared terminal future to be cancelled, although the receipt coroutine deliberately shields it. That draft assertion failure was retained and corrected as a fixture-contract error, not called a production bug. Another draft negative failed at an earlier hook seam; final negative directly reaches pending watcher state. Baseline cleanup drains tasks; no hidden live work remains. This narrow current-stack composition does not imply that the separate hosted activity/retry union was integrated into121813.

## Persisted inbound media reply context

Test-only `b632ef7ae4d51dd782280b4e2826a2a5f2efd821` directly extends Blaryxoff's current [#37717](https://github.com/NousResearch/hermes-agent/pull/37717) `68a913b9b453a5eb02b2e98fc9e0b849f0e284bf`, itself a direct child of pinnedbd0. Blaryxoff owns the existing implementation; Codex added one consumer test.

Actual Telegram event builder, canonical SessionStore append, real SQLite, store close/reopen and transcript load lead into actual inbound text preparation. A native-style ID-only reply recovers the correct earlier voice transcript instead of a distinct newer one. The fixture supplies already-transcribed text and Telegram-shaped objects. No live Telegram, STT provider, authorization, model call or full agent dispatch is claimed.

Final canonical five-file selection: **12 PASS (one new,11 existing)**; Ruff PASS; independent final consumer **1 PASS**, no blocker. Exact parent run_inbound.py module substituted with unchanged test/other sources: **1 FAIL**, missing reply prefix after adapter/persisted-ID assertions already pass. This is a module-source control, not a whole-parent test run.

The current author already rebased/verified formatter cases; this does not replace that work. Prior media #125401 concerns outbound WeChat/weserv URL extraction and was not repeated. The old PR body's quote-cap wording is stale; current full-quote behavior was not changed. Telegram SDK is absent but the existing optional-import parser path works offline; nothing was installed. Hosted workflows on the author's head reportedly require maintainer approval; none were triggered here.

## Checkpoint lock recovery: unchanged current-author recertification

[Upstream #92127](https://github.com/NousResearch/hermes-agent/pull/92127), OPEN exact `cf7e955cbbadeec3f2888daf278b72fdf590c76c`, is 33hodl/Diamond Hands Dig's existing single commit directly atop pinnedbd0. **No new code, tests or duplicate branch**. TurgutKural's earlier live-host observations and historical59-test evidence are credited, not reused as current execution. Earlier automated review/approval language applied to older heads, not current maintainer approval.

Pristine current source, canonical checkpoint file: **59 PASS**. Independent three authored lock cases: **3 PASS**, no scoped blocker. Whole main with unchanged author test overlay cannot collect because it lacks the new imported helper; that failure is not behavioral evidence. A transparent control removes only the unavailable helper import and selects unchanged retry/snapshot bodies and fixture helper (AST bindings verified): whole main **2 FAIL** at real Git lock-exists rc128 / ensure_checkpoint False, identical compatible overlay on author source **2 PASS**. Original test file restored byte-for-byte; no production shim.

Real temporary Git store/index and public snapshot path. No real abandoned process/procfs/concurrent writer. Current implementation uses the existing600-second age threshold. Immediate age0 timeout cleanup remains unimplemented and unqualified; absence before a command alone does not prove ownership of a subsequently appearing lock under concurrency. This is one-file current-head evidence, not full checkpoint/CI/concurrency/cross-platform approval.

## Meta-check, holds and publication limits

Completed hosted/Chronos/Sidebar/checkpoint/cron/Discord source heads were refreshed and unchanged; their already-closed integration gaps were not reopened merely because PRs remain open. Existing supersession dispositions remain: forks182/190/232/268/194/218 should not be revived, and216 points to an open successor rather than a landed fix. Current standalone cancellation/marker integration is distinct from previously tested old-source branches.

External-memory prefetch [#130976](https://github.com/NousResearch/hermes-agent/pull/130976) and [#130997](https://github.com/NousResearch/hermes-agent/pull/130997) propose conflicting policy choices; [the existing discussion](https://github.com/NousResearch/hermes-agent/issues/130974#issuecomment-5941820958) calls for maintainer decision. No policy was selected or provider exercised. #123578 remains owner-contract HOLD based on automated review, not maintainer rejection; #417 remains acceptance HOLD; #131689 remains needs-decision. Library authorization and native older-backend validation limits remain. Bend/z0 work stays with its separate owner.

Final source refresh confirms the selected exact owner heads remain OPEN and unchanged. Independent source/publication audits found no blocker; workflow filters on new candidate trees do not match reviewed branches and have no create trigger. Ref publication uses create-only leases and no tags/old-ref updates. Post-publication verification binds exact remote refs/trees and Actions/check/status counts; empty CI means NOT_RUN, never PASS. Raw logs/full source bindings remain local; this sanitized receipt records public provenance and precise limits. This bounded queue review does not assert exhaustion of all repository work or grant upstream promotion authority.
